# app/schemas/receipt.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ReceiptOut(BaseModel):
    id: int
    user_id: int
    file_path: str
    uploaded_at: datetime
    raw_text: Optional[str] = None
    parsed_json: Optional[str] = None

    class Config:
        orm_mode = True

class ReceiptCreate(BaseModel):
    # no body fields needed for simple upload; kept for future metadata
    pass
