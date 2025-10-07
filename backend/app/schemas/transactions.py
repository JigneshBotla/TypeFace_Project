# app/schemas/transactions.py
from pydantic import BaseModel, condecimal
from typing import Optional
from datetime import date

class TransactionBase(BaseModel):
    type: str  # "income" or "expense"
    amount: condecimal(max_digits=12, decimal_places=2)
    currency: Optional[str] = "INR"
    date: date
    description: Optional[str] = None

class TransactionCreate(TransactionBase):
    pass

class TransactionUpdate(BaseModel):
    type: Optional[str] = None
    amount: Optional[condecimal(max_digits=12, decimal_places=2)] = None
    currency: Optional[str] = None
    date: Optional[date] = None
    description: Optional[str] = None

class TransactionRead(TransactionBase):
    id: int

    class Config:
        orm_mode = True

class TransactionList(BaseModel):
    items: list[TransactionRead]
    total: int
    page: int
    page_size: int
