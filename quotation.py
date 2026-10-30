"""
Quotation Generator module for Electrogen Sales Workplace.
PDF builder + Streamlit UI — completely independent of make_pdf() in app.py.
"""

import io
import html
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, ROUND_CEILING
from pathlib import Path

import streamlit as st
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable,
)

from quote_catalog import (
    QUOTE_CATALOG,
    QUOTE_CATEGORIES,
    QUOTE_CUSTOM_OPTION,
    get_quote_display_label,
    get_quote_invoice_description,
)

# ── Shared assets ─────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent
LOGO_PATH   = BASE_DIR / "ElectrogenLogo.png"
FONT_PATH   = BASE_DIR / "DejaVuSans.ttf"
SIG_PATH    = BASE_DIR / "authorised_signature.png"
BRAND_TEAL  = colors.HexColor("#006A67")
BORDER_CLR  = colors.HexColor("#222222")
LIGHT_BG    = colors.HexColor("#F0F5F5")
COMPANY_NAME = "Electrogen Industries"
SIGNATORY    = "Viji Thomas"

# Register fonts here so quotation.py works even when imported before app.py
# registers them (avoids duplicate-registration errors via a try/except).
try:
    pdfmetrics.registerFont(TTFont("ElectrogenSans",      str(FONT_PATH)))
    pdfmetrics.registerFont(TTFont("ElectrogenSans-Bold", str(FONT_PATH)))
except Exception:
    pass  # already registered by app.py — that's fine

# ── Decimal helpers ────────────────────────────────────────────────────────────
def _money(value):
    return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def _fmt(value):
    return f"{_money(value):,.2f}"

def _ceil_rupee(value: Decimal) -> Decimal:
    """Ceiling-round to the next whole rupee (no paisas on grand total)."""
    return _money(value.to_integral_value(rounding=ROUND_CEILING))

def _P(text, style):
    return Paragraph(text, style)

