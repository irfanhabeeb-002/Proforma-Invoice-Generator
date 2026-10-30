"""
Quotation product catalogue for Electrogen Quotation Generator.
Separate from the Proforma Invoice catalogue.
Includes:
  - Ori-gen SS water tanks (imported from the main catalogue)
  - Domestic UPS / Home Inverters, batteries, trolleys and stands
Rate entry is manual for all UPS / battery items; tank rates are pre-filled.
"""

# ── Water Tanks (imported from catalog.py, rates pre-filled) ──────────────────
WATER_TANKS = [
    {"name": "SS Water Tank 650 LTR 0.6MM (304 Grade)",  "brand": "Ori-gen", "rate": 22033.89},
    {"name": "SS Water Tank 1200 LTR 0.6MM (304 Grade)", "brand": "Ori-gen", "rate": 25000.00},
    {"name": "SS Water Tank 1200 LTR 0.8MM (304 Grade)", "brand": "Ori-gen", "rate": 32118.64},
    {"name": "SS Water Tank 1500 LTR 0.6MM (304 Grade)", "brand": "Ori-gen", "rate": 33898.30},
    {"name": "SS Water Tank 1500 LTR 0.8MM (304 Grade)", "brand": "Ori-gen", "rate": 40254.23},
    {"name": "SS Water Tank 2000 LTR 0.8MM (304 Grade)", "brand": "Ori-gen", "rate": 50423.72},
    {"name": "SS Water Tank 1200 LTR 0.6MM (316 Grade)", "brand": "Ori-gen", "rate": 31779.66},
    {"name": "SS Water Tank 1500 LTR 0.6MM (316 Grade)", "brand": "Ori-gen", "rate": 42796.61},
]

# ── Home / Domestic UPS (Inverters) ──────────────────────────────────────────
HOME_UPS = [
    {"name": "600VA 12V Home UPS",         "brand": "", "rate": 0.0},
    {"name": "800VA 12V Home UPS",         "brand": "", "rate": 0.0},
    {"name": "1KVA 12V Home UPS",          "brand": "", "rate": 0.0},
    {"name": "1.5KVA 24V Home UPS",        "brand": "", "rate": 0.0},
    {"name": "2KVA 24V Home UPS",          "brand": "", "rate": 0.0},
    {"name": "2.5KVA 24V Home UPS",        "brand": "", "rate": 0.0},
    {"name": "3KVA 24V Home UPS",          "brand": "", "rate": 0.0},
    {"name": "4KVA 36V Home UPS",          "brand": "", "rate": 0.0},
    {"name": "5KVA 48V Home UPS",          "brand": "", "rate": 0.0},
    {"name": "7.5KVA 96V Home UPS",        "brand": "", "rate": 0.0},
    {"name": "10KVA 120V Home UPS",        "brand": "", "rate": 0.0},
]

# ── Tubular / SMF Batteries ───────────────────────────────────────────────────
BATTERIES = [
    {"name": "100AH 12V Tubular Battery",  "brand": "", "rate": 0.0},
    {"name": "120AH 12V Tubular Battery",  "brand": "", "rate": 0.0},
    {"name": "150AH 12V Tubular Battery",  "brand": "", "rate": 0.0},
    {"name": "180AH 12V Tubular Battery",  "brand": "", "rate": 0.0},
    {"name": "200AH 12V Tubular Battery",  "brand": "", "rate": 0.0},
    {"name": "220AH 12V Tubular Battery",  "brand": "", "rate": 0.0},
    {"name": "100AH 12V SMF Battery",      "brand": "", "rate": 0.0},
    {"name": "150AH 12V SMF Battery",      "brand": "", "rate": 0.0},
    {"name": "200AH 12V SMF Battery",      "brand": "", "rate": 0.0},
]

# ── Trolleys & Stands ─────────────────────────────────────────────────────────
TROLLEYS = [
    {"name": "Battery Trolley (1 Battery)",  "brand": "", "rate": 0.0},
    {"name": "Battery Trolley (2 Battery)",  "brand": "", "rate": 0.0},
    {"name": "Battery Trolley (4 Battery)",  "brand": "", "rate": 0.0},
    {"name": "Battery Stand (2 Battery)",    "brand": "", "rate": 0.0},
    {"name": "Battery Stand (4 Battery)",    "brand": "", "rate": 0.0},
]

# ── Master catalogue keyed by category ───────────────────────────────────────
QUOTE_CATALOG = {
    "Home UPS / Inverter": {
        "items": HOME_UPS,
        "manual_rate": True,   # rates must be entered manually
    },
    "Battery": {
        "items": BATTERIES,
        "manual_rate": True,
    },
    "Trolley / Stand": {
        "items": TROLLEYS,
        "manual_rate": True,
    },
    "SS Water Tank (Ori-gen)": {
        "items": WATER_TANKS,
        "manual_rate": False,  # rates pre-filled; can still be overridden
    },
}

QUOTE_CATEGORIES = list(QUOTE_CATALOG.keys())
QUOTE_CUSTOM_OPTION = "➕ Custom / Enter Manually"


def get_quote_display_label(item: dict) -> str:
    """Dropdown label for quotation product selectbox."""
    name = item.get("name", "")
    brand = item.get("brand", "")
    rate = item.get("rate", 0.0)
    prefix = f"{name} ({brand})" if brand else name
    rate_str = f"₹{rate:,.2f}" if rate > 0 else "Price on request"
    return f"{prefix}  |  {rate_str}"


def get_quote_invoice_description(item: dict) -> str:
    """Description string written on the quotation line item."""
    name = item.get("name", "")
    brand = item.get("brand", "")
    if brand and brand.lower() not in name.lower():
        return f"{name} ({brand})"
    return name
