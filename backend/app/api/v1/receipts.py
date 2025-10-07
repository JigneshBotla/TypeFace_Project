# app/api/v1/receipts.py
import os
import time
import uuid
import json
import logging
from typing import List

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, get_db_dep
from app.schemas.receipt import ReceiptOut
from app.db import models
from app.services.receipts import ocr_image_to_text, parse_receipt_text
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)
router = APIRouter()

# where to store uploads (relative to backend root)
UPLOAD_ROOT = os.path.abspath(os.path.join(os.getcwd(), "uploads"))

def ensure_user_upload_dir(user_id: int) -> str:
    d = os.path.join(UPLOAD_ROOT, str(user_id))
    os.makedirs(d, exist_ok=True)
    return d

def _process_receipt_in_background(receipt_id: int, rel_path: str) -> None:
    """
    Background worker: open a fresh DB session, run OCR & parsing,
    save raw_text and parsed_json back to the Receipt record.
    """
    db = SessionLocal()
    try:
        rec = db.query(models.Receipt).filter(models.Receipt.id == receipt_id).first()
        if not rec:
            logger.warning("Background OCR: receipt id %s not found", receipt_id)
            return

        abs_path = os.path.join(os.getcwd(), rel_path)
        try:
            raw = ocr_image_to_text(abs_path) or ""
        except Exception as exc:
            # OCR failed (missing tesseract or runtime error). Log and store empty raw_text.
            logger.exception("OCR failed for receipt %s (%s): %s", receipt_id, abs_path, exc)
            raw = ""

        parsed = {}
        try:
            parsed = parse_receipt_text(raw or "")
        except Exception as exc:
            logger.exception("Parsing receipt text failed for receipt %s: %s", receipt_id, exc)
            parsed = {"total": None, "date": None, "merchant": None, "raw_lines": []}

        # persist results (store parsed_json as JSON string)
        try:
            rec.raw_text = raw
            rec.parsed_json = json.dumps(parsed, ensure_ascii=False)
            db.add(rec)
            db.commit()
            logger.info("Background OCR complete for receipt %s", receipt_id)
        except Exception:
            logger.exception("Failed to save OCR result for receipt %s", receipt_id)
            db.rollback()
    finally:
        db.close()

@router.post("", response_model=ReceiptOut, status_code=status.HTTP_201_CREATED)
def upload_receipt(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db_dep),
):
    # validate file type (basic)
    filename = os.path.basename(file.filename or "")
    if len(filename) == 0:
        raise HTTPException(status_code=400, detail="Missing filename")

    user_dir = ensure_user_upload_dir(current_user.id)
    # create unique filename: <timestamp>_<uuid>_<original>
    suffix = str(uuid.uuid4())[:8]
    save_name = f"{int(time.time())}_{suffix}_{filename}"
    dest_path = os.path.join(user_dir, save_name)

    # save file
    try:
        with open(dest_path, "wb") as f:
            content = file.file.read()
            f.write(content)
    finally:
        try:
            file.file.close()
        except Exception:
            pass

    # create DB record (raw_text/parsed_json empty for now)
    rel_path = os.path.relpath(dest_path, os.getcwd())
    rec = models.Receipt(
        user_id=current_user.id,
        file_path=rel_path,
        raw_text="",
        parsed_json=json.dumps({"total": None, "date": None, "merchant": None, "raw_lines": []}),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    # schedule background OCR + parse job (non-blocking)
    background_tasks.add_task(_process_receipt_in_background, rec.id, rec.file_path)

    return rec

@router.get("", response_model=List[ReceiptOut])
def list_receipts(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db_dep),
):
    rows = (
        db.query(models.Receipt)
        .filter(models.Receipt.user_id == current_user.id)
        .order_by(models.Receipt.uploaded_at.desc())
        .all()
    )
    return rows

@router.get("/{receipt_id}", response_model=ReceiptOut)
def get_receipt(
    receipt_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db_dep),
):
    rec = (
        db.query(models.Receipt)
        .filter(models.Receipt.id == receipt_id, models.Receipt.user_id == current_user.id)
        .first()
    )
    if not rec:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return rec

@router.get("/{receipt_id}/download")
def download_receipt(
    receipt_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db_dep),
):
    rec = (
        db.query(models.Receipt)
        .filter(models.Receipt.id == receipt_id, models.Receipt.user_id == current_user.id)
        .first()
    )
    if not rec:
        raise HTTPException(status_code=404, detail="Receipt not found")

    path = os.path.join(os.getcwd(), rec.file_path)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found on disk")
    return FileResponse(path, filename=os.path.basename(path))

@router.delete("/{receipt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_receipt(
    receipt_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db_dep),
):
    rec = (
        db.query(models.Receipt)
        .filter(models.Receipt.id == receipt_id, models.Receipt.user_id == current_user.id)
        .first()
    )
    if not rec:
        raise HTTPException(status_code=404, detail="Receipt not found")

    # delete file (best-effort)
    try:
        disk_path = os.path.join(os.getcwd(), rec.file_path)
        if os.path.exists(disk_path):
            os.remove(disk_path)
    except Exception:
        logger.exception("Failed to delete receipt file %s", rec.file_path)

    db.delete(rec)
    db.commit()
    return None
