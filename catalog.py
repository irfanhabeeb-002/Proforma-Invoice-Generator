"""
Product catalog and price list for Electrogen Proforma Invoice Generator.
All rates are basic rates in INR (₹), excluding GST.
"""

CATALOG = {
    "Energy meters": {
        "default_gst": 18.0,
        "default_hsn": "90280310",
        "items": [
            {"name": "3 Phase Net", "brand": "VisionTek", "hsn": "90280310", "rate": 5508.47},
            {"name": "3 Phase Net", "brand": "L&T", "hsn": "90280310", "rate": 8475.57},
            {"name": "3 Phase Uni", "brand": "VisionTek", "hsn": "90280310", "rate": 3347.45},
            {"name": "3 Phase Uni", "brand": "L&T", "hsn": "90280310", "rate": 4661.01},
            {"name": "HT Bi", "brand": "L&T", "hsn": "90280310", "rate": 50000.00},
            {"name": "HT Uni", "brand": "L&T", "hsn": "90280310", "rate": 36600.00},
            {"name": "LT BI", "brand": "VisionTek", "hsn": "90280310", "rate": 12205.08},
            {"name": "LT BI", "brand": "L&T", "hsn": "90280310", "rate": 19305.08},
            {"name": "LT UNI", "brand": "VisionTek", "hsn": "90280310", "rate": 12105.08},
            {"name": "LT UNI", "brand": "L&T", "hsn": "90280310", "rate": 16525.42},
            {"name": "Single Net", "brand": "VisionTek", "hsn": "90280310", "rate": 2627.11},
            {"name": "Single Phase Net", "brand": "L&T", "hsn": "90280310", "rate": 3156.77},
            {"name": "Single Phase Uni", "brand": "VisionTek", "hsn": "90280310", "rate": 1186.44},
            {"name": "Single Phase Uni", "brand": "L&T", "hsn": "90280310", "rate": 1419.49},
        ],
    },
    "Current transformers (CT)": {
        "default_gst": 18.0,
        "default_hsn": "85043100",
        "items": [
            {"name": "CT 75/5", "brand": "Ori-gen", "hsn": "85043100", "rate": 0.00},
            {"name": "CT 100/5", "brand": "Ori-gen", "hsn": "85043100", "rate": 1775.00},
            {"name": "CT 125/5", "brand": "Ori-gen", "hsn": "85043100", "rate": 0.00},
            {"name": "CT 150/5", "brand": "Ori-gen", "hsn": "85043100", "rate": 1675.00},
            {"name": "CT 200/5", "brand": "Ori-gen", "hsn": "85043100", "rate": 1575.00},
            {"name": "CT 250/5", "brand": "Ori-gen", "hsn": "85043100", "rate": 1575.00},
            {"name": "CT 500/5", "brand": "Ori-gen", "hsn": "85043100", "rate": 0.00},
        ],
    },
    "Water meter": {
        "default_gst": 18.0,
        "default_hsn": "",
        "items": [
            {"name": "Water Meter 15 MM", "brand": "Everest", "hsn": "", "rate": 0.00},
        ],
    },
    "VisionTek solar inverters": {
        "default_gst": 5.0,
        "default_hsn": "85044010",
        "items": [
            {"name": "Inverter 1 PH 3 KW SOLAR", "brand": "VisionTek", "hsn": "85044010", "rate": 14600.00},
            {"name": "Inverter 1 PH 5 KW SOLAR", "brand": "VisionTek", "hsn": "85044010", "rate": 23900.00},
            {"name": "Inverter 3 PH 6 KW SOLAR", "brand": "VisionTek", "hsn": "85044010", "rate": 40000.00},
            {"name": "Inverter 3 PH 8 KW SOLAR", "brand": "VisionTek", "hsn": "85044010", "rate": 44000.00},
            {"name": "Inverter 3 PH 10 KW SOLAR", "brand": "VisionTek", "hsn": "85044010", "rate": 46500.00},
        ],
    },
    "Hoymiles hybrid inverters": {
        "default_gst": 5.0,
        "default_hsn": "85044010",
        "items": [
            {
                "name": "HIS-3L-G3S – Single-Phase Hybrid Inverter (IP66, Double MPPT Tracker, Ultra-slim 99 mm Thickness)",
                "brand": "Hoymiles",
                "hsn": "85044010",
                "rate": 73000.00,
            },
            {
                "name": "HIS-5L-G3S – Single-Phase Hybrid Inverter (IP66, Double MPPT Tracker, Ultra-slim 99 mm Thickness)",
                "brand": "Hoymiles",
                "hsn": "85044010",
                "rate": 79000.00,
            },
            {
                "name": "HIT-5L-G3S – Three-Phase Hybrid Inverter (IP66, Double MPPT Tracker)",
                "brand": "Hoymiles",
                "hsn": "85044010",
                "rate": 157000.00,
            },
            {
                "name": "HIT-10L-G3S – Three-Phase Hybrid Inverter (IP66, Three MPPT Trackers)",
                "brand": "Hoymiles",
                "hsn": "85044010",
                "rate": 189000.00,
            },
            {
                "name": "HIT-15L-G3S – Three-Phase Hybrid Inverter (IP66, Four MPPT Trackers)",
                "brand": "Hoymiles",
                "hsn": "85044010",
                "rate": 212000.00,
            },
            {
                "name": "HIT-20L-G3S – Three-Phase Hybrid Inverter (IP66, Four MPPT Trackers)",
                "brand": "Hoymiles",
                "hsn": "85044010",
                "rate": 257000.00,
            },
        ],
    },
    "Hoymiles batteries": {
        "default_gst": 18.0,
        "default_hsn": "85076000",
        "items": [
            {
                "name": "LB-6D-G3 – Battery (IP65, 314 Ah Cells, 8,000 Cycles, Built-in DC Breaker)",
                "brand": "Hoymiles",
                "hsn": "85076000",
                "rate": 97000.00,
            },
            {
                "name": "LB-16D-G3 – Battery (IP65, 314 Ah Cells, 8,000 Cycles, Built-in DC Breaker)",
                "brand": "Hoymiles",
                "hsn": "85076000",
                "rate": 208000.00,
            },
        ],
    },
    "Ori-gen stainless steel water tanks": {
        "default_gst": 18.0,
        "default_hsn": "73090010",
        "items": [
            {"name": "SS Water Tank 650 LTR 0.6MM (304 Grade)", "brand": "Ori-gen", "hsn": "73090010", "rate": 22033.89},
            {"name": "SS Water Tank 1200 LTR 0.6MM (304 Grade)", "brand": "Ori-gen", "hsn": "73090010", "rate": 25000.00},
            {"name": "SS Water Tank 1200 LTR 0.8MM (304 Grade)", "brand": "Ori-gen", "hsn": "73090010", "rate": 32118.64},
            {"name": "SS Water Tank 1500 LTR 0.6MM (304 Grade)", "brand": "Ori-gen", "hsn": "73090010", "rate": 33898.30},
            {"name": "SS Water Tank 1500 LTR 0.8MM (304 Grade)", "brand": "Ori-gen", "hsn": "73090010", "rate": 40254.23},
            {"name": "SS Water Tank 2000 LTR 0.8MM (304 Grade)", "brand": "Ori-gen", "hsn": "73090010", "rate": 50423.72},
            {"name": "SS Water Tank 1200 LTR 0.6MM (316 Grade)", "brand": "Ori-gen", "hsn": "73090010", "rate": 31779.66},
            {"name": "SS Water Tank 1500 LTR 0.6MM (316 Grade)", "brand": "Ori-gen", "hsn": "73090010", "rate": 42796.61},
        ],
    },
    "Solar panel": {
        "default_gst": 5.0,
        "default_hsn": "85414300",
        "items": [
            {
                "name": "VisionTek Bifacial Mono DCR 535 W Solar Panel",
                "brand": "VisionTek",
                "hsn": "85414300",
                "rate": 12305.00,
            },
        ],
    },
    "Water level controller": {
        "default_gst": 18.0,
        "default_hsn": "",
        "items": [
            {"name": "Water Level Controller", "brand": "Electrogen", "hsn": "", "rate": 0.00},
        ],
    },
}

CATEGORIES = list(CATALOG.keys())

CUSTOM_OPTION = "➕ Custom / Enter Manually"

def get_product_display_label(item: dict) -> str:
    """Format label for selectbox dropdown."""
    brand = item.get("brand", "")
    name = item.get("name", "")
    rate = item.get("rate", 0.0)
    rate_str = f"₹{rate:,.2f}" if rate > 0 else "₹0.00 (Price on request)"
    
    if brand and brand.lower() not in name.lower():
        return f"{name} ({brand})  |  {rate_str}"
    return f"{name}  |  {rate_str}"

def get_product_invoice_description(item: dict) -> str:
    """Format description for invoice line item."""
    brand = item.get("brand", "")
    name = item.get("name", "")
    if brand and brand.lower() not in name.lower():
        return f"{name} ({brand})"
    return name
