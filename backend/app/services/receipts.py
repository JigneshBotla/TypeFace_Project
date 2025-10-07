# app/services/receipts.py
import os
import re
import json
import logging
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

# optionally configure a default Tesseract path here (Windows example).
# You can also set env var TESSERACT_CMD to override at runtime.
_DEFAULT_TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# optional image / OCR libs (don't fail import if missing)
try:
    from PIL import Image, ImageOps, ImageFilter  # type: ignore
    PIL_AVAILABLE = True
except Exception:
    Image = None  # type: ignore
    ImageOps = None  # type: ignore
    ImageFilter = None  # type: ignore
    PIL_AVAILABLE = False

try:
    import pytesseract  # type: ignore
    PYTESS_AVAILABLE = True
except Exception:
    pytesseract = None  # type: ignore
    PYTESS_AVAILABLE = False

# optional smart date parser
try:
    from dateutil import parser as dateparser  # type: ignore
    DATEPARSER_AVAILABLE = True
except Exception:
    dateparser = None  # type: ignore
    DATEPARSER_AVAILABLE = False


def _maybe_configure_tesseract_from_env() -> None:
    """If user set TESSERACT_CMD env var, apply it to pytesseract. Otherwise apply default if present."""
    if not PYTESS_AVAILABLE:
        return

    cmd = os.environ.get("TESSERACT_CMD", None)
    if not cmd and os.path.exists(_DEFAULT_TESSERACT):
        cmd = _DEFAULT_TESSERACT

    if cmd:
        try:
            pytesseract.pytesseract.tesseract_cmd = cmd
            logger.debug("Configured pytesseract command: %s", cmd)
        except Exception:
            logger.exception("Failed to set pytesseract command from env/default")


def _ensure_ocr_available() -> None:
    """Raise RuntimeError if OCR dependencies (PIL + pytesseract) are not available."""
    if not (PIL_AVAILABLE and PYTESS_AVAILABLE):
        raise RuntimeError(
            "OCR not available. Install Pillow + pytesseract and the Tesseract binary.\n"
            "pip install pillow pytesseract python-dateutil\n"
            "then install tesseract (platform-specific). Optionally set TESSERACT_CMD env var."
        )
    # apply any env override/default
    _maybe_configure_tesseract_from_env()


def preprocess_image_for_ocr(img: "Image.Image") -> "Image.Image":
    """
    Preprocess a PIL image in-memory to improve OCR accuracy:
      - auto-orient (if EXIF)
      - convert to L (grayscale)
      - upscale small images
      - mild denoise and autocontrast
    Returns the processed PIL image.
    """
    if not PIL_AVAILABLE:
        raise RuntimeError("Pillow not available")

    try:
        # auto-orient if EXIF present
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass

        # convert to RGB then to grayscale
        if img.mode not in ("RGB", "RGBA", "L"):
            img = img.convert("RGB")
        gray = img.convert("L")

        w, h = gray.size
        # upscale very small images to improve OCR accuracy
        if w < 600:
            scale = max(1, int(600 / max(1, w)))
            new_size = (w * scale, h * scale)
            gray = gray.resize(new_size, Image.Resampling.LANCZOS)

        # small median filter to remove salt/pepper
        try:
            gray = gray.filter(ImageFilter.MedianFilter(size=3))
        except Exception:
            pass

        # autocontrast to improve dynamic range
        try:
            gray = ImageOps.autocontrast(gray)
        except Exception:
            pass

        return gray
    except Exception as exc:  # pragma: no cover - safety
        logger.exception("preprocess_image_for_ocr failed: %s", exc)
        return img


def ocr_image_to_text(path: str) -> Optional[str]:
    """
    Return raw OCR text for an image file.
    Returns None if file not found. Raises RuntimeError if OCR libs missing.
    """
    if not os.path.exists(path):
        logger.debug("ocr_image_to_text: path does not exist: %s", path)
        return None

    _ensure_ocr_available()

    try:
        with Image.open(path) as img:
            img = img.copy()  # ensure image is usable after context close
        processed = preprocess_image_for_ocr(img)
        # run tesseract (language 'eng' by default)
        raw = pytesseract.image_to_string(processed, lang="eng")
        if raw is None:
            return ""
        # normalize lines: trim and remove excessive blank lines
        lines = [ln.rstrip() for ln in raw.splitlines() if ln.strip()]
        return "\n".join(lines).strip()
    except Exception as exc:
        logger.exception("OCR failed for %s: %s", path, exc)
        # bubble up a RuntimeError that callers can catch; return empty string otherwise
        raise RuntimeError(f"OCR failed: {exc}") from exc


