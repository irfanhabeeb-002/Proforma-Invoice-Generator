import io
import base64
import re
import html
import datetime
import uuid
import hashlib
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
from supabase_db import (
    DEFAULT_EMPLOYEES,
    is_supabase_configured,
    fetch_active_employees,
    allocate_pi_record,
    record_download_event,
    fetch_pi_history,
    get_suggested_onedrive_path,
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
    page_title="Electrogen — Sales Workplace",
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
def make_pdf(customer, items, pi_no_override=None, invoice_date=None):
    current_pi = pi_no_override or "PI-DRAFT"
    doc_date = invoice_date if invoice_date else today
    if isinstance(doc_date, str):
        try:
            doc_date = datetime.datetime.strptime(doc_date[:10], "%Y-%m-%d").date()
        except Exception:
            doc_date = today
    doc_date_str = doc_date.strftime("%d.%m.%Y")
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=13 * mm,
        bottomMargin=13 * mm,
        title=f"Proforma Invoice {current_pi}",
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
    styles.add(ParagraphStyle(name="BodyBoldE", fontName="ElectrogenSans-Bold", fontSize=9, leading=12))
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
        P(f"<b>Date:</b> {doc_date_str}<br/><b>P.I No:</b> {html.escape(current_pi)}", styles["SmallBoldE"]),
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

    data.append(["", P("Subtotal", styles["CellBoldE"]), "", "", "", P(fmt(subtotal), styles["CellBoldE"])])

    if len(tax_by_rate) == 1:
        rate_pct = list(tax_by_rate.keys())[0]
        data.append(["", P(f"GST Total ({rate_pct:g}%)", styles["CellBoldE"]), "", "", "", P(fmt(tax_total), styles["CellBoldE"])])
        summary_rows_count = 3
    else:
        for rate_pct, tax_amt in sorted(tax_by_rate.items()):
            data.append(["", P(f"GST ({rate_pct:g}%)", styles["CellBoldE"]), "", "", "", P(fmt(tax_amt), styles["CellBoldE"])])
        data.append(["", P("GST Total", styles["CellBoldE"]), "", "", "", P(fmt(tax_total), styles["CellBoldE"])])
        summary_rows_count = 2 + len(tax_by_rate)

    data.append(["", P("Grand Total", styles["CellBoldE"]), "", "", "", P(fmt(grand_total), styles["CellBoldE"])])

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
    has_hoymiles = any(
        "hoymiles" in str(it.get("category", "")).lower()
        or "hoymiles" in str(it.get("brand", "")).lower()
        or "hoymiles" in str(it.get("description", "")).lower()
        for it in items
    )

    story += [table, Spacer(1, 5 * mm)]

    story.append(P("<b>Additional Info.:</b>", styles["BodyBoldE"]))
    story.append(Spacer(1, 1.5 * mm))
    story.append(P("• &nbsp; Kindly forward the transaction receipt or screenshot of the payment via email or WhatsApp.", styles["SmallE"]))

    if has_hoymiles:
        story.append(Spacer(1, 1 * mm))
        story.append(P("• &nbsp; When the inverter and battery are purchased and used together as a complete system, both products are covered by a 10-year warranty.", styles["SmallE"]))
        story.append(Spacer(1, 1 * mm))
        story.append(P("• &nbsp; If either the inverter or battery is used with a different brand of battery or inverter, respectively, the applicable coverage will be limited to a 5-year warranty.", styles["SmallE"]))
        story.append(Spacer(1, 1 * mm))
        story.append(P("• &nbsp; Transportation Charges Extra At Actuals", styles["SmallE"]))

    story.append(Spacer(1, 4 * mm))
    story.append(P("Kindly make the payment to the following bank account.", styles["BodyE"]))
    story.append(Spacer(1, 3 * mm))

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
        Spacer(1, 5 * mm),
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

# ---- QUOTATION MODULE IMPORT (force fresh reload) ----
import importlib
import quotation
importlib.reload(quotation)
from quotation import render_quotation_ui

# ---- PI HISTORY UI ----
def render_pi_history_ui():
    st.subheader("Proforma Invoice Records & History")
    st.caption("Search, filter, and re-download previously finalized proforma invoices without allocating new numbers.")

    if not is_supabase_configured():
        st.warning(
            "⚠️ **Supabase Connection Not Configured.**\n\n"
            "History requires a configured Supabase database. Add `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` to your Streamlit secrets."
        )
        return

    # Filters
    f_col1, f_col2, f_col3, f_col4 = st.columns([2, 1, 1, 1.5])
    with f_col1:
        search_query = st.text_input("🔍 Search", placeholder="PI No, Customer, Filename, Employee...")
    with f_col2:
        year_opt = ["All", 2026, 2025, 2024]
        selected_year_str = st.selectbox("Year", options=year_opt, index=0)
        selected_year = int(selected_year_str) if selected_year_str != "All" else None
    with f_col3:
        month_opt = ["All"] + [f"{m:02d}" for m in range(1, 13)]
        selected_month_str = st.selectbox("Month", options=month_opt, index=0)
        selected_month = int(selected_month_str) if selected_month_str != "All" else None
    with f_col4:
        employees = fetch_active_employees()
        emp_filter = st.selectbox("Created By", options=["All"] + employees, index=0)

    records = fetch_pi_history(
        search_query=search_query,
        year_filter=selected_year,
        month_filter=selected_month,
        employee_filter=emp_filter,
    )

    if not records:
        st.info("No proforma invoice records found matching the specified filters.")
        return

    st.markdown(f"**Found {len(records)} record(s)**")

    # Display table of records
    display_rows = []
    for r in records:
        display_rows.append({
            "PI Number": r.get("pi_number", ""),
            "Customer Name": r.get("customer_name", ""),
            "PI Date": str(r.get("pi_date", "")),
            "Total Amount (₹)": f"₹ {float(r.get('grand_total', 0.0)):,.2f}",
            "Created By": r.get("created_by_employee", ""),
            "Downloaded By": r.get("latest_downloaded_by") or "—",
            "Download Initiated At": str(r.get("download_initiated_at") or "—")[:19],
            "Status": r.get("status", "Finalized"),
            "Filename": r.get("filename", ""),
        })

    st.dataframe(pd.DataFrame(display_rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Re-download Existing Proforma Invoice")
    st.caption("Select an existing invoice to view details, regenerate the exact PDF, and download without allocating a new number.")

    rec_options = {
        f"{r['pi_number']} | {r['customer_name']} | ₹{float(r.get('grand_total', 0)):,.2f} ({r.get('pi_date')})": r
        for r in records
    }
    selected_label = st.selectbox("Select Proforma Invoice to Re-download", options=list(rec_options.keys()))
    if selected_label:
        sel_rec = rec_options[selected_label]
        
        c1, c2 = st.columns([1.5, 1])
        with c1:
            st.markdown(f"**PI Number:** `{sel_rec['pi_number']}`")
            st.markdown(f"**Customer:** {sel_rec['customer_name']}")
            st.markdown(f"**Date:** {sel_rec['pi_date']}")
            st.markdown(f"**Filename:** `{sel_rec['filename']}`")
        with c2:
            st.markdown(f"**Created By:** {sel_rec['created_by_employee']}")
            st.markdown(f"**Status:** {sel_rec.get('status', 'Finalized')}")
            st.markdown(f"**Latest Downloader:** {sel_rec.get('latest_downloaded_by') or 'None'}")
            st.markdown(f"**Downloads Count:** {sel_rec.get('download_count', 0)}")

        # Dropdown to choose downloader for tracking
        re_downloader = st.selectbox(
            "Employee Re-downloading *",
            options=employees,
            index=None,
            placeholder="Select your name...",
            key=f"emp_redl_{sel_rec['pi_number']}",
        )

        # Suggested onedrive path
        pi_d = today
        try:
            pi_d = datetime.datetime.strptime(str(sel_rec['pi_date'])[:10], "%Y-%m-%d").date()
        except Exception:
            pass
        st.info(f"📁 **Suggested OneDrive Destination:** `{get_suggested_onedrive_path(pi_d)}`")

        # Regenerate exact PDF using stored items
        hist_items = sel_rec.get("items", [])
        hist_pdf_bytes, _, _, _ = make_pdf(
            customer=sel_rec["customer_name"],
            items=hist_items,
            pi_no_override=sel_rec["pi_number"],
            invoice_date=pi_d,
        )

        # --- Two-step history re-download flow ---
        ready_key      = f"hist_dl_ready_{sel_rec['pi_number']}"
        err_key        = f"hist_dl_error_{sel_rec['pi_number']}"
        tracked_by_key = f"hist_dl_tracked_by_{sel_rec['pi_number']}"

        # If the employee selection changed since last tracking, reset the ready state
        if re_downloader != st.session_state.get(tracked_by_key):
            st.session_state[ready_key] = False
            st.session_state[err_key]   = None

        if not st.session_state.get(ready_key):
            # Step 1: Prepare (track) the download
            def on_hist_prepare():
                if re_downloader:
                    st.session_state[err_key] = None
                    try:
                        record_download_event(sel_rec["pi_number"], re_downloader)
                        st.session_state[ready_key]      = True
                        st.session_state[tracked_by_key] = re_downloader
                    except RuntimeError as e:
                        st.session_state[err_key] = str(e)

            st.button(
                f"📋 Prepare Re-download ({sel_rec['filename']})",
                on_click=on_hist_prepare,
                disabled=not bool(re_downloader),
                use_container_width=True,
                key=f"hist_prep_btn_{sel_rec['pi_number']}",
                type="primary",
            )
            if not re_downloader:
                st.caption("⚠️ Please select your name under **Employee Re-downloading *** to enable download.")
            if st.session_state.get(err_key):
                st.error(f"❌ Download tracking failed: {st.session_state[err_key]}")
        else:
            # Step 2: Tracking confirmed — show the actual download button.
            # on_click clears ready state so the next download requires a fresh tracking event.
            def on_hist_dl_click():
                st.session_state[ready_key]      = False
                st.session_state[tracked_by_key] = None

            tracked_by = st.session_state.get(tracked_by_key, re_downloader)
            st.success(f"✅ Tracking recorded for **{tracked_by}**. Click below to download.")
            st.download_button(
                label=f"⬇ Re-download Proforma Invoice PDF ({sel_rec['filename']})",
                data=hist_pdf_bytes,
                file_name=sel_rec["filename"],
                mime="application/pdf",
                type="primary",
                use_container_width=True,
                on_click=on_hist_dl_click,
                key=f"hist_dl_btn_{sel_rec['pi_number']}",
            )
            st.caption(f"PI number `{sel_rec['pi_number']}` and filename are preserved for every repeat download.")

        with st.expander("Document Preview"):
            pdf_viewer(
                input=hist_pdf_bytes,
                width="100%",
                height=800,
                key=f"hist_pv_{sel_rec['pi_number']}",
            )


# ---- MODE TOGGLE ----
if "app_mode" not in st.session_state:
    st.session_state["app_mode"] = "Proforma Invoice Generator"

mode_options = ["Proforma Invoice Generator", "Quotation Generator", "PI History"]
cur_mode_index = mode_options.index(st.session_state["app_mode"]) if st.session_state["app_mode"] in mode_options else 0

mode = st.radio(
    "Select Generator",
    options=mode_options,
    index=cur_mode_index,
    horizontal=True,
    key="app_mode_radio",
    label_visibility="collapsed",
)
if mode != st.session_state["app_mode"]:
    st.session_state["app_mode"] = mode
    st.rerun()

# ---- APP HEADER UI ----
logo_b64 = ""
if LOGO_PATH.exists():
    with open(LOGO_PATH, "rb") as f:
        logo_b64 = base64.b64encode(f.read()).decode()

is_quote_mode = st.session_state["app_mode"] == "Quotation Generator"
is_hist_mode = st.session_state["app_mode"] == "PI History"
if is_quote_mode:
    header_title = "Quotation Generator"
    header_sub = "Electrogen Sales Workplace"
    header_ref_label = "Qt Ref"
    header_ref_val = "Electrogen/Mktg"
elif is_hist_mode:
    header_title = "Proforma Invoice History"
    header_sub = f"GSTIN: {GSTIN} &nbsp;|&nbsp; Electrogen Sales Workplace"
    header_ref_label = "Database"
    header_ref_val = "Archive"
else:
    header_title = "Proforma Invoice Generator"
    header_sub = f"GSTIN: {GSTIN} &nbsp;|&nbsp; Electrogen Sales Workplace"
    header_ref_label = "P.I No"
    if st.session_state.get("pi_finalized") and st.session_state.get("pi_allocated_record"):
        header_ref_val = st.session_state["pi_allocated_record"]["pi_number"]
    else:
        header_ref_val = "DRAFT"

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
                    <div style="font-size: 1.25rem; font-weight: 700; letter-spacing: 0.5px;">{header_title}</div>
                    <div style="font-size: 0.82rem; opacity: 0.9;">{header_sub}</div>
                </div>
            </div>
            <div style="color: white; text-align: right; font-size: 0.85rem; opacity: 0.95;">
                <div><b>Date:</b> {today.strftime('%d.%m.%Y')}</div>
                <div><b>{header_ref_label}:</b> {header_ref_val}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.title(f"Electrogen — {header_title}")
    st.caption("Official Electrogen Sales Workplace")

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# QUOTATION GENERATOR
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state["app_mode"] == "Quotation Generator":
    render_quotation_ui(logo_b64)
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# PI HISTORY
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state["app_mode"] == "PI History":
    render_pi_history_ui()
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# PROFORMA INVOICE GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

# ---- SESSION STATE INITIALIZATION ----
if "customer_name" not in st.session_state:
    st.session_state["customer_name"] = ""

if "pi_request_id" not in st.session_state or not st.session_state["pi_request_id"]:
    st.session_state["pi_request_id"] = str(uuid.uuid4())

if "created_by_employee" not in st.session_state:
    st.session_state["created_by_employee"] = None

if "pi_finalized" not in st.session_state:
    st.session_state["pi_finalized"] = False

if "pi_allocated_record" not in st.session_state:
    st.session_state["pi_allocated_record"] = None

if "pi_finalized_pdf" not in st.session_state:
    st.session_state["pi_finalized_pdf"] = None

if "download_initiated" not in st.session_state:
    st.session_state["download_initiated"] = False
    st.session_state["download_track_error"] = None
    st.session_state["last_downloader"] = None

def reset_pi_draft():
    st.session_state["pi_request_id"] = str(uuid.uuid4())
    st.session_state["customer_name"] = ""
    st.session_state["created_by_employee"] = None
    st.session_state["pi_finalized"] = False
    st.session_state["pi_allocated_record"] = None
    st.session_state["pi_finalized_pdf"] = None
    st.session_state["download_initiated"] = False
    st.session_state["download_track_error"] = None
    st.session_state["last_downloader"] = None
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

is_finalized = bool(st.session_state.get("pi_finalized", False))

# ---- STEP 1: CUSTOMER & EMPLOYEE INFO ----
st.subheader("1. Customer & Employee Information")

col_cust, col_emp = st.columns([1.6, 1.0])
with col_cust:
    customer_name = st.text_input(
        "Bill To / Customer Name *",
        value=st.session_state["customer_name"],
        placeholder="Enter customer or company name (e.g. WEGASOLAR RENEWABLES)",
        help="Type the customer or company name.",
        disabled=is_finalized,
    )
    st.session_state["customer_name"] = customer_name

with col_emp:
    active_employees = fetch_active_employees()
    cur_emp = st.session_state.get("created_by_employee")
    emp_idx = active_employees.index(cur_emp) if cur_emp in active_employees else None
    selected_employee = st.selectbox(
        "Employee / Created By *",
        options=active_employees,
        index=emp_idx,
        placeholder="Select your name...",
        help="Select the employee creating this Proforma Invoice.",
        disabled=is_finalized,
    )
    st.session_state["created_by_employee"] = selected_employee

if is_finalized and st.session_state.get("pi_allocated_record"):
    rec = st.session_state["pi_allocated_record"]
    st.success(
        f"🔒 **PI Finalized & Locked:** `{rec.get('pi_number')}` &nbsp;·&nbsp; "
        f"Filename: `{rec.get('filename')}` &nbsp;·&nbsp; "
        f"Created By: **{rec.get('created_by_employee')}**"
    )
else:
    st.caption(
        f"Invoice Date: **{today.strftime('%d.%m.%Y')}** &nbsp;·&nbsp; "
        f"P.I Number: **[Assigned on Finalize & Save via Supabase]** &nbsp;·&nbsp; "
        f"Draft ID: `{st.session_state['pi_request_id'][:8]}...`"
    )

st.divider()

# ---- STEP 2: PRODUCTS & PARTICULARS ----
st.subheader("2. Items & Particulars")
if is_finalized:
    st.info("🔒 **This Proforma Invoice is finalized.** Line items are locked to prevent accidental modification.")
else:
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
        if len(st.session_state["items"]) > 1 and not is_finalized:
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
            disabled=is_finalized,
        )

        # If category changed, reset product and apply category defaults
        if selected_cat != current_cat and not is_finalized:
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
                disabled=is_finalized,
            )

            # When product selection changes, update HSN, Rate, and description immediately
            if selected_prod_label != current_prod_label and not is_finalized:
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

        is_ct = (item.get("category") == "Current transformers (CT)" or "CT" in str(item.get("category", "")).upper())

        # Custom Description if manual entry or if CT product with edit_mode enabled
        if item.get("is_custom") or (is_ct and item.get("edit_mode")):
            item["description"] = st.text_input(
                "Custom Item Description" if item.get("is_custom") else "Product / Description (Editable)",
                value=item.get("description", ""),
                placeholder="Enter custom product name / particulars...",
                key=f"custom_desc_{item_id}",
                disabled=is_finalized,
            )

        # Row B: HSN, Rate, Quantity, GST, Line Total
        c_hsn, c_rate, c_qty, c_gst, c_total = st.columns([1.1, 1.2, 0.9, 1.0, 1.3])

        # HSN/SAC Field:
        needs_hsn_input = item.get("is_custom") or item.get("edit_mode") or (item.get("product_key") and not item.get("hsn"))
        if needs_hsn_input:
            item["hsn"] = c_hsn.text_input(
                "HSN/SAC",
                value=item.get("hsn", ""),
                placeholder="Enter HSN/SAC",
                key=f"hsn_input_{item_id}_{item.get('category')}",
                disabled=is_finalized,
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
                disabled=is_finalized,
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

        # Quantity Input:
        current_qty = max(1, int(item.get("quantity", 1)))
        item["quantity"] = c_qty.number_input(
            "Quantity",
            min_value=1,
            step=1,
            value=current_qty,
            key=f"qty_{item_id}",
            help="Quantity must be at least 1.",
            disabled=is_finalized,
        )

        # Automated GST Rate:
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

        # Edit override checkbox
        if item.get("product_key") and not item.get("is_custom") and not is_finalized:
            checkbox_label = "✏️ Edit Product Description / Rate / HSN manually for this item" if is_ct else "✏️ Edit Rate / HSN manually for this item"
            override = st.checkbox(checkbox_label, value=item.get("edit_mode", False), key=f"edit_toggle_{item_id}")
            if override != item.get("edit_mode", False):
                item["edit_mode"] = override
                st.rerun()

# Handle item deletion
if items_to_delete and not is_finalized:
    st.session_state["items"] = [it for it in st.session_state["items"] if it["id"] not in items_to_delete]
    st.rerun()

# Button to Add Product Row
if not is_finalized:
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

# ---- STEP 3: LIVE PREVIEW & FINALIZATION ----
st.divider()
st.subheader("3. Live Invoice Preview & PDF Generation")

valid_items = [
    it for it in st.session_state["items"]
    if it.get("description", "").strip()
]

if not customer_name.strip():
    st.info("💡 **Next step:** Enter the **Bill To / Customer Name** above to generate the live invoice preview.")
elif not selected_employee:
    st.info("💡 **Next step:** Select your name under **Employee / Created By *** above to proceed.")
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

    # Metrics summary cards
    if len(tax_by_rate) == 1:
        gst_metric_title = f"GST Total ({list(tax_by_rate.keys())[0]:g}%)"
    else:
        rates_str = ", ".join(f"{r:g}%" for r in sorted(tax_by_rate.keys()))
        gst_metric_title = f"GST Total ({rates_str})"

    m1, m2, m3 = st.columns(3)
    m1.metric("Subtotal", f"₹ {fmt(subtotal)}")
    m2.metric(gst_metric_title, f"₹ {fmt(tax_total)}")
    m3.metric("Grand Total", f"₹ {fmt(grand_total)}")

    st.dataframe(pd.DataFrame(preview_data), use_container_width=True, hide_index=True)

    if not is_finalized:
        # DRAFT STATE: Show draft PDF preview and Finalize button
        draft_pi_label = f"PI-{today.year}-DRAFT"
        draft_pdf_bytes, _, _, _ = make_pdf(customer_name, valid_items, pi_no_override=draft_pi_label)
        draft_hash = hashlib.md5(draft_pdf_bytes).hexdigest()[:8]

        st.markdown("---")
        st.subheader("Finalize & Allocate Official PI Number")
        st.caption(
            "Review the items and customer details above. When ready, click **Finalize & Save** below. "
            "Supabase will atomically allocate the official sequential PI number (e.g. `PI-2026-001`), "
            "stamp it onto the PDF, record the creation audit trail, and enable PDF download."
        )

        col_save, col_info = st.columns([1, 1.2])
        with col_save:
            finalize_clicked = st.button(
                "🔒 Finalize & Save Proforma Invoice",
                type="primary",
                use_container_width=True,
                key="btn_finalize_save",
            )

        with col_info:
            onedrive_dest = get_suggested_onedrive_path(today)
            st.caption(f"📁 Destination: `{onedrive_dest}`")

        if finalize_clicked:
            if not customer_name.strip():
                st.error("❌ Please enter the Bill To / Customer Name.")
            elif not selected_employee or not str(selected_employee).strip():
                st.error("❌ Please select your name under **Employee / Created By *** before finalizing.")
            elif not is_supabase_configured():
                st.error(
                    "❌ **Supabase Connection Not Configured.**\n\n"
                    "Supabase must be the single source of truth for PI numbering. "
                    "Please configure `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in Streamlit secrets "
                    "(`.streamlit/secrets.toml` or Streamlit Cloud Settings)."
                )
            else:
                with st.spinner("Connecting to Supabase and allocating sequential PI number..."):
                    try:
                        record = allocate_pi_record(
                            request_id=st.session_state["pi_request_id"],
                            customer_name=customer_name,
                            created_by_employee=st.session_state["created_by_employee"],
                            pi_date=today,
                            subtotal=float(subtotal),
                            tax_total=float(tax_total),
                            grand_total=float(grand_total),
                            items=valid_items,
                        )
                        allocated_pi_no = record["pi_number"]
                        # Generate final PDF with the allocated official PI number
                        final_pdf, _, _, _ = make_pdf(customer_name, valid_items, pi_no_override=allocated_pi_no)
                        st.session_state["pi_finalized"] = True
                        st.session_state["pi_allocated_record"] = record
                        st.session_state["pi_finalized_pdf"] = final_pdf
                        st.session_state["download_initiated"] = False
                        st.session_state["download_track_error"] = None
                        st.session_state["last_downloader"] = None
                        st.rerun()
                    except Exception as exc:
                        st.error(f"❌ Failed to finalize Proforma Invoice: {str(exc)}")

        st.markdown("#### Draft Document Preview (Unofficial)")
        st.caption("P.I Number is marked as DRAFT until finalized and saved.")
        pdf_viewer(
            input=draft_pdf_bytes,
            width="100%",
            height=850,
            key=f"proforma_draft_preview_{draft_hash}",
        )

    else:
        # FINALIZED STATE: Official PI allocated and locked
        record = st.session_state["pi_allocated_record"]
        pi_number = record.get("pi_number", "PI-FINAL")
        pdf_filename = record.get("filename", f"{pi_number}_{safe_filename(customer_name)}.pdf")
        onedrive_folder = get_suggested_onedrive_path(today)

        st.success(
            f"### ✅ Proforma Invoice Finalized: `{pi_number}`\n\n"
            f"**Allocated PI Number:** `{pi_number}` &nbsp;|&nbsp; "
            f"**Created By:** `{record.get('created_by_employee')}` &nbsp;|&nbsp; "
            f"**Grand Total:** ₹{float(record.get('grand_total', grand_total)):,.2f}"
        )

        st.info(
            f"📁 **Suggested OneDrive Destination Folder:**\n\n"
            f"`{onedrive_folder}`\n\n"
            f"*Please manually move or save your downloaded PDF to this folder in your company OneDrive.*"
        )

        st.write(f"**Generated Filename:** `{pdf_filename}`")

        # Select downloader employee explicitly (do not assume creator is downloader)
        col_dl_emp, col_dl_stat = st.columns([1.5, 1])
        with col_dl_emp:
            main_downloader = st.selectbox(
                "Employee Downloading *",
                options=active_employees,
                index=None,
                placeholder="Select your name to download...",
                key=f"main_dl_emp_{pi_number}",
                help="Select your name before downloading. This is recorded in the download audit trail.",
            )

        # If the employee selection changed since last tracking, reset the ready state
        if main_downloader != st.session_state.get("last_downloader"):
            st.session_state["download_initiated"] = False
            st.session_state["download_track_error"] = None

        with col_dl_stat:
            if st.session_state.get("download_initiated", False):
                st.markdown(
                    f"""
                    <div style="padding-top: 28px;">
                        <span style="color: #006A67; font-weight: 600;">🟢 Download initiated</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"""
                    <div style="padding-top: 28px;">
                        <span style="color: #555;">Status: <b>{record.get('status', 'Finalized')}</b></span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # --- Two-step main PI download flow ---
        if not st.session_state.get("download_initiated", False):
            # Step 1: Prepare (track) the download
            def on_final_pi_prepare():
                if main_downloader:
                    st.session_state["download_track_error"] = None
                    try:
                        record_download_event(pi_number, main_downloader)
                        st.session_state["download_initiated"] = True
                        st.session_state["last_downloader"] = main_downloader
                    except RuntimeError as e:
                        st.session_state["download_track_error"] = str(e)

            st.button(
                f"📋 Prepare Download ({pdf_filename})",
                on_click=on_final_pi_prepare,
                disabled=not bool(main_downloader),
                use_container_width=True,
                key=f"prepare_pdf_{pi_number}",
                type="primary",
            )
            if not main_downloader:
                st.caption("⚠️ Please select your name under **Employee Downloading *** to enable download.")
            if st.session_state.get("download_track_error"):
                st.error(f"❌ Download tracking failed: {st.session_state['download_track_error']}")
        else:
            # Step 2: Tracking confirmed — show the actual download button.
            # on_click clears ready state so the next download requires a fresh tracking event.
            def on_final_dl_click():
                st.session_state["download_initiated"] = False
                st.session_state["last_downloader"]    = None

            tracked_by = st.session_state.get("last_downloader", main_downloader)
            st.success(f"✅ Tracking recorded for **{tracked_by}**. Click below to download.")
            st.download_button(
                label=f"⬇ Download Proforma Invoice PDF ({pdf_filename})",
                data=st.session_state["pi_finalized_pdf"],
                file_name=pdf_filename,
                mime="application/pdf",
                type="primary",
                use_container_width=True,
                on_click=on_final_dl_click,
                key=f"download_pdf_{pi_number}",
            )
            st.caption(f"PI number `{pi_number}` and filename are preserved for every repeat download.")


        st.markdown("")
        col_new, _ = st.columns([1, 2])
        with col_new:
            st.button("➕ Create New Proforma Invoice", on_click=reset_pi_draft, type="secondary")

        st.markdown("#### Embedded Final PDF Preview")
        pdf_viewer(
            input=st.session_state["pi_finalized_pdf"],
            width="100%",
            height=850,
            key=f"proforma_final_preview_{pi_number}",
        )

with st.expander("ℹ️ Company & Bank Configuration Details"):
    st.write(f"**GSTIN:** {GSTIN}")
    st.write(f"**Bank:** Federal Bank, Branch: {BANK_BRANCH}")
    st.write(f"**Account No:** {ACCOUNT_NO}  |  **IFSC:** {IFSC}")
    st.write(f"**Authorised Signatory:** {SIGNATORY}")
    st.write("All rates in the price list are basic prices excluding GST.")
