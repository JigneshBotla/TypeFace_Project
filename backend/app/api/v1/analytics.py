# app/api/v1/analytics.py
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import date

from app.api.v1.deps import get_current_user, get_db
from app.db import models
from sqlalchemy import func

router = APIRouter()

@router.get("/by_category", response_model=List[Dict[str,Any]])
def expenses_by_category(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(models.Category.name.label("category"), func.sum(models.Transaction.amount).label("total")) \
        .join(models.Transaction, models.Transaction.category_id == models.Category.id) \
        .filter(models.Category.user_id == current_user.id, models.Transaction.type == models.TransactionType.expense)
    if start_date:
        q = q.filter(models.Transaction.date >= start_date)
    if end_date:
        q = q.filter(models.Transaction.date <= end_date)
    q = q.group_by(models.Category.name).order_by(func.sum(models.Transaction.amount).desc())
    rows = q.all()
    return [{"category": r.category, "total": float(r.total or 0)} for r in rows]

@router.get("/by_date", response_model=List[Dict[str,Any]])
def expenses_by_date(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(models.Transaction.date.label("date"), func.sum(models.Transaction.amount).label("total")) \
        .filter(models.Transaction.user_id == current_user.id, models.Transaction.type == models.TransactionType.expense)
    if start_date:
        q = q.filter(models.Transaction.date >= start_date)
    if end_date:
        q = q.filter(models.Transaction.date <= end_date)
    q = q.group_by(models.Transaction.date).order_by(models.Transaction.date)
    rows = q.all()
    return [{"date": r.date.isoformat(), "total": float(r.total or 0)} for r in rows]
