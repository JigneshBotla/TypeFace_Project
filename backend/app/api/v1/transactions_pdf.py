# app/api/v1/transactions_pdf.py
import os
import time
import uuid
from decimal import Decimal
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.api.v1.deps import get_current_user, get_db_dep
from app.db import models
from app.services.pdf_parser import parse_transactions_from_pdf

router = APIRouter(tags=["transactions_pdf"])

# reuse uploads root (same as receipts)
UPLOAD_ROOT = os.path.abspath(os.path.join(os.getcwd(), "uploads"))
os.makedirs(UPLOAD_ROOT, exist_ok=True)

def ensure_user_upload_dir(user_id: int) -> str:
    d = os.path.join(UPLOAD_ROOT, str(user_id))
    os.makedirs(d, exist_ok=True)
    return d

@router.post("/upload_pdf", status_code=status.HTTP_201_CREATED)
def upload_and_parse_pdf(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
):
    """
    Upload a PDF and parse tabular transaction rows.
    Response: {"rows": [{"date": "YYYY-MM-DD" | None, "description": str, "amount": float}, ...]}
    """
    if not file:
        raise HTTPException(status_code=400, detail="Missing file")
    # basic filename sanitization
    filename = os.path.basename(file.filename or "")
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    user_dir = ensure_user_upload_dir(current_user.id)
    suffix = str(uuid.uuid4())[:8]
    save_name = f"{int(time.time())}_{suffix}_{filename}"
    dest_path = os.path.join(user_dir, save_name)
    try:
        with open(dest_path, "wb") as f:
            f.write(file.file.read())
    finally:
        try:
            file.file.close()
        except Exception:
            pass

    # call existing parser
    parsed = parse_transactions_from_pdf(dest_path) or []
    # normalize parsed rows: ensure keys and types
    normalized = []
    for r in parsed:
        try:
            amt = r.get("amount")
            if amt is None:
                continue
            # ensure float
            amount = float(amt)
        except Exception:
            continue
        date_val = r.get("date")
        # keep as string if provided; no strict validation here
        normalized.append({
            "date": date_val,
            "description": r.get("description") or "",
            "amount": amount,
        })

    return {"rows": normalized, "file": os.path.relpath(dest_path, os.getcwd())}

class BulkCreatePayload(Base := Dict):  # type: ignore - simple typing
    pass

@router.post("/bulk", status_code=status.HTTP_201_CREATED)
def bulk_create_transactions(payload: Dict[str, Any], current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db_dep)):
    """
    Accept JSON payload: {"rows": [{"date":"YYYY-MM-DD" (or null), "description":"...", "amount":123.45, "type":"expense"|"income" (optional)} , ...]}
    Creates transactions for current_user. If date is missing, uses today. Type defaults to "expense" for negative amounts? We'll default to "expense".
    Returns created count and sample IDs.
    """
    rows = payload.get("rows")
    if not rows or not isinstance(rows, list):
        raise HTTPException(status_code=400, detail="Missing rows array in payload")
    created = []
    try:
        for r in rows:
            try:
                amount = float(r.get("amount"))
            except Exception:
                continue
            ttype = r.get("type") or ("income" if amount > 0 and r.get("type") is None and False else "expense")
            # allow explicit 'income' or 'expense', otherwise default to "expense"
            if ttype not in ("income", "expense"):
                ttype = "expense"
            # date handling
            date_str = r.get("date")
            if date_str:
                try:
                    # accept iso-like date strings
                    dt = datetime.fromisoformat(date_str).date()
                except Exception:
                    # try YYYY-MM-DD via split
                    try:
                        parts = date_str.split("T")[0]
                        dt = datetime.fromisoformat(parts).date()
                    except Exception:
                        dt = datetime.utcnow().date()
            else:
                dt = datetime.utcnow().date()

            txn = models.Transaction(
                user_id=current_user.id,
                type=models.TransactionType[ttype],
                amount=Decimal(str(round(amount, 2))),
                currency=r.get("currency", "INR"),
                date=dt,
                description=r.get("description") or None,
                category_id=r.get("category_id"),
            )
            db.add(txn)
            created.append(txn)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create transactions: {exc}")
    # refresh to get ids
    for t in created:
        db.refresh(t)
    return {"created": len(created), "ids": [t.id for t in created]}
