# Sistema de Items y Combate / Item System & Combat

## 🇪🇸 Español

### 1. Sistema de Items
- **Fuente de datos**: JSON scrapeado de la wiki de LoL (`data/items/items.json`) con 194 items reales.
- **Registro**: `ItemRegistry` carga todos los items con nombre, costo total, costo de receta, componentes, stats e `image_url`.
- **Compra progresiva**: `get_next_purchase()` compra primero el **componente más caro que se pueda permitir**. Cuando tiene todos los componentes y el oro suficiente, compra el item completo.
- **Inventario**: `Vec<InventorySlot>` guarda `{item_name, is_component}`.

### 2. Items Iniciales por Rol / Tipo de Daño

| Rol | Tipo de Daño | Item Inicial |
|-----|-------------|--------------|
| TOP | Físico | Doran's Shield |
| TOP | Mágico | Doran's Ring |
| JGL | — | Gustwalker Hatchling |
| MID | Físico | Doran's Blade |
| MID | Mágico | Doran's Ring |
| ADC | — | Doran's Blade |
| SUP | — | World Atlas |

### 3. Stats de Campeón

**Base** (todos los campeones):
- AD: 60
- AP: 0
- Armor: 30
- MR: 30
- AS: 1.0
- Crit Chance: 0%
- Crit Damage: 2.0x

**Bonus**: Se recalculan automáticamente desde el inventario vía `recalculate_bonus_stats()`.

### 4. Cálculos de Combate

#### Daño del auto-ataque

```
daño_base = si es mágico → total_ap() * 0.8
            si es físico  → total_ad()

multiplicador_crit = 1 + crit_chance * (crit_damage - 1)
daño_bruto = daño_base * multiplicador_crit
```

#### Mitigación

**Daño físico:**
```
armor_efectivo = max(0, armor - lethality - (armor_pen% * armor))
mitigación = 100 / (100 + armor_efectivo)
```

**Daño mágico:**
```
mr_efectivo = max(0, mr - flat_magic_pen - (magic_pen% * mr))
mitigación = 100 / (100 + mr_efectivo)
```

**Daño final:**
```
daño_final = daño_bruto * mitigación
```

#### Cooldown de ataque
```
cooldown = 1.0 / total_as()
```

#### Life Steal (robo de vida)
```
curación = daño_infligido * total_life_steal()
```

---

## 🇬🇧 English

### 1. Item System
- **Data source**: Scraped JSON from LoL wiki (`data/items/items.json`) with 194 real items.
- **Registry**: `ItemRegistry` loads all items with name, total cost, recipe cost, components, stats, and `image_url`.
- **Progressive purchasing**: `get_next_purchase()` buys the **most expensive affordable component first**. When all components are owned and enough gold is available, it buys the complete item.
- **Inventory**: `Vec<InventorySlot>` stores `{item_name, is_component}`.

### 2. Starting Items by Role / Damage Type

| Role | Damage Type | Starting Item |
|------|------------|---------------|
| TOP | Physical | Doran's Shield |
| TOP | Magical | Doran's Ring |
| JGL | — | Gustwalker Hatchling |
| MID | Physical | Doran's Blade |
| MID | Magical | Doran's Ring |
| ADC | — | Doran's Blade |
| SUP | — | World Atlas |

### 3. Champion Stats

**Base** (all champions):
- AD: 60
- AP: 0
- Armor: 30
- MR: 30
- AS: 1.0
- Crit Chance: 0%
- Crit Damage: 2.0x

**Bonus**: Automatically recalculated from inventory via `recalculate_bonus_stats()`.

### 4. Combat Calculations

#### Auto-attack damage

```
base_damage = if magical → total_ap() * 0.8
              if physical → total_ad()

crit_multiplier = 1 + crit_chance * (crit_damage - 1)
raw_damage = base_damage * crit_multiplier
```

#### Mitigation

**Physical damage:**
```
effective_armor = max(0, armor - lethality - (armor_pen% * armor))
mitigation = 100 / (100 + effective_armor)
```

**Magical damage:**
```
effective_mr = max(0, mr - flat_magic_pen - (magic_pen% * mr))
mitigation = 100 / (100 + effective_mr)
```

**Final damage:**
```
final_damage = raw_damage * mitigation
```

#### Attack cooldown
```
cooldown = 1.0 / total_as()
```

#### Life steal
```
heal = damage_dealt * total_life_steal()
```
