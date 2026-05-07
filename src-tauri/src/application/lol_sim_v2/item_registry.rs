use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::OnceLock;

// ── Wiki JSON format ──

#[derive(Debug, Clone, Deserialize)]
struct WikiItemJson {
    name: String,
    #[serde(default)]
    id: i64,
    total_cost: f64,
    sell_value: f64,
    #[serde(default)]
    components: Vec<String>,
    #[serde(default)]
    stats: HashMap<String, f64>,
    #[serde(default)]
    image_url: String,
    #[serde(default)]
    tags: Vec<String>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ItemStats {
    pub flat_hp: f64,
    pub flat_mp: f64,
    pub flat_ad: f64,
    pub flat_ap: f64,
    pub flat_armor: f64,
    pub flat_mr: f64,
    pub flat_ms: f64,
    pub percent_ms: f64,
    pub flat_as: f64,
    pub percent_as: f64,
    pub flat_crit_chance: f64,
    pub flat_crit_damage: f64,
    pub flat_lethality: f64,
    pub flat_armor_pen: f64,
    pub percent_armor_pen: f64,
    pub flat_magic_pen: f64,
    pub percent_magic_pen: f64,
    pub flat_ah: f64,
    pub percent_life_steal: f64,
    pub percent_omnivamp: f64,
    pub flat_hp_regen: f64,
    pub percent_hp_regen: f64,
    pub flat_mp_regen: f64,
    pub percent_mp_regen: f64,
    pub flat_tenacity: f64,
}

impl ItemStats {
    pub fn from_wiki_map(map: &HashMap<String, f64>) -> Self {
        let mut stats = ItemStats::default();
        for (key, value) in map {
            match key.as_str() {
                "hp" => stats.flat_hp = *value,
                "mana" => stats.flat_mp = *value,
                "ad" => stats.flat_ad = *value,
                "ap" => stats.flat_ap = *value,
                "armor" => stats.flat_armor = *value,
                "mr" => stats.flat_mr = *value,
                "attack_speed" => stats.percent_as = *value,
                "crit_chance" => stats.flat_crit_chance = *value,
                "crit_damage" => stats.flat_crit_damage = *value,
                "lethality" => stats.flat_lethality = *value,
                "armor_pen" => {
                    if *value < 1.0 {
                        stats.percent_armor_pen = *value;
                    } else {
                        stats.flat_armor_pen = *value;
                    }
                }
                "magic_pen" => {
                    if *value < 1.0 {
                        stats.percent_magic_pen = *value;
                    } else {
                        stats.flat_magic_pen = *value;
                    }
                }
                "ability_haste" => stats.flat_ah = *value,
                "life_steal" => stats.percent_life_steal = *value,
                "omnivamp" => stats.percent_omnivamp = *value,
                "hp_regen" => stats.percent_hp_regen = *value,
                "mp_regen" => stats.percent_mp_regen = *value,
                "tenacity" => stats.flat_tenacity = *value,
                "movement_speed" => {
                    if *value > 5.0 {
                        stats.flat_ms = *value;
                    } else {
                        stats.percent_ms = *value;
                    }
                }
                _ => {}
            }
        }
        stats
    }

