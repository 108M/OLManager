#!/usr/bin/env python3
"""
fetch_lol_builds.py

Scraper de builds de LoL desde lolalytics.com usando curl_cffi para burlar Cloudflare.
Extrae builds para cada campeón en su lane principal (Challenger).
Guarda las opciones de items en arrays sin expandir combinaciones.

Estructura del output:
{
  "metadata": {...},
  "builds": {
    "jax": {
      "lane": "top",
      "highest_win": {
        "starting_items": [{"item_id": 1082, "name": "Dark Seal"}, ...],
        "core_build": [{"item_id": 3078, "name": "Trinity Force", "win_rate": null, "games": null}, ...],
        "situational_items": {
          "slot_4": [{"item_id": 3053, "name": "Sterak's Gage", "win_rate": 0.9167, "games": 12}, ...],
          ...
        }
      },
      "most_common": { ... }
    }
  }
}
"""

import json
import re
import time
from pathlib import Path

from curl_cffi import requests

BASE_URL = "https://lolalytics.com"
OUTPUT_DIR = Path("data/builds")
OUTPUT_JSON = OUTPUT_DIR / "builds.json"
ITEMS_JSON = Path("data/items/items.json")

SLEEP = 0.5


def load_items_index():
    """Carga items.json y crea índice inverso: item_id -> nombre en inglés."""
    with open(ITEMS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    id_to_name = {}
    for name, item in data["items"].items():
        item_id = item.get("id")
        if item_id:
            id_to_name[int(item_id)] = name
    return id_to_name


def fetch_html(url):
    """Obtiene HTML usando curl_cffi (imita navegador Chrome real)."""
    try:
        r = requests.get(url, impersonate="chrome110", timeout=30)
        if r.status_code == 200:
            return r.text
        else:
            print(f"  ! HTTP {r.status_code} en {url}")
            return ""
    except Exception as e:
        print(f"  ! Error: {e}")
        return ""


def parse_tierlist(html):
    """Extrae lista de campeones y su lane principal desde la tierlist HTML."""
    champions = []
    # Buscar tabla de campeones. Cada fila tiene un enlace al build.
    # Ejemplo: <a href="/es/lol/jax/build/?tier=challenger">...</a>
    # O también puede tener lane: <a href="/es/lol/jax/build/?lane=jungle&tier=challenger">
    
    # Patrón 1: enlaces directos a build
    seen = set()
    for match in re.finditer(r'href="(/es/lol/([^/]+)/build/\?tier=challenger)"', html):
        url = match.group(1)
        name = match.group(2)
        if name not in seen:
            seen.add(name)
            champions.append((name, None))  # Lane desconocida por ahora
    
    # Si no encontramos suficientes, intentar otro patrón
    if len(champions) < 50:
        # Buscar en la tabla: cada fila puede tener el lane en un atributo o en el contexto
        for match in re.finditer(r'href="(/es/lol/([^/]+)/build/\?lane=([a-z]+)&tier=challenger)"', html):
            name = match.group(2)
            lane = match.group(3)
            if name not in seen:
                seen.add(name)
                champions.append((name, lane))
    
    return champions


def get_item_info(img_html, items_index):
    """Extrae item_id y nombre en inglés desde el HTML de una imagen de item."""
    # item_id desde la URL
    id_match = re.search(r'item64/(\d+)\.webp', img_html)
    if not id_match:
        return None
    item_id = int(id_match.group(1))
    
    # Nombre en inglés desde items.json
    name = items_index.get(item_id)
    if not name:
        # Fallback: intentar extraer del alt (estará en español)
        alt_match = re.search(r'alt="([^"]+)"', img_html)
        name = alt_match.group(1) if alt_match else f"unknown_{item_id}"
    
    return {"item_id": item_id, "name": name}


def parse_build_section(section_html, items_index):
    """Parsea una sección de build (starting, core, o item N)."""
    result = []
    
    # Encontrar todos los items en esta sección
    # Cada item está en un div con una imagen
    item_blocks = re.findall(
        r'<div[^>]*class="text-center"[^>]*>.*?<img[^>]*srcset="https://cdn5\.lolalytics\.com/item64/\d+\.webp[^"]*"[^>]*>.*?</div>',
        section_html, re.DOTALL
    )
    
    for block in item_blocks:
        # Extraer info del item
        img_match = re.search(r'<img[^>]*srcset="https://cdn5\.lolalytics\.com/item64/\d+\.webp[^"]*"[^>]*>', block)
        if not img_match:
            continue
        
        item_info = get_item_info(img_match.group(0), items_index)
        if not item_info:
            continue
        
        # Buscar win rate y games asociados a este item
        # Buscar en el mismo bloque o en el hermano siguiente
        win_rate = None
        games = None
        
        # Win rate: <span class="... text-green-500" ...>XX.XX%</span>
        wr_match = re.search(r'<span[^>]*text-green-500[^>]*>.*?<!--t=\w+-->([\d.]+)<!---->%</span>', block)
        if wr_match:
            win_rate = float(wr_match.group(1)) / 100.0
        
        # Games: <span class="... text-gray-400" ...>N</span>
        games_match = re.search(r'<span[^>]*text-gray-400[^>]*>.*?<!--t=\w+-->(\d+)<!----></span>', block)
        if games_match:
            games = int(games_match.group(1))
        
        result.append({
            "item_id": item_info["item_id"],
            "name": item_info["name"],
            "win_rate": win_rate,
            "games": games
        })
    
    return result


def extract_items_from_html(html_block, items_index):
    """Extrae items con sus stats desde un bloque HTML."""
    result = []
    # Buscar cada div que contiene un item
    # Cada item está en un div.text-center que contiene la imagen y opcionalmente stats
    item_divs = re.findall(
        r'<div class="text-center"[^>]*>.*?<img[^>]*srcset="https://cdn5\.lolalytics\.com/item64/(\d+)\.webp[^"]*"[^>]*>.*?</div>',
        html_block, re.DOTALL
    )
    for div_html in item_divs:
        # Extraer item_id
        id_match = re.search(r'item64/(\d+)\.webp', div_html)
        if not id_match:
            continue
        item_id = int(id_match.group(1))
        name = items_index.get(item_id, f"unknown_{item_id}")
        
        # Win rate: buscar <!--t=XX-->NN.NN<!---->%</span>
        win_rate = None
        wr_match = re.search(r'<!--t=\w+-->([\d.]+)<%?\s*-->', div_html)
        if wr_match:
            win_rate = float(wr_match.group(1)) / 100.0
        
        # Games
        games = None
        games_match = re.search(r'<!--t=\w+-->(\d+)<!---->', div_html)
        if games_match:
            games = int(games_match.group(1))
        
        result.append({
            "item_id": item_id,
            "name": name,
            "win_rate": win_rate,
            "games": games
        })
    
    return result


def parse_build_page(html, items_index):
    """Extrae datos de builds desde la página HTML de un campeón."""
    if not html or "Starting Items" not in html:
        return None
    
    # Encontrar el contenedor principal de builds
    # Hay DOS contenedores: uno para Highest Win y otro para Most Common
    # El primero (Highest Win) es el que viene por defecto
    containers = re.findall(
        r'<div class="flex flex-wrap justify-around">(.*?)</div>\s*(?=<div class="flex flex-wrap justify-around">|</main>|<div class="mt-1 grid grid-cols-2">)',
        html, re.DOTALL
    )
    
    if not containers:
        # Fallback: buscar un solo contenedor
        m = re.search(r'<div class="flex flex-wrap justify-around">(.*?)(?:<div class="mt-1 grid grid-cols-2">|</main>)', html, re.DOTALL)
        if m:
            containers = [m.group(1)]
    
    if not containers:
        print("  ! No se encontró el contenedor de builds")
        return None
    
    # Usar el primer contenedor (Highest Win)
    container = containers[0]
    
    # --- Starting Items ---
    starting_items = []
    starting_stats = {"win_rate": None, "games": None}
    
    # Encontrar la sección de Starting Items
    si_start = container.find("Starting Items")
    if si_start != -1:
        # Buscar el div con los items (flex h-[34px])
        si_div_start = container.find('<div class="flex h-[34px] justify-center gap-2">', si_start)
        if si_div_start != -1:
            si_div_end = container.find('</div>', si_div_start)
            si_div_end = container.find('</div>', si_div_end + 6)  # El </div> del contenedor padre
            if si_div_end != -1:
                items_html = container[si_div_start:si_div_end]
                # Extraer items
                for img_m in re.finditer(r'<img[^>]*srcset="https://cdn5\.lolalytics\.com/item64/(\d+)\.webp[^"]*"[^>]*>', items_html):
                    item_id = int(img_m.group(1))
                    name = items_index.get(item_id, f"unknown_{item_id}")
                    starting_items.append({"item_id": item_id, "name": name})
                
                # Win rate y games global (después del div de items)
                stats_html = container[si_div_end:si_div_end+500]
                wr_m = re.search(r'<!--t=\w+-->([\d.]+)<%?\s*Win Rate', stats_html)
                if wr_m:
                    starting_stats["win_rate"] = float(wr_m.group(1)) / 100.0
                games_m = re.search(r'<!--/qv-->(\d+) Games', stats_html)
                if games_m:
                    starting_stats["games"] = int(games_m.group(1))
    
    # --- Core Build ---
    core_build = []
    cb_start = container.find("Core Build")
    if cb_start != -1:
        # Buscar el div flex justify-center que contiene los items
        cb_div_start = container.find('<div class="flex justify-center">', cb_start)
        if cb_div_start != -1:
            # Encontrar el cierre de este bloque (buscamos el </div> del contenedor padre)
            # Estructura: <div class="flex justify-center"> ... items con SVGs ... </div></div></div>
            cb_div_end = container.find('</div>', cb_div_start)
            cb_div_end = container.find('</div>', cb_div_end + 6)
            cb_div_end = container.find('</div>', cb_div_end + 6)
            if cb_div_end != -1:
                cb_html = container[cb_div_start:cb_div_end]
                # Cada item del core está en: <div class="flex justify-center" q:key="N"> ... </div></div>
                core_blocks = re.findall(
                    r'<div class="flex justify-center"[^>]*>(.*?)</div>\s*</div>',
                    cb_html, re.DOTALL
                )
                for block in core_blocks:
                    id_m = re.search(r'item64/(\d+)\.webp', block)
                    if id_m:
                        item_id = int(id_m.group(1))
                        name = items_index.get(item_id, f"unknown_{item_id}")
                        
                        win_rate = None
                        games = None
                        wr_m = re.search(r'<!--t=\w+-->([\d.]+)<%?\s*-->', block)
                        if wr_m:
                            win_rate = float(wr_m.group(1)) / 100.0
                        games_m = re.search(r'<!--t=\w+-->(\d+)<!---->', block)
                        if games_m:
                            games = int(games_m.group(1))
                        
                        core_build.append({
                            "item_id": item_id,
                            "name": name,
                            "win_rate": win_rate,
                            "games": games
                        })
    
    # --- Items 4, 5, 6 ---
    situational = {"slot_4": [], "slot_5": [], "slot_6": []}
    for slot_num in [4, 5, 6]:
        slot_key = f"slot_{slot_num}"
        is_start = container.find(f"Item {slot_num}")
        if is_start != -1:
            is_div_start = container.find('<div class="flex justify-center">', is_start)
            if is_div_start != -1:
                # Encontrar el cierre (varios </div> anidados)
                is_div_end = container.find('</div>', is_div_start)
                is_div_end = container.find('</div>', is_div_end + 6)
                is_div_end = container.find('</div>', is_div_end + 6)
                if is_div_end != -1:
                    is_html = container[is_div_start:is_div_end]
                    # Dividir por "OR"
                    options = re.split(r'<span[^>]*>OR</span>', is_html)
                    for opt_html in options:
                        id_m = re.search(r'item64/(\d+)\.webp', opt_html)
                        if id_m:
                            item_id = int(id_m.group(1))
                            name = items_index.get(item_id, f"unknown_{item_id}")
                            
                            win_rate = None
                            games = None
                            wr_m = re.search(r'<!--t=\w+-->([\d.]+)<%?\s*-->', opt_html)
                            if wr_m:
                                win_rate = float(wr_m.group(1)) / 100.0
                            games_m = re.search(r'<!--t=\w+-->(\d+)<!---->', opt_html)
                            if games_m:
                                games = int(games_m.group(1))
                            
                            situational[slot_key].append({
                                "item_id": item_id,
                                "name": name,
                                "win_rate": win_rate,
                                "games": games
                            })
    
    return {
        "starting_items": {
            "items": starting_items,
            **starting_stats
        },
        "core_build": core_build,
        "situational_items": situational
    }


def get_champion_list_from_tierlist():
    """Obtiene lista de campeones y sus lanes desde la tierlist."""
    print("PASO 1: Obteniendo lista de campeones desde tierlist")
    url = f"{BASE_URL}/es/lol/tierlist/?tier=challenger"
    html = fetch_html(url)
    if not html:
        print("ERROR: No se pudo obtener la tierlist")
        return []
    
    champions = []
    seen = set()
    
    # La tierlist tiene una tabla donde cada fila representa un campeón.
    # Buscamos enlaces a builds con o sin parámetro de lane.
    # Algunos campeones tienen un enlace genérico (sin lane) que redirige a su lane principal.
    
    # Patrón 1: Enlace sin lane (lane principal por defecto)
    for match in re.finditer(r'href="(/es/lol/([^/]+)/build/\?tier=challenger)"', html):
        name = match.group(2)
        if name not in seen:
            seen.add(name)
            champions.append((name, None))
    
    # Si no encontramos suficientes, buscar con lane explícita
    if len(champions) < 50:
        for match in re.finditer(r'href="(/es/lol/([^/]+)/build/\?lane=([a-z]+)&tier=challenger)"', html):
            name = match.group(2)
            lane = match.group(3)
            if name not in seen:
                seen.add(name)
                champions.append((name, lane))
    
    print(f"  -> {len(champions)} campeones encontrados")
    return champions


def get_champion_lane(champ_name):
    """Obtiene la lane principal de un campeón visitando su página."""
    url = f"{BASE_URL}/es/lol/{champ_name}/build/?tier=challenger"
    html = fetch_html(url)
    if not html:
        return None
    
    # Buscar los enlaces de lane en la parte superior
    # Ejemplo: <a href="/es/lol/jax/build/?lane=jungle&tier=challenger" ...>20.4%</a>
    lanes = []
    for match in re.finditer(r'href="/es/lol/' + re.escape(champ_name) + r'/build/\?lane=([a-z]+)&tier=challenger"[^>]*>.*?([\d.]+)%', html, re.DOTALL):
        lane = match.group(1)
        pct = float(match.group(2))
        lanes.append((lane, pct))
    
    if lanes:
        # Ordenar por porcentaje descendente y devolver el primero
        lanes.sort(key=lambda x: -x[1])
        return lanes[0][0]
    
    # Fallback: buscar en el HTML la lane actual
    lane_match = re.search(r'<div class="text-center"[^>]*>\s*<!--t=\w+-->([a-z]+)<!---->\s*</div>', html)
    if lane_match:
        return lane_match.group(1)
    
    return None


def main():
    OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
    
    # Cargar índice de items
    print("=" * 60)
    print("Cargando índice de items...")
    print("=" * 60)
    items_index = load_items_index()
    print(f"  -> {len(items_index)} items cargados")
    
    # Obtener lista de campeones
    print("\n" + "=" * 60)
    champions = get_champion_list_from_tierlist()
    if not champions:
        print("ERROR: No se encontraron campeones. Abortando.")
        return
    
    # 2. Para cada campeón, obtener su build
    print("\n" + "=" * 60)
    print("PASO 2: Scrapeando builds")
    print("=" * 60)
    
    builds_data = {}
    skipped = []
    
    for i, (champ_name, lane_hint) in enumerate(champions):
        print(f"\n  {i+1}/{len(champions)}: {champ_name}...", end=" ")
        
        # Si no tenemos lane, obtenerla
        if not lane_hint:
            lane = get_champion_lane(champ_name)
            if not lane:
                print("SKIP (sin lane)")
                skipped.append(champ_name)
                continue
        else:
            lane = lane_hint
        
        # Construir URL
        url = f"{BASE_URL}/es/lol/{champ_name}/build/?tier=challenger&lane={lane}"
        html = fetch_html(url)
        if not html:
            print("SKIP (no HTML)")
            skipped.append(champ_name)
            continue
        
        # Parsear build
        build = parse_build_page(html, items_index)
        if not build or not build.get("starting_items", {}).get("items"):
            print("SKIP (sin datos de build)")
            skipped.append(champ_name)
            continue
        
        builds_data[champ_name] = {
            "lane": lane,
            **build
        }
        print(f"OK (lane={lane}, items={len(build['starting_items']['items'])}+{len(build['core_build'])})")
        
        time.sleep(SLEEP)
    
    print(f"\n-> {len(builds_data)} builds válidos, {len(skipped)} skipped")
    
    # 3. Guardar JSON
    print("\n" + "=" * 60)
    print("PASO 3: Guardando JSON")
    print("=" * 60)
    
    result = {
        "metadata": {
            "source": "lolalytics.com",
            "tier": "challenger",
            "patch": "unknown",
            "scraped_at": time.strftime("%Y-%m-%d"),
            "total_champions": len(builds_data)
        },
        "builds": builds_data
    }
    
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Listo!")
    print(f"  {len(builds_data)} builds -> {OUTPUT_JSON}")
    
    if builds_data:
        first = next(iter(builds_data.values()))
        print(f"\nEjemplo (primer build):")
        print(json.dumps(first, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
