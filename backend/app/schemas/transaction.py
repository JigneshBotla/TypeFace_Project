# app/schemas/transaction.py
from pydantic import BaseModel, Field
from datetime import date
from typing import Optional, List
from decimal import Decimal
from enum import Enum

class TransactionType(str, Enum):
    income = "income"
    expense = "expense"

class TransactionCreate(BaseModel):
    type: TransactionType
    amount: Decimal = Field(..., gt=0)
    currency: str = "INR"
    date: date
    description: Optional[str] = None

class TransactionOut(BaseModel):
    id: int
    type: TransactionType
    amount: Decimal
    currency: str
    date: date
    description: Optional[str]

    class Config:
        orm_mode = True