    pub fn add(&mut self, other: &ItemStats) {
        self.flat_hp += other.flat_hp;
        self.flat_mp += other.flat_mp;
        self.flat_ad += other.flat_ad;
        self.flat_ap += other.flat_ap;
        self.flat_armor += other.flat_armor;
        self.flat_mr += other.flat_mr;
        self.flat_ms += other.flat_ms;
        self.percent_ms += other.percent_ms;
        self.flat_as += other.flat_as;
        self.percent_as += other.percent_as;
        self.flat_crit_chance += other.flat_crit_chance;
        self.flat_crit_damage += other.flat_crit_damage;
        self.flat_lethality += other.flat_lethality;
        self.flat_armor_pen += other.flat_armor_pen;
        self.percent_armor_pen += other.percent_armor_pen;
        self.flat_magic_pen += other.flat_magic_pen;
        self.percent_magic_pen += other.percent_magic_pen;
        self.flat_ah += other.flat_ah;
        self.percent_life_steal += other.percent_life_steal;
        self.percent_omnivamp += other.percent_omnivamp;
        self.flat_hp_regen += other.flat_hp_regen;
        self.percent_hp_regen += other.percent_hp_regen;
        self.flat_mp_regen += other.flat_mp_regen;
        self.percent_mp_regen += other.percent_mp_regen;
        self.flat_tenacity += other.flat_tenacity;
    }
}

#[derive(Debug, Clone)]
pub struct ItemDefinition {
    pub id: String,
    pub name: String,
    pub total_cost: i64,
    pub recipe_cost: i64,
    pub sell_value: i64,
    pub purchasable: bool,
    pub components: Vec<String>,
    pub stats: ItemStats,
    pub tags: Vec<String>,
    pub depth: i32,
    pub into: Vec<String>,
    pub image_url: String,
}

pub struct ItemRegistry {
    pub items: HashMap<String, ItemDefinition>,
}

impl ItemRegistry {
    pub fn load() -> Self {
        let json_str = include_str!("../../../../data/items/items.json");
        let root: serde_json::Value = serde_json::from_str(json_str).expect("Invalid item JSON");
        let items_obj = root
            .get("items")
            .expect("Missing items field")
            .as_object()
            .expect("Items not object");

        let mut items = HashMap::new();
        for (name, value) in items_obj {
            let wiki: WikiItemJson = match serde_json::from_value(value.clone()) {
                Ok(w) => w,
                Err(e) => {
                    eprintln!("Warning: failed to parse item '{}': {}", name, e);
                    continue;
                }
            };

            let stats = ItemStats::from_wiki_map(&wiki.stats);

            // Compute depth based on component chain
            let depth = if wiki.components.is_empty() {
                0
            } else {
                1
            };

            let def = ItemDefinition {
                id: wiki.id.to_string(),
                name: wiki.name.clone(),
                total_cost: wiki.total_cost as i64,
                recipe_cost: 0, // Will be computed after all items loaded
                sell_value: wiki.sell_value as i64,
                purchasable: wiki.total_cost > 0.0,
                components: wiki.components.clone(),
                stats,
                tags: wiki.tags.clone(),
                depth,
                into: Vec::new(),
                image_url: wiki.image_url.clone(),
            };
            items.insert(name.clone(), def);
        }

        // Second pass: compute recipe_cost and into
        let mut recipe_costs: HashMap<String, i64> = HashMap::new();
        for (name, def) in &items {
            let components_total: i64 = def
                .components
                .iter()
                .filter_map(|c| items.get(c).map(|d| d.total_cost))
                .sum();
            let recipe = (def.total_cost - components_total).max(0);
            recipe_costs.insert(name.clone(), recipe);
        }

        // Build into map
        let mut into_map: HashMap<String, Vec<String>> = HashMap::new();
        for (name, def) in &items {
            for comp in &def.components {
                into_map
                    .entry(comp.clone())
                    .or_default()
                    .push(name.clone());
            }
        }

        // Apply computed fields
        for (name, def) in items.iter_mut() {
            if let Some(cost) = recipe_costs.get(name) {
                def.recipe_cost = *cost;
            }
            if let Some(into) = into_map.get(name) {
                def.into = into.clone();
            }
        }

        Self { items }
    }

    pub fn get(&self, name: &str) -> Option<&ItemDefinition> {
        self.items.get(name)
    }