# ── PDF builder ────────────────────────────────────────────────────────────────
def make_quotation_pdf(
    customer_name: str,
    customer_address: str,
    quote_ref: str,
    quote_date: date,
    enquiry_ref: str,
    items: list,
    warranty_terms: str,
    payment_terms: str,
) -> bytes:
    """
    Build and return a Quotation PDF as bytes.
    items: list of dicts with keys description, quantity, rate, amount
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=f"Quotation {quote_ref}",
        author=COMPANY_NAME,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="QuoteTitleR",  fontName="ElectrogenSans-Bold", fontSize=14, leading=17,
                              textColor=colors.white, alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name="QuoteSubR",    fontName="ElectrogenSans-Bold", fontSize=8.5, leading=11,
                              textColor=colors.white, alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name="QuoteTitleC",  fontName="ElectrogenSans-Bold", fontSize=14, leading=17,
                              textColor=colors.white, alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="QuoteSubC",    fontName="ElectrogenSans-Bold", fontSize=8.5, leading=11,
                              textColor=colors.white, alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="SectionW",     fontName="ElectrogenSans-Bold", fontSize=9.5, leading=12,
                              textColor=colors.white, leftIndent=5))
    styles.add(ParagraphStyle(name="BodyE",        fontName="ElectrogenSans",      fontSize=9,  leading=13))
    styles.add(ParagraphStyle(name="BodyBoldE",    fontName="ElectrogenSans-Bold", fontSize=9,  leading=13))
    styles.add(ParagraphStyle(name="SmallE",       fontName="ElectrogenSans",      fontSize=8,  leading=10))
    styles.add(ParagraphStyle(name="SmallBoldE",   fontName="ElectrogenSans-Bold", fontSize=8,  leading=10))
    styles.add(ParagraphStyle(name="CellE",        fontName="ElectrogenSans",      fontSize=8,  leading=10))
    styles.add(ParagraphStyle(name="CellBoldE",    fontName="ElectrogenSans-Bold", fontSize=8,  leading=10))
    styles.add(ParagraphStyle(name="CellWhiteE",   fontName="ElectrogenSans-Bold", fontSize=8,  leading=10,
                              textColor=colors.white, alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="CellRightE",   fontName="ElectrogenSans",      fontSize=8,  leading=10,
                              alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name="CellBoldRight",fontName="ElectrogenSans-Bold", fontSize=8,  leading=10,
                              alignment=TA_RIGHT))

    story = []

    # ── Header banner ─────────────────────────────────────────────────────────
    if LOGO_PATH.exists():
        logo = Image(str(LOGO_PATH), width=48 * mm, height=14.6 * mm, kind="proportional")
        logo.hAlign = "LEFT"
        header = Table(
            [[logo, [_P("QUOTATION", styles["QuoteTitleR"]),
                     _P(html.escape(COMPANY_NAME), styles["QuoteSubR"])]]],
            colWidths=[55 * mm, 123 * mm],
            rowHeights=[17 * mm],
        )
    else:
        header = Table(
            [[_P("QUOTATION", styles["QuoteTitleC"])],
             [_P(html.escape(COMPANY_NAME), styles["QuoteSubC"])]],
            colWidths=[178 * mm],
            rowHeights=[10 * mm, 7 * mm],
        )
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_TEAL),
        ("BOX",        (0, 0), (-1, -1), 1, BORDER_CLR),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",(0, 0), (-1, -1), 6),
        ("TOPPADDING",  (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING",(0,0),(-1, -1), 2),
    ]))
    story += [header, Spacer(1, 7 * mm)]

    # ── Ref / Date / Enquiry block ────────────────────────────────────────────
    meta_left = [
        _P(f"<b>Ref:</b> {html.escape(quote_ref)}", styles["SmallE"]),
        _P(f"<b>Enquiry Ref:</b> {html.escape(enquiry_ref) if enquiry_ref else '—'}", styles["SmallE"]),
    ]
    meta_right = _P(
        f"<b>Date:</b> {quote_date.strftime('%d.%m.%Y')}",
        styles["SmallBoldE"],
    )
    meta = Table([[meta_left, "", meta_right]], colWidths=[80 * mm, 60 * mm, 38 * mm])
    meta.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN",  (2, 0), (2, 0),   "RIGHT"),
    ]))
    story += [meta, Spacer(1, 4 * mm)]

    # ── To block ──────────────────────────────────────────────────────────────
    to_label = Table([[_P("TO", styles["SectionW"])]], colWidths=[20 * mm], rowHeights=[7 * mm])
    to_label.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_TEAL),
        ("BOX",        (0, 0), (-1, -1), 0.8, BORDER_CLR),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",(0, 0), (-1, -1), 6),
    ]))
    story += [to_label, Spacer(1, 2 * mm)]
    story.append(_P(f"<b>{html.escape(customer_name)}</b>", styles["BodyBoldE"]))
    if customer_address.strip():
        for line in customer_address.strip().split("\n"):
            story.append(_P(html.escape(line.strip()), styles["BodyE"]))
    story.append(Spacer(1, 4 * mm))

    # ── Subject / Dear block ──────────────────────────────────────────────────
    # Determine subject from items
    categories_present = set()
    for it in items:
        cat = it.get("category", "")
        if cat:
            categories_present.add(cat)
    if categories_present:
        subject_products = " & ".join(sorted(categories_present))
    else:
        subject_products = "Products"

    story.append(_P(f"<b>Sub:</b> Quotation for {html.escape(subject_products)}", styles["BodyE"]))
    story.append(Spacer(1, 2 * mm))
    story.append(_P("Dear Sir / Madam,", styles["BodyE"]))
    story.append(Spacer(1, 3 * mm))
    story.append(_P(
        "At the outset, we would like to thank you very much for your valuable enquiry and "
        "continued interest in our products and services.",
        styles["SmallE"],
    ))
    story.append(_P(
        "We ensure that we would deliver the best quality products as per your technical "
        "specifications and delivery requirements.",
        styles["SmallE"],
    ))
    story.append(Spacer(1, 5 * mm))

    # ── Items table ───────────────────────────────────────────────────────────
    col_w = [10 * mm, 82 * mm, 22 * mm, 28 * mm, 30 * mm]  # total = 172 mm ≈ A4 usable
    data = [[
        _P("Sl.<br/>No", styles["CellWhiteE"]),
        _P("Description",  styles["CellWhiteE"]),
        _P("Quantity",      styles["CellWhiteE"]),
        _P("Rate (₹)",      styles["CellWhiteE"]),
        _P("Amount (₹)",    styles["CellWhiteE"]),
    ]]

    subtotal = Decimal("0.00")
    for idx, item in enumerate(items, 1):
        line = _money(Decimal(str(item["rate"])) * Decimal(str(item["quantity"])))
        subtotal += line
        data.append([
            _P(str(idx), styles["CellE"]),
            _P(html.escape(item["description"]).replace("\n", "<br/>"), styles["CellE"]),
            _P(str(item["quantity"]), styles["CellE"]),
            _P(_fmt(item["rate"]), styles["CellRightE"]),
            _P(_fmt(line), styles["CellRightE"]),
        ])

    grand_total = _ceil_rupee(subtotal)

    data.append(["", _P("Total", styles["CellBoldE"]), "", "", _P(_fmt(grand_total), styles["CellBoldRight"])])

    tbl = Table(data, colWidths=col_w, repeatRows=1, hAlign="LEFT")
    tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0),  BRAND_TEAL),
        ("GRID",         (0, 0), (-1, -1), 0.7, BORDER_CLR),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",        (0, 0), (0, -1),  "CENTER"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("BACKGROUND",   (0, -1), (-1, -1), LIGHT_BG),
        ("LINEABOVE",    (0, -1), (-1, -1), 1.2, BORDER_CLR),
    ]))
    story += [tbl, Spacer(1, 8 * mm)]

    # ── Terms & Conditions ────────────────────────────────────────────────────
    story.append(_P("<b>General Terms &amp; Conditions</b>", styles["BodyBoldE"]))
    story.append(Spacer(1, 3 * mm))
    for i, term in enumerate(warranty_terms.strip().split("\n"), 1):
        if term.strip():
            story.append(_P(f"{i}. {html.escape(term.strip())}", styles["SmallE"]))
    for j, term in enumerate(payment_terms.strip().split("\n"), i + 1):
        if term.strip():
            story.append(_P(f"{j}. {html.escape(term.strip())}", styles["SmallE"]))
    story.append(Spacer(1, 3 * mm))

    story.append(_P(
        "Thanking you and assuring you of our best quality products and services at all times.",
        styles["SmallE"],
    ))
    story.append(Spacer(1, 8 * mm))

    # ── Signatory ─────────────────────────────────────────────────────────────
    story.append(_P("Sincerely,", styles["BodyE"]))
    story.append(_P(f"For <b>{html.escape(COMPANY_NAME)}</b>.", styles["BodyE"]))
    story.append(Spacer(1, 2 * mm))
    story.append(_P("<b>Authorised Signatory</b>", styles["BodyE"]))
    story.append(Spacer(1, 2 * mm))
    if SIG_PATH.exists():
        sig = Image(str(SIG_PATH), width=25 * mm, height=18 * mm, kind="proportional")
        sig.hAlign = "LEFT"
        story.append(sig)
    else:
        story.append(Spacer(1, 14 * mm))
    story.append(_P(f"<b>{html.escape(SIGNATORY)}</b>", styles["BodyE"]))

    doc.build(story)
    return buffer.getvalue()


# ── Streamlit UI ───────────────────────────────────────────────────────────────
def render_quotation_ui(logo_b64: str):
    """Render the complete Quotation Generator UI inside the Streamlit app."""
    from streamlit_pdf_viewer import pdf_viewer
    import re
    import pandas as pd

    today = date.today()

    def safe_fn(v):
        v = re.sub(r"[^A-Za-z0-9_-]+", "_", v.strip())
        return v.strip("_") or "Customer"

    # ── State init ─────────────────────────────────────────────────────────────
    if "qt_customer_name"    not in st.session_state:
        st.session_state["qt_customer_name"]    = ""
    if "qt_customer_address" not in st.session_state:
        st.session_state["qt_customer_address"] = ""
    if "qt_ref"              not in st.session_state:
        st.session_state["qt_ref"]              = f"Electrogen/Mktg Qt {str(today.year)[-2:]}-{str(today.year + 1)[-2:]}"
    if "qt_date"             not in st.session_state:
        st.session_state["qt_date"]             = today
    if "qt_enquiry_ref"      not in st.session_state:
        st.session_state["qt_enquiry_ref"]      = ""
    if "qt_warranty"         not in st.session_state:
        st.session_state["qt_warranty"]         = (
            "Guarantee for UPS: 1 Year\n"
            "Guarantee for Battery: 3 Years"
        )
    if "qt_payment"          not in st.session_state:
        st.session_state["qt_payment"]          = "100% Advance Payment."
    if "qt_items"            not in st.session_state:
        st.session_state["qt_items"] = [{
            "id": 1, "category": None, "product_key": None,
            "description": "", "quantity": 1, "rate": 0.0, "is_custom": False,
        }]
        st.session_state["qt_item_counter"] = 1

    # ── Step 1: Customer & Quote details ──────────────────────────────────────
    st.subheader("1. Quotation Details")
    c1, c2, c3, c4 = st.columns([2, 1.2, 1, 1.5])
    st.session_state["qt_customer_name"] = c1.text_input(
        "Customer Name",
        value=st.session_state["qt_customer_name"],
        placeholder="e.g. Mr. Sethumadhavan",
        key="qt_cust_name_inp",
    )
    st.session_state["qt_ref"] = c2.text_input(
        "Quotation Reference",
        value=st.session_state["qt_ref"],
        key="qt_ref_inp",
    )
    st.session_state["qt_date"] = c3.date_input(
        "Date",
        value=st.session_state["qt_date"],
        key="qt_date_inp",
    )
    st.session_state["qt_enquiry_ref"] = c4.text_input(
        "Enquiry Reference",
        value=st.session_state["qt_enquiry_ref"],
        placeholder="e.g. Your Enquiry Dated 23.10.26",
        key="qt_enq_ref_inp",
    )
    st.session_state["qt_customer_address"] = st.text_area(
        "Customer Address",
        value=st.session_state["qt_customer_address"],
        placeholder="City / full address (optional)",
        height=68,
        key="qt_addr_inp",
    )

    st.divider()

    # ── Step 2: Items ──────────────────────────────────────────────────────────
    st.subheader("2. Items / Particulars")
    st.caption("Select a category, then pick the product. Enter rate manually where shown.")

    items_to_delete = []

    for idx, item in enumerate(st.session_state["qt_items"]):
        item_id = item["id"]
        with st.container(border=True):
            hdr_col, del_col = st.columns([0.88, 0.12])
            hdr_col.markdown(f"**Item {idx + 1}**")
            if len(st.session_state["qt_items"]) > 1:
                if del_col.button("🗑 Remove", key=f"qt_del_{item_id}", use_container_width=True):
                    items_to_delete.append(item_id)

            cat_col, prod_col = st.columns([1, 2.2])
            current_cat = item.get("category")
            cat_idx = QUOTE_CATEGORIES.index(current_cat) if current_cat in QUOTE_CATEGORIES else None

            selected_cat = cat_col.selectbox(
                "Category",
                options=QUOTE_CATEGORIES,
                index=cat_idx,
                placeholder="Select category...",
                key=f"qt_cat_{item_id}",
            )

            if selected_cat != current_cat:
                item["category"]    = selected_cat
                item["product_key"] = None
                item["description"] = ""
                item["rate"]        = 0.0
                item["is_custom"]   = False
                st.rerun()

            if not item["category"]:
                prod_col.selectbox(
                    "Product", options=[], disabled=True,
                    placeholder="👈 Select a category first...",
                    key=f"qt_prod_dis_{item_id}",
                )
            else:
                cat_data = QUOTE_CATALOG[item["category"]]
                prod_map = {get_quote_display_label(p): p for p in cat_data["items"]}
                prod_options = list(prod_map.keys()) + [QUOTE_CUSTOM_OPTION]

                current_prod = item.get("product_key")
                prod_idx = prod_options.index(current_prod) if current_prod in prod_options else None

                selected_prod = prod_col.selectbox(
                    "Product / Particulars (Type to search)",
                    options=prod_options,
                    index=prod_idx,
                    placeholder="Type or select from list...",
                    key=f"qt_prod_{item_id}_{item['category']}",
                )

                if selected_prod != current_prod:
                    item["product_key"] = selected_prod
                    if selected_prod == QUOTE_CUSTOM_OPTION:
                        item["is_custom"]   = True
                        item["description"] = ""
                        item["rate"]        = 0.0
                    elif selected_prod in prod_map:
                        matched             = prod_map[selected_prod]
                        item["is_custom"]   = False
                        item["description"] = get_quote_invoice_description(matched)
                        item["rate"]        = float(matched.get("rate", 0.0))
                    st.rerun()

            if item.get("is_custom"):
                item["description"] = st.text_input(
                    "Custom Item Description",
                    value=item.get("description", ""),
                    placeholder="Enter custom product name...",
                    key=f"qt_custom_desc_{item_id}",
                )

            r_col, q_col, line_col = st.columns([1.5, 1, 1.5])

            item["rate"] = r_col.number_input(
                "Rate (₹)",
                min_value=0.0,
                value=float(item.get("rate", 0.0)),
                format="%.2f",
                key=f"qt_rate_{item_id}_{item.get('category')}",
                help="Enter the unit rate in Rupees.",
            )

            item["quantity"] = q_col.number_input(
                "Quantity",
                min_value=1,
                step=1,
                value=max(1, int(item.get("quantity", 1))),
                key=f"qt_qty_{item_id}",
            )

            line_raw   = _money(Decimal(str(item["rate"])) * Decimal(str(item["quantity"])))
            line_ceil  = _ceil_rupee(line_raw)
            line_col.markdown(
                f"""
                <div style="padding: 2px 0 0 4px;">
                    <div style="font-size:0.75rem;color:#666;">Line Amount (₹)</div>
                    <div style="font-size:1.05rem;font-weight:700;color:#006A67;">₹ {_fmt(line_ceil)}</div>
                    <div style="font-size:0.7rem;color:#777;">₹ {_fmt(item['rate'])} × {item['quantity']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Process deletions
    if items_to_delete:
        st.session_state["qt_items"] = [
            it for it in st.session_state["qt_items"] if it["id"] not in items_to_delete
        ]
        st.rerun()

    if st.button("＋ Add Item", use_container_width=False, type="secondary", key="qt_add_item"):
        st.session_state["qt_item_counter"] += 1
        st.session_state["qt_items"].append({
            "id": st.session_state["qt_item_counter"],
            "category": None, "product_key": None,
            "description": "", "quantity": 1, "rate": 0.0, "is_custom": False,
        })
        st.rerun()

    st.divider()

    # ── Step 3: Terms ──────────────────────────────────────────────────────────
    st.subheader("3. Terms & Conditions")
    tc1, tc2 = st.columns(2)
    st.session_state["qt_warranty"] = tc1.text_area(
        "Guarantee / Warranty Terms",
        value=st.session_state["qt_warranty"],
        height=100,
        key="qt_warranty_inp",
        help="One term per line. Each line becomes a numbered point.",
    )
    st.session_state["qt_payment"] = tc2.text_area(
        "Payment Terms",
        value=st.session_state["qt_payment"],
        height=100,
        key="qt_payment_inp",
        help="One term per line.",
    )

    st.divider()

    # ── Step 4: Preview & Download ─────────────────────────────────────────────
    st.subheader("4. Live Preview & Download")

    customer_name    = st.session_state["qt_customer_name"]
    customer_address = st.session_state["qt_customer_address"]
    quote_ref        = st.session_state["qt_ref"]
    quote_date       = st.session_state["qt_date"]
    enquiry_ref      = st.session_state["qt_enquiry_ref"]

    valid_items = [
        it for it in st.session_state["qt_items"]
        if it.get("description", "").strip()
    ]

    if not customer_name.strip():
        st.info("💡 Enter the **Customer Name** above to generate the quotation preview.")
    elif not valid_items:
        st.info("💡 Add at least one item with a description above.")
    else:
        preview_rows = []
        grand = Decimal("0.00")
        for idx, it in enumerate(valid_items, 1):
            line = _money(Decimal(str(it["rate"])) * Decimal(str(it["quantity"])))
            grand += line
            preview_rows.append({
                "Sl. No": idx,
                "Description": it["description"],
                "Quantity": it["quantity"],
                "Rate (₹)": f"₹ {_fmt(it['rate'])}",
                "Amount (₹)": f"₹ {_fmt(line)}",
            })
        grand_ceil = _ceil_rupee(grand)

        import pandas as pd
        m1, m2 = st.columns(2)
        m1.metric("Items", len(valid_items))
        m2.metric("Grand Total", f"₹ {_fmt(grand_ceil)}")
        st.dataframe(pd.DataFrame(preview_rows), use_container_width=True, hide_index=True)

        # Build PDF
        pdf_bytes = make_quotation_pdf(
            customer_name=customer_name,
            customer_address=customer_address,
            quote_ref=quote_ref,
            quote_date=quote_date,
            enquiry_ref=enquiry_ref,
            items=[{**it, "amount": _money(Decimal(str(it["rate"])) * Decimal(str(it["quantity"])))} for it in valid_items],
            warranty_terms=st.session_state["qt_warranty"],
            payment_terms=st.session_state["qt_payment"],
        )
        pdf_filename = f"Electrogen_Quote_{quote_date.year}_{safe_fn(customer_name)}.pdf"

        st.download_button(
            label=f"⬇ Download Quotation PDF ({pdf_filename})",
            data=pdf_bytes,
            file_name=pdf_filename,
            mime="application/pdf",
            type="primary",
            use_container_width=True,
            key="qt_download",
        )

        st.markdown("#### Embedded Quotation Preview")
        pdf_viewer(
            input=pdf_bytes,
            width="100%",
            height=800,
            key="quotation_pdf_preview",
        )
