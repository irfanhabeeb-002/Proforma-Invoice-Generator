import io
import base64
import re
import html
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image

BASE_DIR = Path(__file__).resolve().parent
TEAL = colors.HexColor("#28686A")
BORDER = colors.HexColor("#222222")
GSTIN = "32AADFE7851L1ZA"
BANK_NAME = "Electrogen Industries"
ACCOUNT_NO = "12950200004713"
BANK_BRANCH = "Lulu Mall"
IFSC = "FDRL0002031"
SIGNATORY = "Viji Thomas"
SIGNATURE_PATH = BASE_DIR / "authorised_signature.png"
FONT_PATH = BASE_DIR / "DejaVuSans.ttf"

# DejaVu Sans contains the Indian rupee glyph, unlike ReportLab's built-in Helvetica.
pdfmetrics.registerFont(TTFont("ElectrogenSans", str(FONT_PATH)))
pdfmetrics.registerFont(TTFont("ElectrogenSans-Bold", str(FONT_PATH)))

st.set_page_config(page_title="Electrogen Proforma Invoice Generator", page_icon="🧾", layout="wide")
st.title("Electrogen — Proforma Invoice Generator")
st.caption("Enter the customer and product details. The invoice preview and totals update automatically.")

today = date.today()
pi_no = f"Electrogen/{str(today.year)[-2:]}"
GST_RATES = {"Inverter": 5.0, "Meter": 18.0, "Battery": 18.0, "Other": 18.0}

if "products" not in st.session_state:
    st.session_state["products"] = [
        {"description": "3PH NET (VISIONTEK)", "category": "Meter", "hsn": "90283010", "rate": 5508.47, "quantity": 10}
    ]
if "customer_name" not in st.session_state:
    st.session_state["customer_name"] = "WEGASOLAR RENEWABLES"

# Keep widget state in sync with the product list before rendering widgets.
def money(value):
    return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def fmt(value):
    return f"{money(value):,.2f}"

def safe_filename(value):
    value = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip())
    return value.strip("_") or "Customer"

def P(text, style):
    return Paragraph(text, style)

