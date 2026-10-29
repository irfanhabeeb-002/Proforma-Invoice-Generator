import io
import base64
import re
import html
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, ROUND_CEILING
from pathlib import Path

import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from streamlit_pdf_viewer import pdf_viewer

from catalog import (
    CATALOG,
    CATEGORIES,
    CUSTOM_OPTION,
    get_product_display_label,
    get_product_invoice_description,
)

BASE_DIR = Path(__file__).resolve().parent
BRAND_TEAL = colors.HexColor("#006A67")
BORDER = colors.HexColor("#222222")
GSTIN = "32AADFE7851L1ZA"
BANK_NAME = "Electrogen Industries"
ACCOUNT_NO = "12950200004713"
BANK_BRANCH = "Lulu Mall"
IFSC = "FDRL0002031"
SIGNATORY = "Viji Thomas"
SIGNATURE_PATH = BASE_DIR / "authorised_signature.png"
LOGO_PATH = BASE_DIR / "ElectrogenLogo.png"
FONT_PATH = BASE_DIR / "DejaVuSans.ttf"

# Register DejaVu Sans font for Indian Rupee (₹) glyph support in ReportLab
pdfmetrics.registerFont(TTFont("ElectrogenSans", str(FONT_PATH)))
pdfmetrics.registerFont(TTFont("ElectrogenSans-Bold", str(FONT_PATH)))

st.set_page_config(
    page_title="Electrogen — Proforma Invoice Generator",
    page_icon="🧾",
    layout="wide",
)