# Number detection regex — matches 1,234.56 or 1234.56 or 1234 or 1 234,56 etc.
_NUMBER_RE = re.compile(
    r"(?<!\w)(?:[£$€¥]\s*)?([0-9]{1,3}(?:[ ,][0-9]{3})*(?:[.,][0-9]{2})|[0-9]+(?:[.,][0-9]{2}))"
)


def _normalize_numeric_token(token: str) -> Optional[float]:
    """
    Normalize numeric token like '1,234.56' or '1 234,56' to float.
    Returns None on failure.
    """
    if not token:
        return None
    # replace spaces, non-breaking spaces
    s = token.replace("\u00A0", "").replace(" ", "")
    # if both '.' and ',' present, heuristics: assume ',' thousand sep, '.' decimal OR vice versa
    if "," in s and "." in s:
        # if '.' occurs after ',' -> usual US style 1,234.56
        if s.rfind(".") > s.rfind(","):
            s = s.replace(",", "")
        else:
            s = s.replace(".", "").replace(",", ".")
    else:
        # single separator case: if comma present and decimals look like two digits, treat comma as decimal sep
        if "," in s and re.match(r"^[0-9]+,[0-9]{2}$", s):
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    try:
        return float(s)
    except Exception:
        return None


def extract_total(text: str) -> Optional[float]:
    """
    Heuristic: scan bottom-up for lines containing 'total'/'amount' words and a number.
    Fallback: pick the largest number-like token found.
    Returns float or None.
    """
    if not text:
        return None

    # normalize line endings and get non-empty lines
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    # bottom-up scan for keywords
    for ln in reversed(lines):
        if re.search(r"\b(total|amount|balance|grand total|amount due|total due|net)\b", ln, re.I):
            m = _NUMBER_RE.search(ln)
            if m:
                val = _normalize_numeric_token(m.group(1))
                if val is not None:
                    return val
                else:
                    logger.debug("failed to parse total candidate '%s' from line '%s'", m.group(1), ln)

    # fallback: find all numbers and pick the largest (common heuristic)
    numbers: List[float] = []
    for m in _NUMBER_RE.finditer(text):
        raw = m.group(1)
        nv = _normalize_numeric_token(raw)
        if nv is not None:
            numbers.append(nv)
    if numbers:
        return max(numbers)
    return None


# Simple date regex candidates (ISO, D/M/Y, D Mon YYYY)
_DATE_RE = re.compile(
    r"(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})",
    re.I,
)


def extract_date(text: str) -> Optional[str]:
    """
    Attempt to find and normalize a date string to ISO (YYYY-MM-DD).
    Uses dateutil if available, otherwise uses regex heuristics.
    """
    if not text:
        return None

    # try regex first
    m = _DATE_RE.search(text)
    if m:
        candidate = m.group(1)
        if DATEPARSER_AVAILABLE:
            try:
                dt = dateparser.parse(candidate, fuzzy=True)
                if dt:
                    return dt.date().isoformat()
            except Exception:
                logger.debug("dateparser failed on %s", candidate)
        else:
            # try to normalize simple yyyy-mm-dd or dd/mm/yyyy
            try:
                parts = re.split(r"[-/ ]", candidate)
                if len(parts) >= 3 and len(parts[0]) == 4:
                    # assume yyyy-mm-dd
                    y, mm, dd = parts[0], parts[1], parts[2]
                    return f"{int(y):04d}-{int(mm):02d}-{int(dd):02d}"
                else:
                    # dd/mm/yyyy or similar; prefer dd/mm/yyyy
                    d, m_, y = parts[0], parts[1], parts[2]
                    if len(y) == 2:
                        y = "20" + y
                    return f"{int(y):04d}-{int(m_):02d}-{int(d):02d}"
            except Exception:
                logger.debug("regex date normalization failed for %s", candidate)

    # final fallback: try dateparser on full text if available
    if DATEPARSER_AVAILABLE:
        try:
            dt = dateparser.parse(text, fuzzy=True)
            if dt:
                return dt.date().isoformat()
        except Exception:
            logger.debug("dateparser fallback failed")

    return None


def parse_receipt_text(text: str) -> Dict:
    """
    Parse OCR text into a small dict with keys:
      - total: float | None
      - date: 'YYYY-MM-DD' | None
      - merchant: str | None
      - raw_lines: list[str] (bounded)
    """
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]

    merchant = None
    if lines:
        # heuristic: first line usually merchant (skip if looks numeric only)
        first = lines[0]
        if not re.match(r"^[\d\W]+$", first):  # if not numeric/punctuation only
            merchant = first

    total = extract_total(text or "")
    date = extract_date(text or "")

    parsed = {
        "total": total,
        "date": date,
        "merchant": merchant,
        "raw_lines": lines[:200],  # keep bounded amount
    }
    return parsed


# export-friendly names for router imports
__all__ = ["ocr_image_to_text", "parse_receipt_text", "extract_total", "extract_date"]
