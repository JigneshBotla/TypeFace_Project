# app/services/pdf_parser.py
import pdfplumber
from typing import List, Dict, Any
import logging
from decimal import Decimal
from datetime import datetime

logger = logging.getLogger(__name__)

def parse_transactions_from_pdf(path: str) -> List[Dict[str,Any]]:
    """
    Try to extract tabular transaction rows from a pdf file.
    Returns list of {date: 'YYYY-MM-DD', description: str, amount: Decimal}
    This is heuristic — depends on the vendor PDF layout.
    """
    results = []
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                try:
                    tables = page.extract_tables()
                except Exception:
                    tables = []
                for table in tables:
                    # table is list of rows (list of cols)
                    # try to guess header row with "date" and "amount" keywords
                    for row in table:
                        # flatten row and remove None
                        row_text = [ (c or "").strip() for c in row ]
                        if not any(row_text):
                            continue
                        joined = " ".join(row_text).lower()
                        # skip obvious header lines
                        if "date" in joined and ("amount" in joined or "price" in joined or "description" in joined):
                            continue
                        # try to find a date-like and number-like token
                        date_token = None
                        amount_token = None
                        desc_parts = []
                        for token in row_text:
                            tok = token or ""
                            # naive date detection
                            if any(ch.isdigit() for ch in tok) and ("/" in tok or "-" in tok or len(tok)>=6):
                                # try parse
                                for fmt in ("%Y-%m-%d","%d/%m/%Y","%m/%d/%Y","%d-%m-%Y","%Y/%m/%d"):
                                    try:
                                        dt = datetime.strptime(tok, fmt)
                                        date_token = dt.date().isoformat()
                                        break
                                    except Exception:
                                        pass
                            # amount detection: contains digits and '.' or ','
                            if any(ch.isdigit() for ch in tok) and ('.' in tok or ',' in tok):
                                # clean
                                amt = tok.replace(",", "").replace("$", "").replace("€","").strip()
                                try:
                                    amount_token = Decimal(amt)
                                except Exception:
                                    pass
                            else:
                                desc_parts.append(tok)
                        # if we found amount and date or amount alone, create record
                        if amount_token is not None:
                            rec = {
                                "date": date_token,
                                "description": " ".join([p for p in desc_parts if p]),
                                "amount": float(amount_token),
                            }
                            results.append(rec)
    except Exception as exc:
        logger.exception("pdf parse failed: %s", exc)
    return results
