"""
Supabase Database Integration for Electrogen Proforma Invoice Generator.
Handles:
- Server-side connection via SUPABASE_URL & SUPABASE_SERVICE_ROLE_KEY
- Active employee retrieval (with resilient fallback)
- Atomic PI number allocation via allocate_pi() with idempotency key
- Download event tracking via record_pi_download()
- Historical PI records retrieval and filtering
"""

import os
import re
import json
import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple

import streamlit as st

# Default employee list as specified in requirements (used as seed and fallback)
DEFAULT_EMPLOYEES = [
    "Ashly Celine",
    "Greeshma K M",
    "Meenu M A",
    "Remya Suresh",
    "Rincy Anoop",
    "Sesna Saleem",
    "Simi Chandran",
    "Sreelakshmi D B",
    "Viji P J",
]

_supabase_client = None

def get_supabase_credentials() -> Tuple[Optional[str], Optional[str]]:
    """Retrieve Supabase URL and Service Role Key from st.secrets or os.environ."""
    url = None
    key = None
    
    # 1. Try Streamlit secrets
    try:
        if "SUPABASE_URL" in st.secrets:
            url = str(st.secrets["SUPABASE_URL"]).strip()
        if "SUPABASE_SERVICE_ROLE_KEY" in st.secrets:
            key = str(st.secrets["SUPABASE_SERVICE_ROLE_KEY"]).strip()
    except Exception:
        pass
    
    # 2. Try os.environ fallback
    if not url:
        url = os.environ.get("SUPABASE_URL", "").strip() or None
    if not key:
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip() or None
        
    return url, key

def is_supabase_configured() -> bool:
    """Check if valid Supabase credentials are present."""
    url, key = get_supabase_credentials()
    return bool(url and key)

def get_supabase():
    """Get or create singleton Supabase client."""
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client
        
    url, key = get_supabase_credentials()
    if not url or not key:
        return None
        
    try:
        from supabase import create_client, ClientOptions
        _supabase_client = create_client(url, key)
        return _supabase_client
    except Exception as e:
        # Client creation failed (e.g. invalid url/key format)
        return None

def fetch_active_employees() -> List[str]:
    """
    Fetch active employees from Supabase pi_employees table.
    Supports both standardized ('name', 'is_active') and legacy ('employee_name', 'active') columns.
    Falls back gracefully to DEFAULT_EMPLOYEES if database is unreachable.
    """
    client = get_supabase()
    if client:
        try:
            res = client.table("pi_employees").select("*").execute()
            if res.data and len(res.data) > 0:
                names = []
                for row in res.data:
                    # Check active flag (handles both is_active and active)
                    is_act = row.get("is_active") if "is_active" in row else row.get("active", True)
                    if is_act:
                        n = row.get("name") or row.get("employee_name")
                        if n and str(n).strip():
                            names.append(str(n).strip())
                if names:
                    return sorted(list(set(names)))
        except Exception:
            pass
            
    return sorted(DEFAULT_EMPLOYEES)

def format_clean_customer_name(name: str) -> str:
    """Format customer name for filename: uppercase, alphanumeric & underscores only."""
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", (name or "").strip().upper())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "CUSTOMER"

