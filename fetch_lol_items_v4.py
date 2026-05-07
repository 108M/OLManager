#!/usr/bin/env python3
"""
fetch_lol_items_v4.py

Scraper robusto de items de LoL desde leagueoflegends.fandom.com
usando la API parse y extrayendo datos de la infobox estructurada.

Estructuras clave:
  - Precio:    <td data-source="buy">...875...</td>
  - Venta:     <td data-source="sell">...612.5...</td>
  - ID:        <td data-source="id">1037</td>
  - Imagen:    <td data-source="image">...<img src="..."</td>
  - Stats:     <div data-source="ad|hp|mr|...">...<div class="pi-data-value">+70 attack damage</div></div>
  - Receta:    <table style="border-collapse:collapse;"> (componentes data-item="...")
"""

import httpx
import html as html_module
import json
import re
import time
from pathlib import Path

API_URL = "https://leagueoflegends.fandom.com/api.php"
OUTPUT_DIR = Path("data/items")
OUTPUT_JSON = OUTPUT_DIR / "items.json"

SLEEP = 0.25
client = httpx.Client(
    headers={"User-Agent": "OLM-ItemFetcher/4.0"},
    timeout=20,
    follow_redirects=True,
)

# ── Categorías que nos interesan ──
VALID_CATEGORIES = {
    "Starter items",
    "Basic items",
    "Epic items",
    "Legendary items",
    "Boots",
}

# ── Stats mapping ──
STAT_MAP = {
    "attack damage": "ad",
    "ability power": "ap",
    "armor": "armor",
    "magic resistance": "mr",
    "health": "hp",
    "critical strike chance": "crit_chance",
    "critical strike damage": "crit_damage",
    "attack speed": "attack_speed",
    "movement speed": "movement_speed",
    "life steal": "life_steal",
    "lethality": "lethality",
    "ability haste": "ability_haste",
    "health regen": "hp_regen",
    "mana regen": "mp_regen",
    "tenacity": "tenacity",
    "omnivamp": "omnivamp",
    "mana": "mana",
    "magic penetration": "magic_pen",
    "armor penetration": "armor_pen",
    "armpen": "armor_pen",
    "magicpen": "magic_pen",
}


def api_parse(page: str) -> str:
    params = {
        "action": "parse",
        "page": page,
        "prop": "text",
        "format": "json",
    }
    for attempt in range(3):
        try:
            r = client.get(API_URL, params=params)
            r.raise_for_status()
            return r.json()["parse"]["text"]["*"]
        except Exception as e:
            print(f"  ! Error parseando '{page}': {e}")
            time.sleep(2 * (attempt + 1))
    return ""


def extract_number(text: str) -> float | None:
    """Extrae el primer número de un texto (ej: '+70', '612.<small>5</small>', '25%')."""
    # Quitar HTML
    clean = re.sub(r'<[^>]+>', '', text)
    # Buscar número con opcional decimal
    match = re.search(r'[\+\-]?(\d+(?:\.\d+)?)', clean)
    if match:
        return float(match.group(1))
    return None


