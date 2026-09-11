"""
OCR Service — ดึงข้อความจากรูปภาพด้วย EasyOCR (รองรับไทย + อังกฤษ)

Usage:
    from services.ocr_service import ocr_extract_from_upload
    text = ocr_extract_from_upload(request.files["image"])

Design notes:
- Lazy-load EasyOCR Reader ครั้งแรกที่ถูกเรียก (~10–20 วินาที)
  Reader instance ถูก cache ไว้ตลอด lifetime ของ process
- ใช้ CPU เป็น default (gpu=False) เพื่อให้ deploy ได้ทุกที่
- Post-process text เพื่อแก้ปัญหาที่ EasyOCR มักพลาดกับ URL
  (แทรกช่องว่างรอบ . / : ทำให้ URL ใช้ไม่ได้)
"""
from __future__ import annotations

import re

# ── Config ────────────────────────────────────────────────────
OCR_LANGS = ["th", "en"]                     # ภาษาที่รองรับ
OCR_MAX_BYTES = 5 * 1024 * 1024              # 5 MB
OCR_ALLOWED_EXT = {"png", "jpg", "jpeg", "webp", "bmp"}
OCR_ALLOWED_MIME = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "image/bmp",
}


# ── Custom exception ─────────────────────────────────────────
class OCRError(Exception):
    """ข้อผิดพลาดจากระบบ OCR — ใช้ส่ง error message แบบผู้ใช้อ่านได้"""
    pass


# ── Lazy-loaded reader ───────────────────────────────────────
_reader = None


def _get_reader():
    """
    โหลด EasyOCR Reader ครั้งแรกที่ถูกเรียก แล้ว cache ไว้ใช้ซ้ำ

    เรียกตรง ๆ ใน app.py ตอน Flask start เพื่อ pre-warm ได้:
        from services.ocr_service import _get_reader
        _get_reader()
    """
    global _reader
    if _reader is None:
        try:
            import easyocr
        except ImportError as e:
            raise OCRError(
                "ยังไม่ได้ติดตั้ง EasyOCR — ติดตั้งด้วย: pip install easyocr"
            ) from e

        # gpu=False เพื่อให้ deploy ได้ทุกที่ ถ้ามี GPU เปลี่ยนเป็น True ได้
        _reader = easyocr.Reader(OCR_LANGS, gpu=False, verbose=False)
    return _reader


# ── Helpers ──────────────────────────────────────────────────
def _validate_upload(file_storage) -> None:
    """ตรวจ filename + MIME + size ก่อนประมวลผล"""
    if not file_storage or not file_storage.filename:
        raise OCRError("ไม่พบไฟล์แนบ กรุณาลองแนบรูปใหม่อีกครั้ง")

    filename = file_storage.filename.lower()
    ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
    if ext not in OCR_ALLOWED_EXT:
        raise OCRError(
            f"รูปแบบไฟล์ไม่รองรับ — ต้องเป็น {', '.join(sorted(OCR_ALLOWED_EXT))}"
        )

    mime = (file_storage.mimetype or "").lower()
    if mime and mime not in OCR_ALLOWED_MIME:
        raise OCRError("ประเภทไฟล์ไม่ถูกต้อง กรุณาแนบรูปภาพเท่านั้น")

    # Check size without reading full content
    file_storage.stream.seek(0, 2)  # seek to end
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size == 0:
        raise OCRError("ไฟล์ว่างเปล่า กรุณาลองแนบรูปใหม่")
    if size > OCR_MAX_BYTES:
        raise OCRError(
            f"ไฟล์มีขนาดใหญ่เกินไป (จำกัด {OCR_MAX_BYTES // (1024 * 1024)} MB)"
        )


def _read_image_bytes(file_storage) -> bytes:
    """อ่าน bytes ทั้งหมดจาก Werkzeug FileStorage"""
    file_storage.stream.seek(0)
    data = file_storage.stream.read()
    file_storage.stream.seek(0)
    return data


