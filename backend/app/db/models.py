# app/db/models.py — canonical version with User, Transaction, Receipt, Category
from sqlalchemy import Column, Integer, String, DateTime, func, Numeric, Text, Date, ForeignKey, Enum
from sqlalchemy.orm import relationship
from .base import Base
import enum

class TransactionType(enum.Enum):
    income = "income"
    expense = "expense"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), nullable=True, unique=False)
    email = Column(String(255), nullable=True, unique=True, index=True)
    hashed_password = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # relationships
    transactions = relationship(
        "Transaction", back_populates="user", cascade="all, delete-orphan"
    )
    receipts = relationship(
        "Receipt", back_populates="user", cascade="all, delete-orphan"
    )
    categories = relationship(
        "Category", back_populates="user", cascade="all, delete-orphan"
    )

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(Enum(TransactionType), nullable=False)
    amount = Column(Numeric(12,2), nullable=False)
    currency = Column(String(10), default="INR")
    date = Column(Date, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # optional category relation
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    category = relationship("Category", back_populates="transactions")

    user = relationship("User", back_populates="transactions")

class Receipt(Base):
    __tablename__ = "receipts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_path = Column(String(1024), nullable=False)
    uploaded_at = Column(DateTime, server_default=func.now(), nullable=False)
    raw_text = Column(Text, nullable=True)
    parsed_json = Column(Text, nullable=True)

    user = relationship("User", back_populates="receipts")

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    description = Column(String(500), nullable=True)

    user = relationship("User", back_populates="categories")
    transactions = relationship("Transaction", back_populates="category")