def make_pdf(customer, items):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=16*mm, leftMargin=16*mm,
                            topMargin=13*mm, bottomMargin=13*mm,
                            title=f"Proforma Invoice {pi_no}", author="Electrogen Industries")
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="InvTitle", fontName="ElectrogenSans-Bold", fontSize=16, leading=19,
                              textColor=colors.white, alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="InvSub", fontName="ElectrogenSans-Bold", fontSize=9, leading=11,
                              textColor=colors.white, alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="Section", fontName="ElectrogenSans-Bold", fontSize=10, leading=12,
                              textColor=colors.white, leftIndent=5))
    styles.add(ParagraphStyle(name="BodyE", fontName="ElectrogenSans", fontSize=9, leading=12))
    styles.add(ParagraphStyle(name="SmallE", fontName="ElectrogenSans", fontSize=8, leading=10))
    styles.add(ParagraphStyle(name="SmallBoldE", fontName="ElectrogenSans-Bold", fontSize=8, leading=10))
    styles.add(ParagraphStyle(name="CellE", fontName="ElectrogenSans", fontSize=7.5, leading=9))
    styles.add(ParagraphStyle(name="CellBoldE", fontName="ElectrogenSans-Bold", fontSize=7.5, leading=9))
    styles.add(ParagraphStyle(name="CellWhiteE", fontName="ElectrogenSans-Bold", fontSize=7.5, leading=9,
                              textColor=colors.white, alignment=TA_CENTER))
    story=[]
    header=Table([[P("PROFORMA INVOICE", styles["InvTitle"])],
                  [P(f"GSTIN: {html.escape(GSTIN)}", styles["InvSub"])]],
                 colWidths=[178*mm], rowHeights=[10*mm,7*mm])
    header.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),TEAL),("BOX",(0,0),(-1,-1),1,BORDER),
                                ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),4),
                                ("RIGHTPADDING",(0,0),(-1,-1),4)]))
    story += [header, Spacer(1,13*mm)]
    bill=Table([[P("BILL TO",styles["Section"]),"",
                 P(f"<b>Date:</b> {today.strftime('%d.%m.%Y')}<br/><b>P.I No:</b> {html.escape(pi_no)}",styles["SmallBoldE"])]],
               colWidths=[50*mm,63*mm,65*mm])
    bill.setStyle(TableStyle([("BACKGROUND",(0,0),(0,0),TEAL),("BOX",(0,0),(0,0),0.8,BORDER),
                              ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),5),
                              ("RIGHTPADDING",(0,0),(-1,-1),5),("TOPPADDING",(0,0),(-1,-1),5),
                              ("BOTTOMPADDING",(0,0),(-1,-1),5)]))
    story += [bill,Spacer(1,3*mm),P(html.escape(customer),styles["BodyE"]),Spacer(1,5*mm)]
    data=[[P("Sl.<br/>No",styles["CellWhiteE"]),P("Description of Goods",styles["CellWhiteE"]),
           P("HSN/SAC",styles["CellWhiteE"]),P("Rate (₹)",styles["CellWhiteE"]),
           P("Quantity",styles["CellWhiteE"]),P("GST",styles["CellWhiteE"]),P("Total (₹)",styles["CellWhiteE"])]]
    subtotal=Decimal("0.00"); tax_total=Decimal("0.00")
    for idx,item in enumerate(items,1):
        line=money(Decimal(str(item["rate"])) * Decimal(str(item["quantity"])))
        tax=money(line*Decimal(str(item["gst"]))/Decimal("100"))
        subtotal += line; tax_total += tax
        data.append([P(str(idx),styles["CellE"]),P(html.escape(item["description"]).replace("\n","<br/>"),styles["CellE"]),
                     P(html.escape(item["hsn"] or "-"),styles["CellE"]),P(fmt(item["rate"]),styles["CellE"]),
                     P(str(item["quantity"]),styles["CellE"]),P(f"{item['gst']:g}%",styles["CellE"]),P(fmt(line),styles["CellE"])])
    total=money(subtotal+tax_total)
    data += [["",P("Subtotal",styles["CellBoldE"]),"","","","",P(fmt(subtotal),styles["CellBoldE"])],
             ["",P("GST Total",styles["CellBoldE"]),"","","","",P(fmt(tax_total),styles["CellBoldE"])],
             ["",P("Grand Total",styles["CellBoldE"]),"","","","",P(fmt(total),styles["CellBoldE"])]]
    table=Table(data,colWidths=[10*mm,53*mm,21*mm,25*mm,20*mm,15*mm,30*mm],repeatRows=1,hAlign="LEFT")
    table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),TEAL),("GRID",(0,0),(-1,-1),0.7,BORDER),
                               ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("ALIGN",(0,0),(0,-1),"CENTER"),
                               ("ALIGN",(2,1),(-1,-1),"RIGHT"),("LEFTPADDING",(0,0),(-1,-1),4),
                               ("RIGHTPADDING",(0,0),(-1,-1),4),("TOPPADDING",(0,0),(-1,-1),5),
                               ("BOTTOMPADDING",(0,0),(-1,-1),5),("BACKGROUND",(0,-3),(-1,-1),colors.HexColor("#F0F5F5")),
                               ("LINEABOVE",(0,-1),(-1,-1),1.2,BORDER)]))
    story += [table,Spacer(1,10*mm),P("Kindly make the payment to the following bank account.",styles["BodyE"]),Spacer(1,7*mm)]
    bank_data=[[P("Bank Details",styles["CellWhiteE"]),"","",""],
               [P("Federal Bank",styles["CellWhiteE"]),"","",""],
               [P("Name",styles["CellBoldE"]),P(html.escape(BANK_NAME),styles["CellE"]),P("AC No.",styles["CellBoldE"]),P(html.escape(ACCOUNT_NO),styles["CellE"])],
               [P("Branch",styles["CellBoldE"]),P(html.escape(BANK_BRANCH),styles["CellE"]),P("IFSC Code",styles["CellBoldE"]),P(html.escape(IFSC),styles["CellE"])]]
    bank=Table(bank_data,colWidths=[18*mm,70*mm,25*mm,65*mm],repeatRows=2)
    bank.setStyle(TableStyle([("SPAN",(0,0),(-1,0)),("SPAN",(0,1),(-1,1)),("BACKGROUND",(0,0),(-1,1),TEAL),
                              ("GRID",(0,0),(-1,-1),0.8,BORDER),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                              ("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),
                              ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6)]))
    story += [
        bank,
        Spacer(1, 9*mm),
        P("<b>Additional Info.</b>", styles["BodyE"]),
        Spacer(1, 3*mm),
        P(
            "• Kindly forward the transaction receipt or screenshot of the payment via email or WhatsApp.",
            styles["SmallE"]
        ),
        Spacer(1, 8*mm),
    ]

    # Left-align the authorised signatory and signature.
    story.append(P("<b>Authorised Signatory</b>", styles["BodyE"]))
    story.append(Spacer(1, 2*mm))

    if SIGNATURE_PATH.exists():
        signature = Image(
            str(SIGNATURE_PATH),
            width=25*mm,
            height=18*mm,
            kind="proportional"
        )
        signature.hAlign = "LEFT"
        story.append(signature)
    else:
        story.append(Spacer(1, 15*mm))

    story.append(P(f"<b>{html.escape(SIGNATORY)}</b>", styles["BodyE"]))
    doc.build(story)
    return buffer.getvalue(),float(subtotal),float(tax_total),float(total)