# ── URL post-processing ──────────────────────────────────────
# EasyOCR มักแทรกช่องว่างในที่ที่ไม่ควรมี เช่น:
#   "https://adsly.click/myash?code=c80"
#   → "https:  /adsly. click / myash?code=c80"
#
# ฟังก์ชันนี้จับคืนให้เป็น URL ที่ถูกต้อง เพื่อให้
#  (1) ระบบ link_checker ส่งไป Google Safe Browsing / VirusTotal ได้จริง
#  (2) ผู้ใช้เห็นข้อความที่ใกล้ต้นฉบับมากที่สุด

_SCHEME_FIX_RE = re.compile(r"\b(https?)\s*:\s*/\s*/?\s*", re.IGNORECASE)
_WWW_FIX_RE = re.compile(
    r"\bwww\s*\.\s*([a-zA-Z0-9\-]+)\s*\.\s*([a-zA-Z]{2,})\b",
    re.IGNORECASE,
)

# อักขระที่ถือเป็นส่วนของ URL (ไม่รวม whitespace)
_URL_CHAR_RE = re.compile(r"[A-Za-z0-9./?=&_\-#:%~+]")
# Punctuation ที่เป็นไปได้ว่าเป็นช่องว่างระหว่าง URL tokens ที่ EasyOCR แทรก
_URL_PUNCT = set("./?=&_-#%")


def _looks_like_url_continuation(after_space: str) -> bool:
    """
    ดูหลัง whitespace ว่า "token ถัดไปน่าจะเป็นส่วนต่อของ URL" ไหม
    ถือว่าต่อ URL ถ้า:
      - ขึ้นต้นด้วย URL punct (. / ? & = ฯลฯ)
      - หรือขึ้นต้นด้วย ASCII alphanumeric (ไม่ใช่ตัวไทยหรือสัญลักษณ์อื่น)
    """
    if not after_space:
        return False
    ch = after_space[0]
    if ch in _URL_PUNCT:
        return True
    # ASCII alphanumeric เท่านั้น — ตัวไทยและสัญลักษณ์อื่นถือว่า URL จบแล้ว
    return ch.isascii() and ch.isalnum()


def _extract_url_end(text: str, start: int) -> int:
    """
    เริ่มจาก position `start` (ตอนนี้ชี้อยู่หลัง "https://")
    อ่านต่อจนสุด URL แล้วคืน index ที่ URL จบ

    กฎ:
      - อักขระ URL (alnum, ./?=&_-#%) → กินไป
      - whitespace → ดูข้างหลัง ถ้า "ดูเหมือน URL ต่อ" → กินไปด้วย
                     ถ้าเป็นข้อความไทย/อื่น → URL จบ
    """
    i = start
    n = len(text)
    while i < n:
        ch = text[i]
        if _URL_CHAR_RE.match(ch):
            i += 1
            continue
        if ch in (" ", "\t"):
            # peek หลัง space (อาจมีหลาย space)
            j = i
            while j < n and text[j] in (" ", "\t"):
                j += 1
            if j < n and _looks_like_url_continuation(text[j:]):
                i = j  # ข้าม space กลุ่มนั้น ไปอ่าน URL ต่อ
                continue
            # ไม่ใช่ URL ต่อ → หยุดที่ตำแหน่ง i (ก่อน space)
            break
        # ตัวอักษรอื่น (ไทย, สัญลักษณ์ที่ไม่ใช่ URL) → URL จบ
        break
    return i


def _collapse_url_body(body: str) -> str:
    """ลบช่องว่างทั้งหมดใน body ของ URL"""
    return re.sub(r"\s+", "", body)


