# app/api/v1/categories.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate
from app.api.v1.deps import get_db_dep, get_current_user
from app.db import models

router = APIRouter(tags=["categories"])

@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db_dep), current_user: models.User = Depends(get_current_user)):
    # enforce name uniqueness for this user (optional - change to global if desired)
    existing = db.query(models.Category).filter(models.Category.user_id == current_user.id, models.Category.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category with this name already exists")
    new = models.Category(user_id=current_user.id, name=payload.name, description=payload.description)
    db.add(new)
    db.commit()
    db.refresh(new)
    return new

@router.get("", response_model=List[CategoryOut])
def list_categories(skip: int = 0, limit: int = 100, db: Session = Depends(get_db_dep), current_user: models.User = Depends(get_current_user)):
    items = db.query(models.Category).filter(models.Category.user_id == current_user.id).offset(skip).limit(limit).all()
    return items

@router.get("/{category_id}", response_model=CategoryOut)
def get_category(category_id: int, db: Session = Depends(get_db_dep), current_user: models.User = Depends(get_current_user)):
    cat = db.query(models.Category).filter(models.Category.id == category_id, models.Category.user_id == current_user.id).first()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return cat

@router.put("/{category_id}", response_model=CategoryOut)
def update_category(category_id: int, payload: CategoryUpdate, db: Session = Depends(get_db_dep), current_user: models.User = Depends(get_current_user)):
    cat = db.query(models.Category).filter(models.Category.id == category_id, models.Category.user_id == current_user.id).first()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    if payload.name is not None:
        cat.name = payload.name
    if payload.description is not None:
        cat.description = payload.description
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat

@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: Session = Depends(get_db_dep), current_user: models.User = Depends(get_current_user)):
    cat = db.query(models.Category).filter(models.Category.id == category_id, models.Category.user_id == current_user.id).first()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    db.delete(cat)
    db.commit()
    return None
