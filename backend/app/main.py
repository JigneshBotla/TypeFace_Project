# app/main.py
from fastapi import FastAPI
from app.api.v1 import health, auth, transactions, categories, receipts
from fastapi.staticfiles import StaticFiles
import os
from app.api.v1 import analytics
# app/main.py (add)
from app.api.v1 import transactions_pdf

app = FastAPI(title="Finance API", version="0.1.0")
from fastapi.middleware.cors import CORSMiddleware

# ensure absolute uploads path — same as receipts service uses
UPLOAD_ROOT = os.path.abspath(os.path.join(os.getcwd(), "uploads"))
os.makedirs(UPLOAD_ROOT, exist_ok=True)

# serve files under /uploads so browser can GET /uploads/<user>/<file>
app.mount("/uploads", StaticFiles(directory=UPLOAD_ROOT), name="uploads")

app.add_middleware(
  CORSMiddleware,
  allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

app.include_router(transactions_pdf.router, prefix="/api/v1/transactions", tags=["transactions_pdf"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(categories.router, prefix="/api/v1/categories", tags=["categories"])
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(transactions.router, prefix="/api/v1/transactions", tags=["transactions"])
app.include_router(receipts.router, prefix="/api/v1/receipts", tags=["receipts"])

@app.get("/")
def root():
    return {"message": "Finance API - visit /api/v1/health"}
