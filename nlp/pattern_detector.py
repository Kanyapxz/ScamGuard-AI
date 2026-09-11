import re
from nlp.preprocess import extract_urls


def analyze_link_suspicion(text: str) -> list[str]:
    signals = []
    text = str(text)
    urls = extract_urls(text)

    if re.search(r"(bit\.ly|tinyurl\.com|goo\.gl|t\.co|rb\.gy|cutt\.ly|short\.link|rebrand\.ly|is\.gd)", text, re.I):
        signals.append("ลิงก์ถูกย่อ อาจซ่อนปลายทางจริง")

    if re.search(r"(adsly\.click|adf\.ly|linkvertise)", text, re.I):
        signals.append("พบลิงก์แนว redirect / tracking / โฆษณา")

    if re.search(r"(\.xyz|\.top|\.club|\.online|\.site|\.click|\.live|\.cam|\.link)", text, re.I):
        signals.append("โดเมนมีลักษณะค่อนข้างน่าสงสัยหรือพบน้อย")

    if re.search(r"(คลิก|กดลิงก์|กดที่นี่|ลิงก์นี้|ลิ้งนี้|กดเลย|กดด่วน|สมัครเลย|สมัครด่วน|ดูเลย|เข้าเลย)", text, re.I):
        signals.append("มีถ้อยคำชักชวนให้คลิกลิงก์")

    if re.search(r"(paypal-|bank-|secure-|verify-|login-|update-|kbank-|scb-|ktb-|gov-|thai-)", text, re.I):
        signals.append("ข้อความมีลักษณะคล้ายแอบอ้างบริการหรือหน่วยงานจริง")

    if urls:
        signals.append("พบ URL / ลิงก์ภายนอก")

    # ลบค่าซ้ำ
    result = []
    for item in signals:
        if item not in result:
            result.append(item)
    return result


def detect_extra_patterns(text: str) -> dict:
    text = str(text)

    return {
        "has_gambling": int(bool(re.search(
            r"(พนัน|เว็บพนัน|บาคาร่า|สล็อต|หวย|คาสิโน|แทงบอล|เดิมพัน|ฝากถอน|เครดิตฟรี|เว็บตรง|joker|pg)",
            text,
            re.I
        ))),
        "has_investment_hype": int(bool(re.search(
            r"(ลงทุน|กำไร|ผลตอบแทน|คืนทุน|กำไรเกินคาด|รับผลตอบแทน|รวยเร็ว|เงินไว|ทำเงิน|เทรด)",
            text,
            re.I
        ))),
        "has_prize_bait": int(bool(re.search(
            r"(ยินดีด้วย|ได้รับรางวัล|รับฟรี|ของฟรี|แจกฟรี|โบนัสฟรี|รับสิทธิ์|สิทธิพิเศษ)",
            text,
            re.I
        ))),
        "has_impersonation": int(bool(re.search(
            r"(ธนาคาร|ขนส่ง|ไปรษณีย์|กรม|รัฐบาล|ตำรวจ|ศาล|บริษัท|เจ้าหน้าที่|แอดมิน|ผู้ดูแลระบบ)",
            text,
            re.I
        ))),
        "has_clickbait": int(bool(re.search(
            r"(คลิก|กดเลย|กดด่วน|สมัครเลย|สมัครตอนนี้|เข้าเลย|รับเลย|ดูรายละเอียด|ดูเลย)",
            text,
            re.I
        ))),
    }


def build_indicator_labels(structured: dict, extra: dict) -> list[str]:
    labels = {
        "🔗 พบ URL / ลิงก์ภายนอก": structured["has_url"],
        "📞 พบเบอร์โทร / รหัส USSD": structured["has_phone"],
        "⚡ มีคำเร่งด่วน / กดดัน": structured["has_urgency"],
        "💰 มีบริบทด้านเงิน / รางวัล / โปรโมชั่น": structured["has_money"],
        "🪪 มีการกล่าวถึงข้อมูลส่วนตัว": structured["has_personal_info_request"],
        "🎰 มีคำเกี่ยวกับพนัน / เครดิตฟรี / ฝากถอน": extra["has_gambling"],
        "📈 มีคำชวนลงทุน / กำไร / ผลตอบแทน": extra["has_investment_hype"],
        "🎁 มีคำล่อรางวัล / ของฟรี": extra["has_prize_bait"],
        "🏢 มีลักษณะคล้ายแอบอ้างหน่วยงาน": extra["has_impersonation"],
    }
    return [label for label, found in labels.items() if found]