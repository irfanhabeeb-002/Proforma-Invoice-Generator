# Electrogen Proforma Invoice Generator

A Streamlit application that creates multi-page, printable Proforma Invoice PDFs with automatic GST calculations, category-filtered product catalog dropdowns, and live PDF preview.

## Run Locally
1. Install Python 3.10 or newer.
2. Open Terminal in this folder.
3. Create and activate a virtual environment:
   - macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate`
   - Windows: `python -m venv .venv && .venv\Scripts\activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Start the app: `streamlit run app.py`

## Features & User Flow
- **Branded Executive Interface:** Integrated Electrogen logo (`ElectrogenLogo.png`) in both the web workspace header and the official PDF letterhead banner.
- **Clean Initial State:** No default dummy values pre-filled; all fields display informative placeholders.
- **Step 1: Customer Information:** Enter customer / company name to initiate the live invoice.
- **Step 2: Category & Product Selection (Typing Suggestion):**
  - Select Category: 9 built-in categories (Energy meters, CTs, Water meter, Solar inverters, Hybrid inverters, Batteries, Water tanks, Solar panels, Water level controller).
  - Searchable Particulars: Type letters into the product selectbox to instantly filter from the official price list.
  - Automatic HSN/SAC & Rates: HSN/SAC codes and basic rates populate automatically.
  - Custom / Manual Entry Fallback: If an item is not in the list, choose `➕ Custom / Enter Manually`.
- **Strict Quantity Validation:** Quantity cannot be zero or negative; UI restricts typing zero alone or stepping below 1.
- **Real-Time Financial Math:** Live line total, subtotal, GST total, and grand total calculated with precise decimal rounding.
- **Step 3: Live Preview & PDF Download:**
  - Embedded PDF preview powered by `streamlit-pdf-viewer`.
  - Downloadable PDF generated using ReportLab with custom rupee font (`DejaVuSans.ttf`), bank details, and authorised signature (`authorised_signature.png`).
