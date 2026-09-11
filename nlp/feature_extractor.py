import re
from nlp.preprocess import clean_text


def extract_structured_features(text: str) -> dict:
    """
    ต้องรักษาลำดับให้ตรงกับตอน train:
    [msg_length, word_count, has_url, has_phone, has_urgency, has_money, has_personal_info_request]
    """
    text = str(text)
    cleaned = clean_text(text)

    has_url = int(bool(re.search(
        r"(http|https|www\.|bit\.ly|tinyurl|goo\.gl|adsly|adf\.ly|\.com|\.net|\.org|\.click|ลิงก์|ลิ้ง|link|คลิก)",
        text,
        re.I
    )))

    has_phone = int(bool(re.search(
        r"(\d{3}[-.\s]?\d{3}[-.\s]?\d{4}|\d{10}|\*\d+#)",
        text
    )))

    has_urgency = int(bool(re.search(
        r"(ด่วน|ภายใน|วันนี้|ทันที|โปรด|กรุณา|ระงับ|ล็อก|ถูกอายัด|ค้างชำระ|รีบ|ด่วนที่สุด|ทันด่วน)",
        text,
        re.I
    )))

    has_money = int(bool(re.search(
        r"(บาท|฿|รางวัล|เงิน|ฟรี|จ่าย|ชำระ|โอน|โบนัส|ถอน|ฝาก|เครดิต|โปร|โปรโมชัน|รายได้|ลงทุน|กำไร|ผลตอบแทน)",
        text,
        re.I
    )))

    has_personal_info_request = int(bool(re.search(
        r"(บัตรประชาชน|otp|pin|รหัสผ่าน|เลขบัญชี|ข้อมูลส่วนตัว|ยืนยันตัวตน|ส่งรูป|ที่อยู่)",
        text,
        re.I
    )))

    return {
        "msg_length": len(cleaned), #ความยาวข้อความ
        "word_count": len(cleaned.split()), #จำนวนคำในข้อความ
        "has_url": has_url, #มี URL หรือไม่ 
        "has_phone": has_phone, #มีหมายเลขโทรศัพท์หรือไม่ 
        "has_urgency": has_urgency, #มีคำที่แสดงถึงความเร่งด่วนหรือไม่
        "has_money": has_money, #มีคำที่เกี่ยวข้องกับเงินหรือไม่
        "has_personal_info_request": has_personal_info_request, #มีคำที่ขอข้อมูลส่วนตัวหรือไม่
    }