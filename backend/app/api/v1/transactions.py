# app/api/v1/transactions.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from datetime import date, datetime
from decimal import Decimal

from app.api.v1.deps import get_current_user, get_db_dep
from app.db import models
from sqlalchemy import func

router = APIRouter(tags=["transactions"])

def txn_to_dict(txn: models.Transaction) -> Dict[str, Any]:
    return {
        "id": txn.id,
        "user_id": txn.user_id,
        "type": txn.type.value if txn.type is not None else None,
        "amount": str(txn.amount),
        "currency": txn.currency,
        "date": txn.date.isoformat() if txn.date else None,
        "description": txn.description,
        "category_id": txn.category_id,
        "category": {"id": txn.category.id, "name": txn.category.name} if getattr(txn, "category", None) else None,
        "created_at": txn.created_at.isoformat() if getattr(txn, "created_at", None) else None,
    }

@router.get("", response_model=Dict[str, Any])
def list_transactions(
    start_date: Optional[date] = Query(None, description="YYYY-MM-DD"),
    end_date: Optional[date] = Query(None, description="YYYY-MM-DD"),
    type: Optional[str] = Query(None, description="income or expense"),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=200),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db_dep),
):
    """
    Paginated list of transactions for current user, with optional date range and type filter.
    """
    q = db.query(models.Transaction).filter(models.Transaction.user_id == current_user.id)

    if start_date:
        q = q.filter(models.Transaction.date >= start_date)
    if end_date:
        q = q.filter(models.Transaction.date <= end_date)
    if type:
        if type not in ("income", "expense"):
            raise HTTPException(status_code=400, detail="type must be income or expense")
        # map string to Enum
        q = q.filter(models.Transaction.type == models.TransactionType[type])

    total = q.count()
    items = (
        q.order_by(models.Transaction.date.desc(), models.Transaction.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return {"total": total, "page": page, "per_page": per_page, "items": [txn_to_dict(t) for t in items]}

@router.post("", status_code=status.HTTP_201_CREATED)
def create_transaction(payload: Dict = None, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db_dep)):
    """
    Create a transaction. Expect JSON:
    {
      "type": "expense"|"income",
      "amount": 123.45,
      "currency": "INR",
      "date": "2025-10-07",
      "description": "...",
      "category_id": 1   # optional
    }
    """
    if not payload:
        raise HTTPException(status_code=400, detail="Missing payload")
    try:
        if payload.get("type") not in ("income", "expense"):
            raise HTTPException(status_code=400, detail="type must be 'income' or 'expense'")

        t = models.Transaction(
            user_id=current_user.id,
            type=models.TransactionType[payload["type"]],
            amount=Decimal(str(payload["amount"])),
            currency=payload.get("currency", "INR"),
            date=datetime.fromisoformat(payload["date"]).date(),
            description=payload.get("description"),
            category_id=payload.get("category_id"),
        )
        db.add(t)
        db.commit()
        db.refresh(t)
        return txn_to_dict(t)
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Missing field: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{txn_id}", response_model=Dict[str, Any])
def get_transaction(txn_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db_dep)):
    txn = db.query(models.Transaction).filter(models.Transaction.id == txn_id, models.Transaction.user_id == current_user.id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return txn_to_dict(txn)

@router.put("/{txn_id}")
def update_transaction(txn_id: int, payload: Dict = None, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db_dep)):
    txn = db.query(models.Transaction).filter(models.Transaction.id == txn_id, models.Transaction.user_id == current_user.id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if payload is None:
        raise HTTPException(status_code=400, detail="Missing payload")
    # update fields
    if "type" in payload:
        txn.type = models.TransactionType[payload["type"]]
    if "amount" in payload:
        txn.amount = Decimal(str(payload["amount"]))
    if "currency" in payload:
        txn.currency = payload["currency"]
    if "date" in payload:
        txn.date = datetime.fromisoformat(payload["date"]).date()
    if "description" in payload:
        txn.description = payload["description"]
    if "category_id" in payload:
        txn.category_id = payload["category_id"]
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn_to_dict(txn)

@router.delete("/{txn_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(txn_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db_dep)):
    txn = db.query(models.Transaction).filter(models.Transaction.id == txn_id, models.Transaction.user_id == current_user.id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(txn)
    db.commit()
    return None
