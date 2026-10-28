# Electrogen Proforma Invoice Generator

A Streamlit prototype that creates a multi-page, printable Proforma Invoice PDF.

## Run locally
1. Install Python 3.10 or newer.
2. Open Terminal in this folder.
3. Create and activate a virtual environment:
   - macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate`
   - Windows: `python -m venv .venv && .venv\\Scripts\\activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Start the app: `streamlit run app.py`

## Features
- Current date prefilled, editable invoice date
- P.I. number defaults to `Electrogen/YY`
- Automatic SI numbers for line items
- Automatic line totals, GST, and grand total
- GST presets: Inverter 5%, Meter 18%, Battery 18%; custom GST for other items
- Optional signature image upload
- PDF download with customer and year in the filename
- PDF pagination and repeated product-table header

## Before production
This prototype does not persist invoices or coordinate invoice numbering between staff. For the live Electrogen Sales Workplace, connect it to the site's backend/database and implement atomic invoice-number allocation, access control, audit logging, and backups. Confirm GST/HSN data with the accounts team.