# Custom CSS:
# 1. Eliminate blinking cursor from selectbox inputs (Category, Product, GST rate)
# 2. Hide + and - stepper buttons from number inputs
# 3. Style automatic HSN/SAC and Rate read-only fields cleanly without cursors
st.markdown(
    """
    <style>
    /* Remove blinking cursor from selectbox inputs (Category, Product, GST rate) */
    div[data-testid="stSelectbox"] input,
    div[data-baseweb="select"] input,
    div[data-baseweb="select"] [role="combobox"] {
        caret-color: transparent !important;
        cursor: pointer !important;
    }

    /* Hide + and - stepper buttons in number inputs */
    button[data-testid="stNumberInputStepDown"],
    button[data-testid="stNumberInputStepUp"] {
        display: none !important;
    }

    /* Remove native browser spin buttons */
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { 
        -webkit-appearance: none !important;
        margin: 0 !important;
    }
    input[type=number] {
        -moz-appearance: textfield !important;
    }

    /* Clean styling for automatic display boxes */
    .auto-field-label {
        font-size: 0.85rem;
        font-weight: 500;
        color: #31333F;
        margin-bottom: 4px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .auto-field-box {
        background-color: #F8FAFA;
        border: 1px solid #D0DCDC;
        border-radius: 6px;
        padding: 0 12px;
        height: 40px;
        display: flex;
        align-items: center;
        user-select: none;
        caret-color: transparent !important;
        cursor: default;
    }
    .auto-field-val {
        font-size: 0.95rem;
        font-weight: 600;
        color: #111827;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .auto-field-val-teal {
        font-size: 1.0rem;
        font-weight: 700;
        color: #006A67;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .auto-field-val-muted {
        font-size: 0.9rem;
        font-weight: 400;
        color: #888888;
        font-style: italic;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

today = date.today()
pi_no = f"Electrogen/{str(today.year)[-2:]}"

# Helper financial math functions
def money(value):
    return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def fmt(value):
    return f"{money(value):,.2f}"

def safe_filename(value):
    value = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip())
    return value.strip("_") or "Customer"

def P(text, style):
    return Paragraph(text, style)

# PDF Generation Function
def make_pdf(customer, items):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=13 * mm,
        bottomMargin=13 * mm,
        title=f"Proforma Invoice {pi_no}",
        author="Electrogen Industries",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="InvTitleR", fontName="ElectrogenSans-Bold", fontSize=14, leading=17,
                              textColor=colors.white, alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name="InvSubR", fontName="ElectrogenSans-Bold", fontSize=8.5, leading=11,
                              textColor=colors.white, alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name="InvTitleC", fontName="ElectrogenSans-Bold", fontSize=15, leading=18,
                              textColor=colors.white, alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="InvSubC", fontName="ElectrogenSans-Bold", fontSize=9, leading=11,
                              textColor=colors.white, alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="Section", fontName="ElectrogenSans-Bold", fontSize=10, leading=12,
                              textColor=colors.white, leftIndent=5))
    styles.add(ParagraphStyle(name="BodyE", fontName="ElectrogenSans", fontSize=9, leading=12))
    styles.add(ParagraphStyle(name="SmallE", fontName="ElectrogenSans", fontSize=8, leading=10))
    styles.add(ParagraphStyle(name="SmallBoldE", fontName="ElectrogenSans-Bold", fontSize=8, leading=10))
    styles.add(ParagraphStyle(name="CellE", fontName="ElectrogenSans", fontSize=7.5, leading=9.5))
    styles.add(ParagraphStyle(name="CellBoldE", fontName="ElectrogenSans-Bold", fontSize=7.5, leading=9.5))
    styles.add(ParagraphStyle(name="CellWhiteE", fontName="ElectrogenSans-Bold", fontSize=7.5, leading=9.5,
                              textColor=colors.white, alignment=TA_CENTER))

    story = []

    # Header with Logo
    if LOGO_PATH.exists():
        logo = Image(str(LOGO_PATH), width=48 * mm, height=14.6 * mm, kind="proportional")
        logo.hAlign = "LEFT"
        header_text = [
            P("PROFORMA INVOICE", styles["InvTitleR"]),
            P(f"GSTIN: {html.escape(GSTIN)}", styles["InvSubR"]),
        ]
        header = Table([[logo, header_text]], colWidths=[55 * mm, 123 * mm], rowHeights=[17 * mm])
        header.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BRAND_TEAL),
            ("BOX", (0, 0), (-1, -1), 1, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
    else:
        header = Table([
            [P("PROFORMA INVOICE", styles["InvTitleC"])],
            [P(f"GSTIN: {html.escape(GSTIN)}", styles["InvSubC"])],
        ], colWidths=[178 * mm], rowHeights=[10 * mm, 7 * mm])
        header.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BRAND_TEAL),
            ("BOX", (0, 0), (-1, -1), 1, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))

    story += [header, Spacer(1, 10 * mm)]

    # Bill To Box
    bill = Table([[
        P("BILL TO", styles["Section"]),
        "",
        P(f"<b>Date:</b> {today.strftime('%d.%m.%Y')}<br/><b>P.I No:</b> {html.escape(pi_no)}", styles["SmallBoldE"]),
    ]], colWidths=[50 * mm, 63 * mm, 65 * mm])
    bill.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), BRAND_TEAL),
        ("BOX", (0, 0), (0, 0), 0.8, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story += [bill, Spacer(1, 3 * mm), P(html.escape(customer), styles["BodyE"]), Spacer(1, 5 * mm)]

    # Items Table (GST column removed; GST percentage is shown in the GST Total row)
    data = [[
        P("Sl.<br/>No", styles["CellWhiteE"]),
        P("Description of Goods", styles["CellWhiteE"]),
        P("HSN/SAC", styles["CellWhiteE"]),
        P("Rate (₹)", styles["CellWhiteE"]),
        P("Quantity", styles["CellWhiteE"]),
        P("Total (₹)", styles["CellWhiteE"]),
    ]]

    subtotal = Decimal("0.00")
    tax_by_rate = {}

    for idx, item in enumerate(items, 1):
        line = money(Decimal(str(item["rate"])) * Decimal(str(item["quantity"])))
        r = float(item["gst"])
        tax = money(line * Decimal(str(r)) / Decimal("100"))
        subtotal += line
        tax_by_rate[r] = tax_by_rate.get(r, Decimal("0.00")) + tax
        data.append([
            P(str(idx), styles["CellE"]),
            P(html.escape(item["description"]).replace("\n", "<br/>"), styles["CellE"]),
            P(html.escape(item["hsn"] or "-"), styles["CellE"]),
            P(fmt(item["rate"]), styles["CellE"]),
            P(str(item["quantity"]), styles["CellE"]),
            P(fmt(line), styles["CellE"]),
        ])

    tax_total = sum(tax_by_rate.values(), Decimal("0.00"))
    raw_grand_total = subtotal + tax_total
    # Ceiling round: add paisas to eliminate trailing decimals and round to next whole rupee (.00)
    grand_total = money(raw_grand_total.to_integral_value(rounding=ROUND_CEILING))
    round_off = grand_total - raw_grand_total

    data.append(["", P("Subtotal", styles["CellBoldE"]), "", "", "", P(fmt(subtotal), styles["CellBoldE"])])

    if len(tax_by_rate) == 1:
        rate_pct = list(tax_by_rate.keys())[0]
        data.append(["", P(f"GST Total ({rate_pct:g}%)", styles["CellBoldE"]), "", "", "", P(fmt(tax_total), styles["CellBoldE"])])
        summary_rows_count = 2
    else:
        for rate_pct, tax_amt in sorted(tax_by_rate.items()):
            data.append(["", P(f"GST ({rate_pct:g}%)", styles["CellBoldE"]), "", "", "", P(fmt(tax_amt), styles["CellBoldE"])])
        data.append(["", P("GST Total", styles["CellBoldE"]), "", "", "", P(fmt(tax_total), styles["CellBoldE"])])
        summary_rows_count = 1 + len(tax_by_rate)

    if round_off > 0:
        data.append(["", P("Round Off", styles["CellBoldE"]), "", "", "", P(f"+{fmt(round_off)}", styles["CellBoldE"])])
        summary_rows_count += 1

    data.append(["", P("Grand Total", styles["CellBoldE"]), "", "", "", P(fmt(grand_total), styles["CellBoldE"])])
    summary_rows_count += 1

    table = Table(data, colWidths=[10 * mm, 68 * mm, 25 * mm, 25 * mm, 20 * mm, 30 * mm], repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_TEAL),
        ("GRID", (0, 0), (-1, -1), 0.7, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("BACKGROUND", (0, -summary_rows_count), (-1, -1), colors.HexColor("#F0F5F5")),
        ("LINEABOVE", (0, -1), (-1, -1), 1.2, BORDER),
    ]))
    story += [table, Spacer(1, 9 * mm), P("Kindly make the payment to the following bank account.", styles["BodyE"]), Spacer(1, 6 * mm)]

    # Bank Details
    bank_data = [
        [P("Bank Details", styles["CellWhiteE"]), "", "", ""],
        [P("Federal Bank", styles["CellWhiteE"]), "", "", ""],
        [P("Name", styles["CellBoldE"]), P(html.escape(BANK_NAME), styles["CellE"]), P("AC No.", styles["CellBoldE"]), P(html.escape(ACCOUNT_NO), styles["CellE"])],
        [P("Branch", styles["CellBoldE"]), P(html.escape(BANK_BRANCH), styles["CellE"]), P("IFSC Code", styles["CellBoldE"]), P(html.escape(IFSC), styles["CellE"])],
    ]
    bank = Table(bank_data, colWidths=[18 * mm, 70 * mm, 25 * mm, 65 * mm], repeatRows=2)
    bank.setStyle(TableStyle([
        ("SPAN", (0, 0), (-1, 0)),
        ("SPAN", (0, 1), (-1, 1)),
        ("BACKGROUND", (0, 0), (-1, 1), BRAND_TEAL),
        ("GRID", (0, 0), (-1, -1), 0.8, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story += [
        bank,
        Spacer(1, 8 * mm),
        P("<b>Additional Info.</b>", styles["BodyE"]),
        Spacer(1, 2 * mm),
        P("• Kindly forward the transaction receipt or screenshot of the payment via email or WhatsApp.", styles["SmallE"]),
        Spacer(1, 7 * mm),
    ]

    # Authorised Signatory
    story.append(P("<b>Authorised Signatory</b>", styles["BodyE"]))
    story.append(Spacer(1, 2 * mm))

    if SIGNATURE_PATH.exists():
        signature = Image(str(SIGNATURE_PATH), width=25 * mm, height=18 * mm, kind="proportional")
        signature.hAlign = "LEFT"
        story.append(signature)
    else:
        story.append(Spacer(1, 15 * mm))

    story.append(P(f"<b>{html.escape(SIGNATORY)}</b>", styles["BodyE"]))
    doc.build(story)
    return buffer.getvalue(), float(subtotal), float(tax_total), float(grand_total)

# ---- APP HEADER UI ----
logo_b64 = ""
if LOGO_PATH.exists():
    with open(LOGO_PATH, "rb") as f:
        logo_b64 = base64.b64encode(f.read()).decode()

if logo_b64:
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #005653 0%, #006A67 100%); 
                    padding: 16px 24px; 
                    border-radius: 10px; 
                    display: flex; 
                    flex-wrap: wrap;
                    align-items: center; 
                    justify-content: space-between; 
                    margin-bottom: 24px; 
                    box-shadow: 0 4px 12px rgba(0, 106, 103, 0.2);">
            <div style="display: flex; align-items: center; gap: 18px;">
                <img src="data:image/png;base64,{logo_b64}" style="height: 46px; max-width: 190px; object-fit: contain;" />
                <div style="border-left: 2px solid rgba(255,255,255,0.3); padding-left: 16px; color: white;">
                    <div style="font-size: 1.25rem; font-weight: 700; letter-spacing: 0.5px;">Proforma Invoice Generator</div>
                    <div style="font-size: 0.82rem; opacity: 0.9;">GSTIN: {GSTIN} &nbsp;|&nbsp; Electrogen Sales Workplace</div>
                </div>
            </div>
            <div style="color: white; text-align: right; font-size: 0.85rem; opacity: 0.95;">
                <div><b>Date:</b> {today.strftime('%d.%m.%Y')}</div>
                <div><b>P.I No:</b> {pi_no}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.title("Electrogen — Proforma Invoice Generator")
    st.caption("Official Sales Workplace Proforma Invoice Generator")

# ---- SESSION STATE INITIALIZATION ----
if "customer_name" not in st.session_state:
    st.session_state["customer_name"] = ""

if "items" not in st.session_state:
    st.session_state["items"] = [
        {
            "id": 1,
            "category": None,
            "product_key": None,
            "description": "",
            "brand": "",
            "hsn": "",
            "rate": 0.0,
            "quantity": 1,
            "gst": 18.0,
            "is_custom": False,
            "edit_mode": False,
        }
    ]
    st.session_state["item_counter"] = 1

# ---- STEP 1: CUSTOMER NAME ----
st.subheader("1. Customer Information")
customer_name = st.text_input(
    "Bill To / Customer Name",
    value=st.session_state["customer_name"],
    placeholder="Enter customer or company name (e.g. WEGASOLAR RENEWABLES)",
    help="Type the customer or company name. The invoice updates live.",
)
st.session_state["customer_name"] = customer_name

st.caption(f"Invoice Date: **{today.strftime('%d.%m.%Y')}** &nbsp;·&nbsp; P.I Number: **{pi_no}**")

st.divider()

# ---- STEP 2: PRODUCTS & PARTICULARS ----
st.subheader("2. Items & Particulars")
st.caption(
    "Select a product category, then choose the product from the price list. "
    "HSN/SAC and Rate display automatically without manual typing."
)

items_to_delete = []

for idx, item in enumerate(st.session_state["items"]):
    item_id = item["id"]
    with st.container(border=True):
        col_hdr, col_del = st.columns([0.88, 0.12])
        col_hdr.markdown(f"**Item {idx + 1}**")
        if len(st.session_state["items"]) > 1:
            if col_del.button("🗑 Remove", key=f"del_{item_id}", use_container_width=True):
                items_to_delete.append(item_id)

        # Row A: Category and Product Selection
        cat_col, prod_col = st.columns([1, 2])
        
        # Category Selectbox
        current_cat = item.get("category")
        cat_index = CATEGORIES.index(current_cat) if current_cat in CATEGORIES else None
        
        selected_cat = cat_col.selectbox(
            "Category",
            options=CATEGORIES,
            index=cat_index,
            placeholder="Select product category...",
            key=f"cat_select_{item_id}",
        )

        # If category changed, reset product and apply category defaults
        if selected_cat != current_cat:
            item["category"] = selected_cat
            item["product_key"] = None
            item["description"] = ""
            item["brand"] = ""
            item["edit_mode"] = False
            if selected_cat:
                cat_info = CATALOG[selected_cat]
                item["hsn"] = cat_info["default_hsn"]
                item["gst"] = cat_info["default_gst"]
                item["rate"] = 0.0
            st.rerun()

        # Product Selectbox
        if not item["category"]:
            prod_col.selectbox(
                "Product / Particulars",
                options=[],
                disabled=True,
                placeholder="👈 Select a category first...",
                key=f"prod_disabled_{item_id}",
            )
        else:
            cat_data = CATALOG[item["category"]]
            prod_map = {get_product_display_label(p): p for p in cat_data["items"]}
            prod_options = list(prod_map.keys()) + [CUSTOM_OPTION]

            current_prod_label = item.get("product_key")
            prod_index = prod_options.index(current_prod_label) if current_prod_label in prod_options else None

            selected_prod_label = prod_col.selectbox(
                "Product / Particulars (Type to search)",
                options=prod_options,
                index=prod_index,
                placeholder="Type letters or select from price list...",
                key=f"prod_select_{item_id}_{item['category']}",
            )

            # When product selection changes, update HSN, Rate, and description immediately
            if selected_prod_label != current_prod_label:
                item["product_key"] = selected_prod_label
                if selected_prod_label == CUSTOM_OPTION:
                    item["is_custom"] = True
                    item["description"] = ""
                    item["brand"] = ""
                    item["rate"] = 0.0
                    item["edit_mode"] = True
                elif selected_prod_label in prod_map:
                    matched = prod_map[selected_prod_label]
                    item["is_custom"] = False
                    item["description"] = get_product_invoice_description(matched)
                    item["brand"] = matched.get("brand", "")
                    item["hsn"] = matched.get("hsn", "")
                    item["rate"] = float(matched.get("rate", 0.0))
                    item["edit_mode"] = False
                st.rerun()

        # Custom Description if manual entry
        if item.get("is_custom"):
            item["description"] = st.text_input(
                "Custom Item Description",
                value=item.get("description", ""),
                placeholder="Enter custom product name / particulars...",
                key=f"custom_desc_{item_id}",
            )

        # Row B: HSN, Rate, Quantity, GST, Line Total
        c_hsn, c_rate, c_qty, c_gst, c_total = st.columns([1.1, 1.2, 0.9, 1.0, 1.3])

        # HSN/SAC Field:
        # Automatic display box (no cursor) when catalog product is chosen, or input if custom/blank/editing
        needs_hsn_input = item.get("is_custom") or item.get("edit_mode") or (item.get("product_key") and not item.get("hsn"))
        if needs_hsn_input:
            item["hsn"] = c_hsn.text_input(
                "HSN/SAC",
                value=item.get("hsn", ""),
                placeholder="Enter HSN/SAC",
                key=f"hsn_input_{item_id}_{item.get('category')}",
            )
        else:
            hsn_display = item.get("hsn") or ("— (Blank)" if item.get("product_key") else "—")
            c_hsn.markdown(
                f"""
                <div class="auto-field-label">HSN/SAC (Auto)</div>
                <div class="auto-field-box">
                    <span class="auto-field-val">{html.escape(hsn_display)}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Rate Field:
        # Automatic display box (no cursor, NO +/- signs) when catalog price exists, or input if custom/0.00/editing
        needs_rate_input = item.get("is_custom") or item.get("edit_mode") or (item.get("product_key") and item.get("rate", 0.0) == 0.0)
        if needs_rate_input:
            rate_val = c_rate.number_input(
                "Rate (₹ - Basic)",
                min_value=0.0,
                value=float(item.get("rate", 0.0)),
                step=1.0,
                format="%.2f",
                key=f"rate_input_{item_id}_{item.get('category')}",
                help="Type the basic rate in Rupees.",
            )
            item["rate"] = float(rate_val)
        else:
            if item.get("product_key"):
                rate_display = f"₹ {fmt(item.get('rate', 0.0))}"
                val_class = "auto-field-val-teal"
            else:
                rate_display = "₹ 0.00"
                val_class = "auto-field-val-muted"
            c_rate.markdown(
                f"""
                <div class="auto-field-label">Rate (₹ - Basic)</div>
                <div class="auto-field-box">
                    <span class="{val_class}">{rate_display}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Quantity Input: strictly positive integers >= 1 (typing 0 alone or negative disallowed)
        current_qty = max(1, int(item.get("quantity", 1)))
        item["quantity"] = c_qty.number_input(
            "Quantity",
            min_value=1,
            step=1,
            value=current_qty,
            key=f"qty_{item_id}",
            help="Quantity must be at least 1.",
        )

        # Automated GST Rate: Non-selectable, strictly automated based on category
        if item.get("category") in CATALOG:
            item["gst"] = float(CATALOG[item["category"]]["default_gst"])
        else:
            item["gst"] = 18.0

        gst_display = f"{item['gst']:g}%" if item.get("category") else "—"
        c_gst.markdown(
            f"""
            <div class="auto-field-label">GST (Auto)</div>
            <div class="auto-field-box">
                <span class="auto-field-val">{gst_display}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Line Total Calculation & Display (Ceiling rounded to whole rupees)
        line_subtotal = money(Decimal(str(item["rate"])) * Decimal(str(item["quantity"])))
        line_tax = money(line_subtotal * Decimal(str(item["gst"])) / Decimal("100"))
        line_raw = line_subtotal + line_tax
        line_grand = money(line_raw.to_integral_value(rounding=ROUND_CEILING))
        
        c_total.markdown(
            f"""
            <div style="padding: 2px 0 0 4px;">
                <div style="font-size: 0.75rem; color: #666;">Line Total (₹)</div>
                <div style="font-size: 1.05rem; font-weight: 700; color: #006A67;">₹ {fmt(line_grand)}</div>
                <div style="font-size: 0.7rem; color: #777;">Base: ₹{fmt(line_subtotal)} + GST: ₹{fmt(line_tax)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Small option to toggle custom rate override for catalog items if needed
        if item.get("product_key") and not item.get("is_custom") and item.get("rate", 0.0) > 0:
            override = st.checkbox("✏️ Edit Rate / HSN manually for this item", value=item.get("edit_mode", False), key=f"edit_toggle_{item_id}")
            if override != item.get("edit_mode", False):
                item["edit_mode"] = override
                st.rerun()

# Handle item deletion
if items_to_delete:
    st.session_state["items"] = [it for it in st.session_state["items"] if it["id"] not in items_to_delete]
    st.rerun()

# Button to Add Product Row
if st.button("＋ Add Product Item", use_container_width=False, type="secondary"):
    st.session_state["item_counter"] += 1
    st.session_state["items"].append({
        "id": st.session_state["item_counter"],
        "category": None,
        "product_key": None,
        "description": "",
        "brand": "",
        "hsn": "",
        "rate": 0.0,
        "quantity": 1,
        "gst": 18.0,
        "is_custom": False,
        "edit_mode": False,
    })
    st.rerun()

# ---- STEP 3: LIVE INVOICE PREVIEW & PDF DOWNLOAD ----
st.divider()
st.subheader("3. Live Invoice Preview & PDF Generation")

valid_items = [
    it for it in st.session_state["items"]
    if it.get("description", "").strip()
]

if not customer_name.strip():
    st.info("💡 **Next step:** Enter the **Customer Name** above to generate the live invoice preview and download the PDF.")
elif not valid_items:
    st.info("💡 **Next step:** Select at least one product from the categories above to populate the invoice.")
else:
    preview_data = []
    subtotal = Decimal("0.00")
    tax_by_rate = {}

    for idx, item in enumerate(valid_items, 1):
        line = money(Decimal(str(item["rate"])) * Decimal(str(item["quantity"])))
        r = float(item["gst"])
        tax = money(line * Decimal(str(r)) / Decimal("100"))
        subtotal += line
        tax_by_rate[r] = tax_by_rate.get(r, Decimal("0.00")) + tax
        preview_data.append({
            "Sl. No": idx,
            "Description of Goods": item["description"],
            "HSN/SAC": item["hsn"] or "—",
            "Rate (₹)": f"₹ {fmt(item['rate'])}",
            "Quantity": item["quantity"],
            "Total (₹)": f"₹ {fmt(line)}",
        })

    tax_total = sum(tax_by_rate.values(), Decimal("0.00"))
    raw_grand_total = subtotal + tax_total
    grand_total = money(raw_grand_total.to_integral_value(rounding=ROUND_CEILING))
    round_off = grand_total - raw_grand_total

    # Metrics summary cards
    if len(tax_by_rate) == 1:
        gst_metric_title = f"GST Total ({list(tax_by_rate.keys())[0]:g}%)"
    else:
        rates_str = ", ".join(f"{r:g}%" for r in sorted(tax_by_rate.keys()))
        gst_metric_title = f"GST Total ({rates_str})"

    m1, m2, m3 = st.columns(3)
    m1.metric("Subtotal", f"₹ {fmt(subtotal)}")
    m2.metric(gst_metric_title, f"₹ {fmt(tax_total)}")
    m3.metric(
        "Grand Total",
        f"₹ {fmt(grand_total)}",
        delta=f"+₹ {fmt(round_off)} (Round Off)" if round_off > 0 else None,
        delta_color="off",
    )

    st.dataframe(pd.DataFrame(preview_data), use_container_width=True, hide_index=True)

    # Generate PDF
    pdf_bytes, _, _, _ = make_pdf(customer_name, valid_items)
    pdf_filename = f"Electrogen_PI_{today.year}_{safe_filename(customer_name)}.pdf"

    st.download_button(
        label=f"⬇ Download Proforma Invoice PDF ({pdf_filename})",
        data=pdf_bytes,
        file_name=pdf_filename,
        mime="application/pdf",
        type="primary",
        use_container_width=True,
    )

    st.markdown("#### Embedded PDF Document Preview")
    pdf_viewer(
        input=pdf_bytes,
        width="100%",
        height=850,
        key="proforma_pdf_preview",
    )

with st.expander("ℹ️ Company & Bank Configuration Details"):
    st.write(f"**GSTIN:** {GSTIN}")
    st.write(f"**Bank:** Federal Bank, Branch: {BANK_BRANCH}")
    st.write(f"**Account No:** {ACCOUNT_NO}  |  **IFSC:** {IFSC}")
    st.write(f"**Authorised Signatory:** {SIGNATORY}")
    st.write("All rates in the price list are basic prices excluding GST.")
