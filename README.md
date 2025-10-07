# Finance Project

## Run locally
1. create virtualenv & install:
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt

   Required extras (for OCR and PDF import):
   pip install pillow pytesseract python-dateutil pdfplumber

   Windows: install Tesseract OCR and set environment variable TESSERACT_CMD if needed.

2. ensure .env contains DATABASE_URL and SECRET_KEY
3. create DB tables (dev only):
   python create_tables.py
4. start server:
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

## API highlights
- POST /api/v1/auth/register  (body: email, password, username)
- POST /api/v1/auth/login  -> returns access_token
- GET /api/v1/transactions?page=1&per_page=25&start_date=YYYY-MM-DD
- GET /api/v1/analytics/by_category?start_date=&end_date=
- POST /api/v1/receipts (multipart file) -> upload + OCR
- GET /uploads/<user>/<file> (static, if uploads mounted)

## Notes
- For PDF imports use POST /api/v1/import/pdf (not included by default) — accepts pdf file and returns parsed rows for review.