def parse_item(name: str) -> dict | None:
    """Extrae todos los datos de un item desde su HTML."""
    html = api_parse(name)
    if not html:
        return None

    result = {
        "name": name,
        "id": None,
        "total_cost": 0,
        "sell_value": 0,
        "components": [],
        "stats": {},
        "image_url": None,
        "tags": [],
    }

    # ── Precio (buy) ──
    buy_match = re.search(
        r'<td[^>]*data-source="buy"[^>]*>(.*?)</td>',
        html, re.DOTALL | re.IGNORECASE
    )
    if buy_match:
        cost = extract_number(buy_match.group(1))
        if cost:
            result["total_cost"] = cost

    # ── Venta (sell) ──
    sell_match = re.search(
        r'<td[^>]*data-source="sell"[^>]*>(.*?)</td>',
        html, re.DOTALL | re.IGNORECASE
    )
    if sell_match:
        sell = extract_number(sell_match.group(1))
        if sell:
            result["sell_value"] = sell

    # ── ID ──
    id_match = re.search(
        r'<td[^>]*data-source="id"[^>]*>(\d+)</td>',
        html, re.DOTALL | re.IGNORECASE
    )
    if id_match:
        result["id"] = int(id_match.group(1))

    # ── Imagen ──
    img_match = re.search(
        r'<td[^>]*data-source="image"[^>]*>.*?<img[^>]*src="([^"]+)"[^>]*>',
        html, re.DOTALL | re.IGNORECASE
    )
    if img_match:
        img_url = img_match.group(1)
        if "data:image" in img_url:
            # Buscar data-src
            ds = re.search(r'data-src="([^"]+)"', img_match.group(0))
            if ds:
                img_url = ds.group(1)
        result["image_url"] = img_url

    # ── Stats ──
    # Buscar divs con data-source que mapeen a stats conocidos
    stat_blocks = re.findall(
        r'<div[^>]*data-source="([^"]+)"[^>]*>.*?<div[^>]*class="pi-data-value[^"]*"[^>]*>(.*?)</div>.*?</div>',
        html, re.DOTALL | re.IGNORECASE
    )
    for source, value_html in stat_blocks:
        stat_key = STAT_MAP.get(source.lower())
        if not stat_key:
            # Intentar inferir del texto (priorizar nombres más largos para evitar
            # que 'armor' se coma a 'armor penetration', etc.)
            clean_text = re.sub(r'<[^>]+>', '', value_html).lower()
            for key, mapped in sorted(STAT_MAP.items(), key=lambda kv: -len(kv[0])):
                if key in clean_text:
                    stat_key = mapped
                    break
        if stat_key:
            val = extract_number(value_html)
            if val is not None:
                # Detectar si es porcentaje
                if '%' in value_html:
                    val = val / 100.0
                result["stats"][stat_key] = val

    # ── Componentes ──
    recipe_table = re.search(
        r'<table[^>]*style="border-collapse:collapse;"[^>]*>(.*?)</table>',
        html, re.DOTALL | re.IGNORECASE
    )
    if recipe_table:
        recipe_html = recipe_table.group(1)
        items_in_recipe = re.findall(r'data-item="([^"]+)"', recipe_html)
        if len(items_in_recipe) > 1:
            # El primer data-item es el item mismo, los siguientes son componentes
            # Pero a veces hay duplicados (icono + nombre)
            seen = set()
            components = []
            for item_name in items_in_recipe[1:]:
                decoded = html_module.unescape(item_name)
                if decoded != name and decoded not in seen:
                    seen.add(decoded)
                    components.append(decoded)
            result["components"] = components

    # Si no tiene costo ni stats ni componentes, probablemente no es un item jugable
    if result["total_cost"] == 0 and not result["stats"] and not result["components"]:
        return None

    return result


def fetch_items_from_grid() -> list[dict]:
    """Obtiene lista de items desde la página principal, filtrando por categoría."""
    print("=" * 60)
    print("PASO 1: Obteniendo lista de items")
    print("=" * 60)

    html = api_parse("Item (League of Legends)")
    if not html:
        return []

    items = []
    grid_start = html.find('id="item-grid"')
    if grid_start == -1:
        return []

    grid_html = html[grid_start:grid_start + 200000]

    # Extraer secciones por categoría
    # Cada categoría es: <dl><dt>Categoría</dt></dl> seguido de <div class="tlist"><ul>...items...</ul></div>
    sections = re.findall(
        r'<dl><dt>([^<]+)</dt></dl>\s*<div[^>]*class="tlist"[^>]*>\s*<ul>(.*?)</ul>',
        grid_html, re.DOTALL
    )

    print(f"  -> {len(sections)} categorías encontradas")

    for category, ul_html in sections:
        category = category.strip()
        if category not in VALID_CATEGORIES:
            continue

        # Extraer data-item de cada <li>
        item_matches = re.findall(r'data-item="([^"]+)"', ul_html)
        unique_items = list(dict.fromkeys(item_matches))

        print(f"  [{category}]: {len(unique_items)} items")

        for raw_name in unique_items:
            name = html_module.unescape(raw_name)
            items.append({"name": name, "category": category})

    print(f"\n  Total items a procesar: {len(items)}")
    return items


def main():
    OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

    items_list = fetch_items_from_grid()
    if not items_list:
        print("ERROR: No se encontraron items")
        return

    # 2. Parsear cada item
    print("\n" + "=" * 60)
    print("PASO 2: Parseando items")
    print("=" * 60)

    items_data = {}
    skipped = []

    for i, info in enumerate(items_list):
        name = info["name"]
        print(f"  {i+1}/{len(items_list)}: {name}...", end=" ")

        data = parse_item(name)
        if data and data.get("total_cost", 0) > 0:
            items_data[name] = data
            stats_keys = list(data["stats"].keys())
            print(f"OK (cost={data['total_cost']}, stats={stats_keys})")
        else:
            skipped.append(name)
            print("SKIP")

        time.sleep(SLEEP)

    print(f"\n-> {len(items_data)} items válidos, {len(skipped)} skipped")

    # 3. Guardar JSON
    print("\n" + "=" * 60)
    print("PASO 3: Guardando JSON")
    print("=" * 60)

    result = {
        "source": "leagueoflegends.fandom.com (infobox v4)",
        "item_count": len(items_data),
        "items": items_data,
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Listo!")
    print(f"  {len(items_data)} items -> {OUTPUT_JSON}")

    if items_data:
        first = next(iter(items_data.values()))
        print(f"\nEjemplo: {first['name']}")
        print(json.dumps(first, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