def allocate_pi_record(
    request_id: str,
    customer_name: str,
    created_by_employee: str,
    pi_date: date,
    subtotal: float,
    tax_total: float,
    grand_total: float,
    items: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Call Supabase allocate_pi() function to atomically allocate the next PI number.
    Uses request_id (UUID) as the idempotency key so double-clicks, retries,
    or reruns return the exact same PI record.
    """
    client = get_supabase()
    if not client:
        raise RuntimeError(
            "Supabase connection is not configured. Please add SUPABASE_URL and "
            "SUPABASE_SERVICE_ROLE_KEY to your Streamlit secrets."
        )

    # Convert items to JSON-serializable list
    serializable_items = []
    for it in items:
        serializable_items.append({
            "id": it.get("id"),
            "category": it.get("category"),
            "product_key": it.get("product_key"),
            "description": str(it.get("description", "")),
            "brand": str(it.get("brand", "")),
            "hsn": str(it.get("hsn", "")),
            "rate": float(it.get("rate", 0.0)),
            "quantity": int(it.get("quantity", 1)),
            "gst": float(it.get("gst", 18.0)),
        })

    year = pi_date.year
    payload = {
        "p_request_id": str(request_id),
        "p_customer_name": customer_name.strip(),
        "p_created_by_employee": created_by_employee.strip(),
        "p_pi_date": pi_date.isoformat(),
        "p_subtotal": float(subtotal),
        "p_tax_total": float(tax_total),
        "p_grand_total": float(grand_total),
        "p_items": serializable_items,
        "p_year": int(year),
    }

    try:
        # Call PostgreSQL allocate_pi() function
        res = client.rpc("allocate_pi", payload).execute()
        data = res.data

        # Normalize return value
        record = None
        if isinstance(data, list) and len(data) > 0:
            record = data[0]
        elif isinstance(data, dict):
            record = data
        elif isinstance(data, str):
            try:
                record = json.loads(data)
            except Exception:
                pass

        if not record or not isinstance(record, dict) or "pi_number" not in record:
            # Fallback query directly in pi_records if function returned scalar
            query = client.table("pi_records").select("*").eq("request_id", str(request_id)).limit(1).execute()
            if query.data and len(query.data) > 0:
                record = query.data[0]

        if not record or "pi_number" not in record:
            raise RuntimeError(f"Unexpected response from allocate_pi(): {data}")

        return record

    except Exception as e:
        raise RuntimeError(f"Failed to allocate PI number in Supabase: {str(e)}") from e

def record_download_event(pi_number: str, downloaded_by_employee: str) -> Dict[str, Any]:
    """
    Record a download event in Supabase exclusively via the record_pi_download() RPC.
    Single source of truth: never falls back to direct table inserts or updates.
    Returns the updated PI record on success.
    Raises RuntimeError on failure.
    """
    client = get_supabase()
    if not client:
        raise RuntimeError(
            "Supabase connection is not configured. Please check SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY."
        )

    if not pi_number or not str(pi_number).strip():
        raise ValueError("Cannot record download: PI number is required.")

    if not downloaded_by_employee or not str(downloaded_by_employee).strip():
        raise ValueError("Cannot record download: Employee name is required.")

    payload = {
        "p_pi_number": str(pi_number).strip(),
        "p_downloaded_by_employee": str(downloaded_by_employee).strip(),
    }

    try:
        res = client.rpc("record_pi_download", payload).execute()
        data = res.data
        if not data:
            raise RuntimeError("Database function record_pi_download returned empty response.")

        record = None
        if isinstance(data, list) and len(data) > 0:
            record = data[0]
        elif isinstance(data, dict):
            record = data
        elif isinstance(data, str):
            try:
                record = json.loads(data)
            except Exception:
                pass

        if not record or not isinstance(record, dict):
            record = {"status": "Download initiated", "pi_number": str(pi_number)}

        return record
    except Exception as e:
        raise RuntimeError(f"Database download tracking failed: {str(e)}") from e

def fetch_pi_history(
    search_query: str = "",
    year_filter: Optional[int] = None,
    month_filter: Optional[int] = None,
    employee_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve PI records history from Supabase with optional filters.
    """
    client = get_supabase()
    if not client:
        return []

    try:
        query = client.table("pi_records").select("*").order("created_at", desc=True)

        if year_filter:
            query = query.eq("year", int(year_filter))
        if employee_filter and employee_filter != "All":
            query = query.eq("created_by_employee", employee_filter)

        res = query.execute()
        records = res.data or []

        # Local filtering for search and month
        filtered = []
        q = search_query.strip().lower()
        for rec in records:
            # Month filter
            pi_date_str = str(rec.get("pi_date", ""))
            if month_filter:
                try:
                    p_date = datetime.strptime(pi_date_str[:10], "%Y-%m-%d").date()
                    if p_date.month != int(month_filter):
                        continue
                except Exception:
                    pass

            # Search query filter (customer name or pi number)
            if q:
                cust = str(rec.get("customer_name", "")).lower()
                pi_num = str(rec.get("pi_number", "")).lower()
                emp = str(rec.get("created_by_employee", "")).lower()
                fn = str(rec.get("filename", "")).lower()
                if q not in cust and q not in pi_num and q not in emp and q not in fn:
                    continue

            filtered.append(rec)

        return filtered
    except Exception:
        return []

def get_suggested_onedrive_path(pi_date: date) -> str:
    """Return the suggested manual OneDrive folder path with full uppercase month name."""
    year_str = str(pi_date.year)
    month_name = pi_date.strftime("%B").upper()
    return f"Electrogen — Shared Documents/Finance/Proforma Invoices/{year_str}/{month_name}/"