    pub fn is_boots(&self, name: &str) -> bool {
        const BOOTS: &[&str] = &[
            "Boots",
            "Berserker's Greaves",
            "Boots of Swiftness",
            "Ionian Boots of Lucidity",
            "Mercury's Treads",
            "Plated Steelcaps",
            "Sorcerer's Shoes",
            "Symbiotic Soles",
            "Synchronized Souls",
            "Zephyr",
        ];
        BOOTS.contains(&name)
    }
}

static ITEM_REGISTRY: OnceLock<ItemRegistry> = OnceLock::new();

pub fn item_registry() -> &'static ItemRegistry {
    ITEM_REGISTRY.get_or_init(|| ItemRegistry::load())
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct InventorySlot {
    pub item_name: String,
    pub is_component: bool,
}

impl InventorySlot {
    pub fn definition(&self) -> Option<&'static ItemDefinition> {
        item_registry().get(&self.item_name)
    }
}

pub fn inventory_total_value(inventory: &[InventorySlot]) -> i64 {
    inventory
        .iter()
        .filter_map(|slot| slot.definition())
        .map(|def| def.total_cost)
        .sum()
}

pub fn inventory_total_stats(inventory: &[InventorySlot]) -> ItemStats {
    let mut total = ItemStats::default();
    for slot in inventory {
        if let Some(def) = slot.definition() {
            total.add(&def.stats);
        }
    }
    total
}

/// Returns the next item/component a champion should buy given their build plan,
/// current inventory, and available gold. Buys the most expensive component
/// they can afford, prioritizing completing items.
pub fn get_next_purchase(
    plan: &[&str; 6],
    inventory: &[InventorySlot],
    gold: i64,
) -> Option<String> {
    let registry = item_registry();

    for target_name in plan {
        if target_name.is_empty() {
            continue;
        }

        // Skip if already fully owned
        let already_owned = inventory.iter().any(|s| s.item_name == *target_name && !s.is_component);
        if already_owned {
            continue;
        }

        let target = match registry.get(target_name) {
            Some(t) => t,
            None => continue,
        };

        // Check if we can afford the full item
        if target.total_cost <= gold {
            // Check if we own all components
            let owned_components: Vec<&str> = inventory
                .iter()
                .filter(|s| s.is_component)
                .map(|s| s.item_name.as_str())
                .collect();

            let missing_components: Vec<&String> = target
                .components
                .iter()
                .filter(|c| !owned_components.contains(&c.as_str()))
                .collect();

            if missing_components.is_empty() {
                return Some(target_name.to_string());
            }
        }

        // Otherwise, try to buy the most expensive missing component we can afford
        let owned_names: Vec<&str> = inventory.iter().map(|s| s.item_name.as_str()).collect();

        let mut missing: Vec<&ItemDefinition> = target
            .components
            .iter()
            .filter(|c| !owned_names.contains(&c.as_str()))
            .filter_map(|c| registry.get(c))
            .collect();

        missing.sort_by(|a, b| b.total_cost.cmp(&a.total_cost));

        for comp in &missing {
            if comp.total_cost <= gold {
                return Some(comp.name.clone());
            }
        }

        // If we can't afford any component of this item, try saving for the most expensive missing component
        // (return it so the caller knows what to save for)
        if let Some(first_missing) = missing.first() {
            if gold < first_missing.total_cost {
                // Don't return here; continue to next plan item if this one is too expensive
                // But actually we should keep trying other plan items
            }
        }
    }

    // Fallback: save for the first unowned item's most expensive component
    for target_name in plan {
        if target_name.is_empty() {
            continue;
        }
        let already_owned = inventory.iter().any(|s| s.item_name == *target_name && !s.is_component);
        if already_owned {
            continue;
        }
        let target = registry.get(target_name)?;
        let owned_names: Vec<&str> = inventory.iter().map(|s| s.item_name.as_str()).collect();
        let missing: Vec<&ItemDefinition> = target
            .components
            .iter()
            .filter(|c| !owned_names.contains(&c.as_str()))
            .filter_map(|c| registry.get(c))
            .collect();
        if let Some(first) = missing.first() {
            return Some(first.name.clone());
        }
        // No components needed, return the item itself
        return Some(target_name.to_string());
    }

    None
}