def _fix_ocr_urls(text: str) -> str:
    """
    แก้ URL ที่ EasyOCR ทำเพี้ยน 3 step:
      1. รวม scheme: "https:  /" | "https :/" → "https://"
      2. รวม "www . example . com" → "www.example.com"
      3. ภายใน URL (หลัง https?://): ปิดช่องว่างรอบ . / ? = & ฯลฯ
    """
    if not text:
        return text

    # 1. scheme — ทำก่อน เพื่อให้ step 3 หา "https://" ได้เจอ
    text = _SCHEME_FIX_RE.sub(r"\1://", text)

    # 2. www.x.y (ไม่มี scheme)
    text = _WWW_FIX_RE.sub(r"www.\1.\2", text)

    # 3. URL body cleanup — ใช้ scanner แทน regex pattern
    result = []
    i = 0
    n = len(text)
    while i < n:
        # หา "http://" หรือ "https://" starting at i
        m = re.match(r"(https?://)", text[i:], re.IGNORECASE)
        if m:
            scheme = m.group(1).lower()
            scheme_end = i + len(m.group(1))
            url_end = _extract_url_end(text, scheme_end)
            body = text[scheme_end:url_end]
            result.append(scheme + _collapse_url_body(body))
            i = url_end
        else:
            result.append(text[i])
            i += 1

    return "".join(result)


def _postprocess_text(text: str) -> str:
    """
    ทำความสะอาด OCR text ก่อนส่งกลับไปให้ผู้ใช้:
      - แก้ URL ที่ถูกแทรกช่องว่าง
      - ลบช่องว่างซ้ำในแต่ละบรรทัด
      - ตัดบรรทัดว่าง
    """
    if not text:
        return text

    # แก้ URL ก่อน (เพื่อให้ collapse ช่องว่างใน URL ทัน ก่อน normalize)
    text = _fix_ocr_urls(text)

    # normalize ช่องว่างในแต่ละบรรทัด + ตัดบรรทัดว่าง
    lines = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", line).strip()
        if line:
            lines.append(line)

    return "\n".join(lines)


# ── Public API ───────────────────────────────────────────────
def ocr_extract_from_upload(file_storage) -> str:
    """
    รับ Werkzeug FileStorage (จาก request.files["image"])
    คืนข้อความที่อ่านได้จากรูป (ผ่าน post-process แล้ว)

    Raises:
        OCRError: ถ้าไฟล์ไม่ถูกต้อง / อ่านไม่ได้ / ระบบ OCR ใช้ไม่ได้
    """
    _validate_upload(file_storage)
    image_bytes = _read_image_bytes(file_storage)

    try:
        reader = _get_reader()
    except OCRError:
        raise
    except Exception as e:
        raise OCRError(f"ระบบ OCR ไม่พร้อมใช้งาน: {e}") from e

    try:
        # detail=0 → คืนแค่ list ของ string (ไม่เอา bbox/confidence)
        # paragraph=True → รวมบรรทัดที่อยู่ใกล้กันให้เป็นย่อหน้าเดียว อ่านง่ายกว่า
        lines = reader.readtext(image_bytes, detail=0, paragraph=True)
    except Exception as e:
        raise OCRError(f"ไม่สามารถอ่านข้อความจากรูปได้: {e}") from e

    # รวมบรรทัดเป็นข้อความเดียว
    text = "\n".join(str(x).strip() for x in lines if str(x).strip())

    # Post-process: แก้ URL + normalize whitespace
    text = _postprocess_text(text)

    if not text:
        raise OCRError(
            "ไม่พบข้อความในรูป — อาจเป็นรูปภาพเปล่า หรือภาพไม่ชัดเกินไป"
        )

    return text


def get_ocr_limits() -> dict:
    """ข้อจำกัดของ OCR — ให้ frontend โชว์ให้ผู้ใช้ดู"""
    return {
        "max_bytes": OCR_MAX_BYTES,
        "max_mb": OCR_MAX_BYTES // (1024 * 1024),
        "allowed_ext": sorted(OCR_ALLOWED_EXT),
        "languages": OCR_LANGS,
    }