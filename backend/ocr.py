"""
OCR processing. Wraps pytesseract with sensible defaults for game UI text.
Falls back gracefully if Tesseract is not installed.
"""
import json
import os
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

_root = Path(__file__).resolve().parents[1]
with open(_root / "config.json") as _f:
    _cfg = json.load(_f)

_TESS_PATH: str = _cfg.get("tesseract_path", "")
_OCR_LANG: str = _cfg.get("ocr_lang", "eng")

try:
    import pytesseract
    if _TESS_PATH and os.path.exists(_TESS_PATH):
        pytesseract.pytesseract.tesseract_cmd = _TESS_PATH
    _tess_available = True
except ImportError:
    _tess_available = False


def _preprocess(img: Image.Image) -> Image.Image:
    """Upscale small images and sharpen for better OCR accuracy on game UIs."""
    w, h = img.size
    if w < 1280:
        scale = 1280 / w
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    img = img.filter(ImageFilter.SHARPEN)
    return img


def extract_text(image_path: str) -> str:
    """Run OCR on the given image path and return the raw text."""
    if not _tess_available:
        return "[OCR unavailable — install pytesseract and Tesseract-OCR]"

    try:
        img = Image.open(image_path).convert("RGB")
        img = _preprocess(img)
        text = pytesseract.image_to_string(
            img,
            lang=_OCR_LANG,
            config="--psm 3 --oem 3",
        )
        return text.strip()
    except Exception as exc:
        return f"[OCR error: {exc}]"


def extract_text_region(image_path: str, box: tuple) -> str:
    """OCR a specific (left, upper, right, lower) crop of the image."""
    if not _tess_available:
        return ""
    try:
        img = Image.open(image_path).convert("RGB").crop(box)
        img = _preprocess(img)
        return pytesseract.image_to_string(img, lang=_OCR_LANG, config="--psm 6 --oem 3").strip()
    except Exception:
        return ""


def is_available() -> bool:
    return _tess_available