st.subheader("Customer")
customer=st.text_input("Bill to / Customer name",key="customer_name",placeholder="Enter customer or company name")
st.caption(f"Invoice date: {today.strftime('%d.%m.%Y')}  ·  P.I No: {pi_no}")
st.subheader("Products")
st.caption("Choose a product category to apply the configured GST rate. SI numbers are assigned automatically.")

for i, product in enumerate(st.session_state["products"]):
    with st.container(border=True):
        st.markdown(f"**Item {i+1}**")
        c1,c2,c3,c4,c5=st.columns([2.8,1.2,1.2,1.1,0.8])
        product["description"]=c1.text_input("Description",value=product["description"],key=f"desc_{i}")
        cat_options=list(GST_RATES.keys())
        cat=product.get("category","Other")
        product["category"]=c2.selectbox("Category",cat_options,index=cat_options.index(cat) if cat in cat_options else 3,key=f"cat_{i}")
        product["hsn"]=c3.text_input("HSN/SAC",value=product["hsn"],key=f"hsn_{i}")
        product["rate"]=c4.number_input("Rate (₹)",min_value=0.0,value=float(product["rate"]),step=0.01,format="%.2f",key=f"rate_{i}")
        product["quantity"]=c5.number_input("Quantity",min_value=1,value=int(product["quantity"]),step=1,key=f"qty_{i}")
        product["gst"]=GST_RATES[product["category"]]
        st.caption(f"GST applied: {product['gst']:g}%")

add_col,remove_col=st.columns(2)
with add_col:
    if st.button("＋ Add product",use_container_width=True):
        st.session_state["products"].append({"description":"","category":"Other","hsn":"","rate":0.0,"quantity":1})
        st.rerun()
with remove_col:
    if len(st.session_state["products"])>1 and st.button("− Remove last product",use_container_width=True):
        st.session_state["products"].pop()
        st.rerun()

current=[]
for p in st.session_state["products"]:
    current.append({"description":p["description"],"category":p["category"],"hsn":p["hsn"],
                    "rate":p["rate"],"quantity":p["quantity"],"gst":GST_RATES[p["category"]]})

st.divider()
st.subheader("Live invoice preview")
if not customer.strip():
    st.warning("Enter the customer name to preview and download the invoice.")
else:
    preview=[]; subtotal=0.0; tax_total=0.0
    for i,item in enumerate(current,1):
        line=float(money(item["rate"]*item["quantity"]))
        tax=float(money(line*item["gst"]/100))
        subtotal+=line; tax_total+=tax
        preview.append({"Sl. No":i,"Description":item["description"],"HSN/SAC":item["hsn"],
                        "Rate (₹)":f"₹ {fmt(item['rate'])}","Quantity":item["quantity"],
                        "GST":f"{item['gst']:g}%","Line total":f"₹ {fmt(line)}"})
    st.dataframe(pd.DataFrame(preview),use_container_width=True,hide_index=True)
    m1,m2,m3=st.columns(3)
    m1.metric("Subtotal",f"₹ {fmt(subtotal)}")
    m2.metric("GST total",f"₹ {fmt(tax_total)}")
    m3.metric("Grand total",f"₹ {fmt(subtotal+tax_total)}")
    pdf_bytes,_,_,_=make_pdf(customer,current)
    filename=f"Electrogen_PI_{today.year}_{safe_filename(customer)}.pdf"
    st.download_button("⬇ Download PDF",data=pdf_bytes,file_name=filename,mime="application/pdf",type="primary",use_container_width=True)
    st.markdown("**PDF preview**")

    from streamlit_pdf_viewer import pdf_viewer

    pdf_viewer(
        input=pdf_bytes,
        width="100%",
        height=900,
        key="proforma_pdf_preview",
    )


with st.expander("Internal configuration note"):
    st.write("Fixed in the template: GSTIN, bank details, signatory, signature, date and year-based P.I. number. Confirm GST rates and HSN/SAC codes with accounts before production use.")
