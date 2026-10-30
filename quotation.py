"""
Quotation Generator module for Electrogen Sales Workplace.
PDF builder + Streamlit UI aligned with the official Electrogen letterhead.
"""

import io
import re
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
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image,
)

from quote_catalog import (
    QUOTE_CATALOG,
    QUOTE_CATEGORIES,
    QUOTE_CUSTOM_OPTION,
    get_quote_display_label,
    get_quote_invoice_description,
)

# ── Shared assets ─────────────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).resolve().parent
LETTERHEAD_PATH = BASE_DIR / "image1.jpg"
LOGO_PATH       = BASE_DIR / "ElectrogenLogo.png"
SIG_PATH        = BASE_DIR / "authorised_signature.png"
BRAND_TEAL      = colors.HexColor("#006A67")
BORDER_CLR      = colors.HexColor("#222222")
COMPANY_NAME    = "Electrogen Industries"

# ── Decimal helpers ────────────────────────────────────────────────────────────
def _money(value):
    return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def _fmt(value):
    return f"{_money(value):,.2f}"

def _ceil_rupee(value: Decimal) -> Decimal:
    """Ceiling-round to whole rupee (no paisas on grand total)."""
    return _money(value.to_integral_value(rounding=ROUND_CEILING))


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
    subject: str = "",
    salutation: str = "Dear Sir,",
) -> bytes:
    """
    Build and return a Quotation PDF on official Electrogen letterhead.
    items: list of dicts with keys description, quantity, rate, amount
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=22 * mm,
        rightMargin=22 * mm,
        topMargin=38 * mm,    # starts comfortably below the letterhead header line
        bottomMargin=18 * mm,
        title=f"Quotation {quote_ref}",
        author=COMPANY_NAME,
    )

    def _draw_letterhead(canvas, document):
        canvas.saveState()
        if LETTERHEAD_PATH.exists():
            canvas.drawImage(str(LETTERHEAD_PATH), 0, 0, width=210 * mm, height=297 * mm)
        elif LOGO_PATH.exists():
            # Fallback if letterhead image is not available
            canvas.drawImage(str(LOGO_PATH), 22 * mm, (297 - 25) * mm, width=45 * mm, height=14 * mm, preserveAspectRatio=True)
            canvas.setStrokeColor(BRAND_TEAL)
            canvas.setLineWidth(1)
            canvas.line(22 * mm, (297 - 28) * mm, (210 - 22) * mm, (297 - 28) * mm)
        canvas.restoreState()

    base_font = "Times-Roman"
    bold_font = "Times-Bold"

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="QRefL",  fontName=bold_font, fontSize=10.5, leading=14))
    styles.add(ParagraphStyle(name="QRefR",  fontName=bold_font, fontSize=10.5, leading=14, alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name="QTo",    fontName=bold_font, fontSize=10.5, leading=14))
    styles.add(ParagraphStyle(name="QSub",   fontName=base_font, fontSize=10.5, leading=14))
    styles.add(ParagraphStyle(name="QBody",  fontName=base_font, fontSize=10,   leading=14))
    styles.add(ParagraphStyle(name="QTH",    fontName=bold_font, fontSize=9.5,  leading=12))
    styles.add(ParagraphStyle(name="QTHR",   fontName=bold_font, fontSize=9.5,  leading=12, alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name="QTD",    fontName=base_font, fontSize=9.5,  leading=12))
    styles.add(ParagraphStyle(name="QTDR",   fontName=base_font, fontSize=9.5,  leading=12, alignment=TA_RIGHT))

    story = []

    # ── Ref & Date ────────────────────────────────────────────────────────────
    formatted_date = quote_date.strftime("%d.%m.%y")
    ref_tbl = Table([
        [Paragraph(f"Ref: {html.escape(quote_ref)}", styles["QRefL"]),
         Paragraph(f"DATE: {formatted_date}", styles["QRefR"])]
    ], colWidths=[100 * mm, 66 * mm])
    ref_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING",   (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 0),
    ]))
    story.append(ref_tbl)
    story.append(Spacer(1, 4 * mm))

    # ── To block ──────────────────────────────────────────────────────────────
    story.append(Paragraph("<b>To</b>", styles["QTo"]))
    story.append(Paragraph(f"<b>{html.escape(customer_name)}</b>", styles["QTo"]))
    if customer_address.strip():
        for line in customer_address.strip().split("\n"):
            if line.strip():
                story.append(Paragraph(f"<b>{html.escape(line.strip())}</b>", styles["QTo"]))
    story.append(Spacer(1, 4 * mm))

    # ── Sub & Ref (Enquiry) ───────────────────────────────────────────────────
    if not subject.strip():
        categories_present = [it.get("category") for it in items if it.get("category")]
        unique_cats = sorted(set(categories_present))
        if unique_cats:
            subject = f"Quotation for {' & '.join(unique_cats)}"
        else:
            subject = "Quotation"

    story.append(Paragraph(f"<b>Sub:</b> &nbsp; {html.escape(subject)}", styles["QSub"]))
    if enquiry_ref.strip():
        story.append(Paragraph(f"<b>Ref:</b> &nbsp; {html.escape(enquiry_ref.strip())}", styles["QSub"]))
    story.append(Spacer(1, 3 * mm))

    # ── Salutation & Opening ──────────────────────────────────────────────────
    story.append(Paragraph(html.escape(salutation), styles["QBody"]))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        "At the outset, we would like to thank you very much for your valuable enquiry and "
        "continued interest in our products and services.",
        styles["QBody"],
    ))
    story.append(Spacer(1, 1.5 * mm))
    story.append(Paragraph(
        "We ensure that, we would deliver the best quality products as per your technical "
        "specifications and delivery requirements.",
        styles["QBody"],
    ))
    story.append(Spacer(1, 1.5 * mm))
    story.append(Paragraph(
        "Thanking you and assuring you of our best quality products and services at all times.",
        styles["QBody"],
    ))
    story.append(Spacer(1, 4 * mm))

    # ── Items Table ───────────────────────────────────────────────────────────
    col_w = [12 * mm, 76 * mm, 18 * mm, 30 * mm, 30 * mm]  # total = 166 mm
    table_data = [[
        Paragraph("Sl.No", styles["QTH"]),
        Paragraph("Description", styles["QTH"]),
        Paragraph("Qty", styles["QTHR"]),
        Paragraph("Rate (Rs.)", styles["QTHR"]),
        Paragraph("Amount (Rs.)", styles["QTHR"]),
    ]]

    subtotal = Decimal("0.00")
    for idx, item in enumerate(items, 1):
        line = _money(Decimal(str(item["rate"])) * Decimal(str(item["quantity"])))
        subtotal += line
        desc_text = html.escape(item["description"]).replace("\n", "<br/>")
        table_data.append([
            Paragraph(str(idx), styles["QTD"]),
            Paragraph(desc_text, styles["QTD"]),
            Paragraph(str(item["quantity"]), styles["QTDR"]),
            Paragraph(f"{_money(item['rate']):,.2f}", styles["QTDR"]),
            Paragraph(f"{line:,.2f}", styles["QTDR"]),
        ])

    grand_total = _ceil_rupee(subtotal)
    table_data.append([
        "",
        Paragraph("TOTAL", styles["QTH"]),
        "",
        "",
        Paragraph(f"Rs. {grand_total:,.2f}", styles["QTHR"]),
    ])

    tbl = Table(table_data, colWidths=col_w, hAlign="LEFT")
    tbl.setStyle(TableStyle([
        ("LINEABOVE",     (0, 0), (-1, 0),   1,   BRAND_TEAL),
        ("LINEBELOW",     (0, 0), (-1, 0),   1,   BRAND_TEAL),
        ("LINEABOVE",     (0, -1), (-1, -1), 1,   BRAND_TEAL),
        ("LINEBELOW",     (0, -1), (-1, -1), 1.5, BRAND_TEAL),
        ("VALIGN",        (0, 0), (-1, -1),  "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1),  3),
        ("BOTTOMPADDING", (0, 0), (-1, -1),  3),
        ("LEFTPADDING",   (0, 0), (-1, -1),  2),
        ("RIGHTPADDING",  (0, 0), (-1, -1),  2),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 5 * mm))

    # ── Terms & Conditions ────────────────────────────────────────────────────
    story.append(Paragraph("<b>GENERAL TERMS &amp; CONDITIONS</b>", styles["QTo"]))
    story.append(Spacer(1, 2 * mm))

    all_terms = []
    for term in warranty_terms.strip().split("\n"):
        if term.strip():
            all_terms.append(term.strip())
    for term in payment_terms.strip().split("\n"):
        if term.strip():
            all_terms.append(term.strip())

    for idx, term in enumerate(all_terms, 1):
        clean_text = re.sub(r"^\d+[\.\)]\s*", "", term)
        story.append(Paragraph(f"{idx}) &nbsp; {html.escape(clean_text)}", styles["QBody"]))
        story.append(Spacer(1, 1.5 * mm))

    story.append(Spacer(1, 4 * mm))

    # ── Closing & Signatory ───────────────────────────────────────────────────
    story.append(Paragraph("Sincerely,", styles["QBody"]))
    story.append(Paragraph(f"For <b>{html.escape(COMPANY_NAME)}.</b>", styles["QBody"]))

    if SIG_PATH.exists():
        sig = Image(str(SIG_PATH), width=25 * mm, height=14 * mm, kind="proportional")
        sig.hAlign = "LEFT"
        story.append(sig)
    else:
        story.append(Spacer(1, 12 * mm))

    story.append(Paragraph("<b>Authorized Signatory</b>", styles["QTo"]))

    doc.build(story, onFirstPage=_draw_letterhead, onLaterPages=_draw_letterhead)
    return buffer.getvalue()


# ── Streamlit UI ───────────────────────────────────────────────────────────────
def render_quotation_ui(logo_b64: str):
    """Render the complete Quotation Generator UI inside the Streamlit app."""
    from streamlit_pdf_viewer import pdf_viewer
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
    if "qt_subject"          not in st.session_state:
        st.session_state["qt_subject"]          = "Quotation for Home UPS & Tubular battery"
    if "qt_enquiry_ref"      not in st.session_state:
        st.session_state["qt_enquiry_ref"]      = ""
    if "qt_salutation"       not in st.session_state:
        st.session_state["qt_salutation"]       = "Dear Sir,"
    if "qt_warranty"         not in st.session_state:
        st.session_state["qt_warranty"]         = "Guarantee for UPS 1 Year and for battery Three years"
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
    c1, c2, c3 = st.columns([2, 1.2, 1])
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

    c4, c5 = st.columns([2, 2])
    st.session_state["qt_subject"] = c4.text_input(
        "Subject",
        value=st.session_state["qt_subject"],
        placeholder="e.g. Quotation for Home UPS & Tubular battery",
        key="qt_subj_inp",
    )
    st.session_state["qt_enquiry_ref"] = c5.text_input(
        "Enquiry Reference (optional)",
        value=st.session_state["qt_enquiry_ref"],
        placeholder="e.g. Your Enquiry Dated 23.10.26",
        key="qt_enq_ref_inp",
    )

    ca1, ca2 = st.columns([3, 1])
    st.session_state["qt_customer_address"] = ca1.text_area(
        "Customer Address / Location",
        value=st.session_state["qt_customer_address"],
        placeholder="e.g. Ernakulam",
        height=68,
        key="qt_addr_inp",
    )
    st.session_state["qt_salutation"] = ca2.text_input(
        "Salutation",
        value=st.session_state["qt_salutation"],
        key="qt_salut_inp",
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

            line_raw  = _money(Decimal(str(item["rate"])) * Decimal(str(item["quantity"])))
            line_ceil = _ceil_rupee(line_raw)
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
        height=90,
        key="qt_warranty_inp",
        help="One term per line. Each line becomes a numbered point.",
    )
    st.session_state["qt_payment"] = tc2.text_area(
        "Payment Terms",
        value=st.session_state["qt_payment"],
        height=90,
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
    subject          = st.session_state["qt_subject"]
    enquiry_ref      = st.session_state["qt_enquiry_ref"]
    salutation       = st.session_state["qt_salutation"]

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
                "Rate (Rs.)": f"Rs. {_fmt(it['rate'])}",
                "Amount (Rs.)": f"Rs. {_fmt(line)}",
            })
        grand_ceil = _ceil_rupee(grand)

        m1, m2 = st.columns(2)
        m1.metric("Items", len(valid_items))
        m2.metric("Grand Total", f"Rs. {_fmt(grand_ceil)}")
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
            subject=subject,
            salutation=salutation,
        )
        pdf_filename = f"Electrogen_Quote_{quote_date.year}_{safe_fn(customer_name)}.pdf"

        import hashlib
        pdf_hash = hashlib.md5(pdf_bytes).hexdigest()[:8]

        st.download_button(
            label=f"⬇ Download Quotation PDF ({pdf_filename})",
            data=pdf_bytes,
            file_name=pdf_filename,
            mime="application/pdf",
            type="primary",
            use_container_width=True,
            key=f"qt_download_{pdf_hash}",
        )

        st.markdown("#### Embedded Quotation Preview")
        pdf_viewer(
            input=pdf_bytes,
            width="100%",
            height=800,
            key=f"quotation_pdf_preview_{pdf_hash}",
        )
