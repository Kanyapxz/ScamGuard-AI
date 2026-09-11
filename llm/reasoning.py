import re

from services.link_checker import LinkChecker
from rag.vector_store import RAGVectorStore
from ml.classifier import ScamClassifier
from nlp.pattern_detector import (
    analyze_link_suspicion,
    detect_extra_patterns,
    build_indicator_labels,
)
from services.ollama_client import OllamaClient
from llm.memory_manager import MemoryManager


class ScamReasoner:
    SITUATION_LABELS = {
        "not_clicked": "ยังไม่ได้กดลิงก์",
        "clicked_link": "กดลิงก์ไปแล้ว",
        "shared_info": "ให้ข้อมูลไปแล้ว",
        "sent_money": "โอนเงินไปแล้ว",
    }

    def __init__(self):
        self.classifier = ScamClassifier()
        self.ollama = OllamaClient()
        self.rag_store = RAGVectorStore()
        self.link_checker = LinkChecker()
        self.memory = MemoryManager()

    # =========================
    # SAFETY GUARD
    # =========================
    @staticmethod
    def is_harmful_request(text: str, mode: str = "detect") -> bool:
        text = str(text).lower().strip()

        # คำถามเชิงความรู้ / นิยาม / การป้องกัน => ไม่ควรถูกบล็อก
        safe_patterns = [
            r"คืออะไร",
            r"คือแบบไหน",
            r"คือยังไง",
            r"คือไร",
            r"หมายถึงอะไร",
            r"แปลว่าอะไร",
            r"อธิบาย",
            r"ยกตัวอย่าง",
            r"แตกต่างยังไง",
            r"ต่างกันยังไง",
            r"ป้องกันยังไง",
            r"ป้องกันอย่างไร",
            r"รับมือยังไง",
            r"รับมืออย่างไร",
            r"สังเกตยังไง",
            r"สังเกตอย่างไร",
            r"ดูยังไง",
            r"ดูอย่างไร",
            r"ตรวจสอบยังไง",
            r"ตรวจสอบอย่างไร",
        ]

        if any(re.search(pattern, text, re.I) for pattern in safe_patterns):
            return False

        # คำขอเชิงโจมตี / ขอวิธีทำผิด => ต้องบล็อก
        harmful_patterns = [
            r"สมมุติว่าคุณเป็นสแกมเมอร์",
            r"เป็นสแกมเมอร์",
            r"วิธีหลอก",
            r"หลอกเอาเงิน",
            r"หลอกคนแก่",
            r"โกงเงิน",
            r"เขียนข้อความหลอก",
            r"ช่วยเขียนข้อความหลอก",
            r"ช่วยร่างข้อความหลอก",
            r"ทำยังไงให้คนโอนเงิน",
            r"ทำยังไงให้เหยื่อเชื่อ",
            r"ปลอมเป็นธนาคารยังไง",
            r"ปลอมเป็นตำรวจยังไง",
            r"ปลอมเป็นเจ้าหน้าที่ยังไง",
            r"แอบอ้างยังไงให้เนียน",
            r"ขโมย otp",
            r"ขโมยรหัส",
            r"ขโมยข้อมูล",
            r"ทำฟิชชิง",
            r"สร้างฟิชชิง",
            r"ทำเว็บปลอม",
            r"ทำลิงก์ปลอม",
        ]

        return any(re.search(pattern, text, re.I) for pattern in harmful_patterns)

    @staticmethod
    def get_safe_refusal() -> str:
        return (
            "ผมไม่สามารถช่วยให้คำแนะนำในการหลอกลวง เอาเงินผู้อื่น "
            "หรือทำให้ผู้อื่นเสียหายได้ครับ แต่ผมช่วยอธิบายสัญญาณเตือน "
            "วิธีป้องกัน และแนวทางรับมืออย่างปลอดภัยได้"
        )

 
    def infer_topic(self, text: str, mode: str = "detect") -> str:
        text = str(text).lower().strip()

        if mode == "knowledge":
            if re.search(r"(scammer|สแกมเมอร์|มิจฉาชีพคืออะไร|scam คืออะไร)", text):
                return "ความหมายของ scam / scammer"
            if re.search(r"(คอลเซ็นเตอร์|call center|โทรศัพท์|เบอร์โทร)", text):
                return "แก๊งคอลเซ็นเตอร์ / โทรศัพท์หลอกลวง"
            if re.search(r"(sms|ข้อความ|ลิงก์|url|ฟิชชิง|phishing)", text):
                return "ข้อความ / SMS / ลิงก์หลอกลวง"
            if re.search(r"(ลงทุน|กำไร|ผลตอบแทน|รวยเร็ว)", text):
                return "หลอกลงทุน / ผลตอบแทนเกินจริง"
            if re.search(r"(otp|รหัสผ่าน|ข้อมูลส่วนตัว|เลขบัญชี)", text):
                return "การขอข้อมูลส่วนตัว / OTP / บัญชี"
            if re.search(r"(เจ้าหน้าที่|ปลอมเป็นเจ้าหน้าที่|แอบอ้างหน่วยงาน|ตำรวจปลอม|ธนาคารปลอม)", text):
                return "การแอบอ้างเป็นเจ้าหน้าที่ / หน่วยงาน"
            return "ความรู้ทั่วไปเกี่ยวกับ scam"

        if re.search(r"(http|www\.|bit\.ly|tinyurl|ลิงก์|link|คลิก)", text):
            return "ตรวจข้อความที่มีลิงก์"
        if re.search(r"(otp|pin|รหัสผ่าน|เลขบัญชี|ข้อมูลส่วนตัว)", text):
            return "ตรวจข้อความขอข้อมูลส่วนตัว"
        if re.search(r"(ตำรวจ|ธนาคาร|ศาล|รัฐบาล|เจ้าหน้าที่|ขนส่ง)", text):
            return "ตรวจข้อความแอบอ้างหน่วยงาน"
        if re.search(r"(เงินฟรี|เครดิตฟรี|โบนัส|รับรางวัล|ยินดีด้วย)", text):
            return "ตรวจข้อความล่อรางวัล / โปรโมชั่น"
        if re.search(r"(ลงทุน|กำไร|ผลตอบแทน|เทรด|รวยเร็ว)", text):
            return "ตรวจข้อความชวนลงทุน"
        return "ตรวจข้อความต้องสงสัยทั่วไป"

    def build_memory_context_text(self, session_id: str) -> str:
        bundle = self.memory.get_context_bundle(session_id)
        state = bundle["state"]
        prefs = bundle["preferences"]
        history_text = bundle["history_text"]

        return f"""
บริบทการสนทนาก่อนหน้า:
- หัวข้อล่าสุด: {state.get("last_topic", "") or "-"}
- ผลล่าสุด: {state.get("last_result", "") or "-"}
- สรุปย่อ: {state.get("summary", "") or "-"}
- โหมดหลักของผู้ใช้: {prefs.get("default_mode", "detect")}
- ประวัติย่อ:
{history_text}
""".strip()

    def refresh_memory_summary(self, session_id: str) -> None:
        summary = self.memory.build_lightweight_summary(session_id)
        self.memory.update_state(session_id, summary=summary)

    def build_compact_detect_payload(self, result: dict) -> dict:
        return {
            "final_label": result.get("final_label", ""),
            "final_color": result.get("final_color", ""),
            "reply": result.get("reply", ""),
            "reasons": result.get("reasons", []),
            "indicators": result.get("indicators", []),
            "advice": result.get("advice", []),
            "link_signals": result.get("link_signals", []),
            "link_check": result.get("link_check", {}),
        }

    # =========================
    # DETECT MODE
    # =========================
    @staticmethod
    def decide_final_label(
        model_is_scam: bool,
        structured: dict,
        extra: dict,
        link_signals: list[str]
    ):
        reasons = []

        has_url = structured["has_url"]
        has_urgency = structured["has_urgency"]
        has_money = structured["has_money"]
        has_personal = structured["has_personal_info_request"]

        if model_is_scam:
            reasons.append("โมเดลฝั่ง Structured Data มองว่าข้อความนี้เข้าข่าย scam")
            return "⚠️ พบจุดน่าสงสัย", "SUSPICIOUS", reasons

        if has_url and extra["has_gambling"]:
            reasons.append("พบลิงก์ร่วมกับคำเกี่ยวกับพนันหรือเครดิตฟรี")
            return "⚠️ พบจุดน่าสงสัย", "SUSPICIOUS", reasons

        if has_url and extra["has_investment_hype"]:
            reasons.append("พบลิงก์ร่วมกับคำชวนลงทุนหรือผลตอบแทนเกินจริง")
            return "⚠️ พบจุดน่าสงสัย", "SUSPICIOUS", reasons

        if has_url and extra["has_prize_bait"]:
            reasons.append("พบลิงก์ร่วมกับข้อความล่อรางวัลหรือของฟรี")
            return "⚠️ พบจุดน่าสงสัย", "SUSPICIOUS", reasons

        if has_personal and (has_url or extra["has_impersonation"]):
            reasons.append("มีการกล่าวถึงข้อมูลส่วนตัวร่วมกับลิงก์หรือการแอบอ้าง")
            return "⚠️ พบจุดน่าสงสัย", "SUSPICIOUS", reasons

        if len(link_signals) >= 4:
            reasons.append("ลิงก์มีหลายสัญญาณผิดสังเกตร่วมกัน")
            return "⚠️ พบจุดน่าสงสัย", "SUSPICIOUS", reasons

        if extra["has_impersonation"] and (has_url or has_urgency):
            reasons.append("มีลักษณะคล้ายแอบอ้างหน่วยงานร่วมกับการกดดันให้ดำเนินการ")
            return "⚠️ พบจุดน่าสงสัย", "SUSPICIOUS", reasons

        if has_url:
            reasons.append("พบลิงก์ในข้อความ ควรตรวจสอบปลายทางก่อนคลิก")
            return "🟡 ควรตรวจสอบเพิ่มเติม", "REVIEW", reasons

        if has_urgency and has_money:
            reasons.append("มีคำเร่งด่วนร่วมกับบริบทด้านการเงิน")
            return "🟡 ควรตรวจสอบเพิ่มเติม", "REVIEW", reasons

        if extra["has_clickbait"] and (
            has_money or extra["has_prize_bait"] or extra["has_investment_hype"]
        ):
            reasons.append("มีคำชักชวนร่วมกับข้อความผลประโยชน์")
            return "🟡 ควรตรวจสอบเพิ่มเติม", "REVIEW", reasons

        if has_personal:
            reasons.append("มีการกล่าวถึงข้อมูลส่วนตัวหรือข้อมูลลับ")
            return "🟡 ควรตรวจสอบเพิ่มเติม", "REVIEW", reasons

        if has_money:
            reasons.append("มีบริบทเรื่องเงินหรือผลประโยชน์ ควรอ่านอย่างระวัง")
            return "🟡 ควรตรวจสอบเพิ่มเติม", "REVIEW", reasons

        reasons.append("ยังไม่พบ pattern ที่น่าสงสัยอย่างชัดเจนจากข้อความนี้")
        return "✅ ไม่พบจุดน่าสงสัยที่ชัดเจน", "CLEAR", reasons

    @staticmethod
    def build_advice(status: str, extra: dict):
        if status == "SUSPICIOUS":
            advice = [
                "อย่าคลิกลิงก์หรือกดปุ่มใด ๆ ในข้อความนี้",
                "อย่าให้ข้อมูลส่วนตัว รหัส OTP หรือเลขบัญชีแก่ผู้ส่ง",
                "อย่าโอนเงิน ฝากเงิน หรือสมัครผ่านลิงก์ในข้อความ",
                "ตรวจสอบกับหน่วยงานหรือผู้ส่งผ่านช่องทางทางการเท่านั้น",
            ]
            if extra.get("has_gambling"):
                advice.append("ข้อความแนวพนันหรือเครดิตฟรีมักใช้ลิงก์ล่อคลิก ควรหลีกเลี่ยง")
            if extra.get("has_investment_hype"):
                advice.append("ข้อความแนวลงทุนกำไรสูงควรตรวจสอบอย่างมากก่อนเชื่อ")
            return advice

        if status == "REVIEW":
            return [
                "ตรวจสอบว่าผู้ส่งเป็นคนที่รู้จักจริงหรือไม่",
                "ยืนยันข้อมูลผ่านช่องทางอื่น เช่น โทรศัพท์หรือช่องทางทางการ",
                "อย่ากดลิงก์จากแหล่งที่ไม่แน่ใจ",
                "หากจำเป็น ให้คัดลอก URL ไปตรวจสอบก่อนเปิด",
            ]

        return [
            "ตอนนี้ยังไม่พบจุดน่าสงสัยที่ชัดเจนจากข้อความนี้",
            "อย่างไรก็ตาม หากไม่มั่นใจควรตรวจสอบกับผู้ส่งโดยตรง",
        ]

    @staticmethod
    def build_link_checker_indicators(link_report: dict) -> list[str]:
        indicators = []
        for item in link_report.get("results", []):
            if item.get("status") == "unsafe":
                threats = ", ".join(item.get("threat_types", [])) or "UNSAFE"
                indicators.append(f"🛡️ Link Checker พบว่า URL ไม่ปลอดภัย ({threats})")
        return indicators

    @staticmethod
    def build_link_checker_reasons(link_report: dict) -> list[str]:
        reasons = []
        for item in link_report.get("results", []):
            if item.get("status") == "unsafe":
                threats = ", ".join(item.get("threat_types", [])) or "UNSAFE"
                reasons.append(f"Link Checker ตรวจพบว่า URL เข้าข่ายไม่ปลอดภัย ({threats})")
        return reasons

    def build_basic_reply(self, label: str, indicators: list[str], reasons: list[str]) -> str:
        if label == "⚠️ พบจุดน่าสงสัย":
            head = "ข้อความนี้มีจุดน่าสงสัยค่อนข้างชัดเจนครับ"
        elif label == "🟡 ควรตรวจสอบเพิ่มเติม":
            head = "ข้อความนี้ยังไม่ชัดพอจะสรุปเด็ดขาด แต่มีบางจุดที่ควรตรวจสอบเพิ่มเติมครับ"
        else:
            head = "ตอนนี้ยังไม่พบจุดน่าสงสัยที่ชัดเจนจากข้อความนี้ครับ"

        parts = [head]

        if reasons:
            parts.append("เหตุผลหลักคือ " + " / ".join(reasons))

        if indicators:
            parts.append("จุดที่ระบบพบ ได้แก่ " + ", ".join(indicators[:4]))

        return " ".join(parts)

    def build_llm_detect_reply(
        self,
        text: str,
        label: str,
        indicators: list[str],
        reasons: list[str],
        session_id: str = "anonymous",
    ) -> str:
        if not self.ollama.is_available():
            return self.build_basic_reply(label, indicators, reasons)

        memory_context = self.build_memory_context_text(session_id)

        prompt = f"""
คุณคือผู้ช่วยตรวจข้อความต้องสงสัยชื่อ ScamGuard AI

หน้าที่:
- อธิบายผลการตรวจให้ผู้ใช้เข้าใจง่าย
- อย่าฟันธงเกินจริง
- ใช้ภาษาไทยสุภาพ กระชับ ชัดเจน
- อย่าพูดเกินข้อมูลที่มี
- ห้ามแนะนำการหลอกลวงหรือการกระทำผิดกฎหมาย

กฎการใช้ภาษา:
- ห้ามขึ้นต้นคำตอบด้วยคำว่า "ขออภัย" ถ้ายังสามารถตอบคำถามได้ตามข้อมูลที่มี
- ใช้คำว่า "ขออภัย" ได้เฉพาะกรณีที่ตอบไม่ได้จริง ข้อมูลไม่พอ หรืออยู่นอกขอบเขตเท่านั้น
- ถ้าตอบได้ ให้ตอบเข้าประเด็นทันทีโดยไม่ต้องเกริ่นขอโทษ
- โทนคำตอบต้องเป็นมืออาชีพ เป็นธรรมชาติ ไม่เวิ่นเว้อ

{memory_context}

ข้อความผู้ใช้:
{text}

ผลการตรวจ:
{label}

เหตุผล:
{", ".join(reasons) if reasons else "-"}

Indicators ที่พบ:
{", ".join(indicators) if indicators else "-"}

แนวทางเขียนคำตอบ:
- ตอบ 2-4 ประโยค
- ถ้ามีบริบทก่อนหน้า ให้เชื่อมโยงได้แบบธรรมชาติ แต่ห้ามอ้างเกินข้อมูล
- ถ้าข้อความนี้คล้ายรูปแบบที่คุยก่อนหน้า ให้บอกได้สั้น ๆ ว่าคล้ายกัน

คำตอบ:
""".strip()

        try:
            response = self.ollama.generate(prompt)
            return response if response else self.build_basic_reply(label, indicators, reasons)
        except Exception:
            return self.build_basic_reply(label, indicators, reasons)

    def analyze_message(self, text: str, session_id: str = "anonymous") -> dict:
        text = str(text).strip()
        if not text:
            return {"ok": False, "message": "กรุณาพิมพ์ข้อความก่อนส่งตรวจสอบ"}

        model_result = self.classifier.predict(text)
        structured = model_result.structured_features
        extra = detect_extra_patterns(text)
        link_signals = analyze_link_suspicion(text)
        link_report = self.link_checker.check_text(text)

        final_label, final_color, reasons = self.decide_final_label(
            model_result.is_scam,
            structured,
            extra,
            link_signals,
        )

        if link_report.get("available") and link_report.get("summary", {}).get("unsafe_count", 0) > 0:
            final_label = "⚠️ พบจุดน่าสงสัย"
            final_color = "SUSPICIOUS"
            reasons = self.build_link_checker_reasons(link_report) + reasons

        indicators = build_indicator_labels(structured, extra)
        indicators += self.build_link_checker_indicators(link_report)

        indicators = list(dict.fromkeys(indicators))
        reasons = list(dict.fromkeys(reasons))

        advice = self.build_advice(final_color, extra)

        if link_report.get("summary", {}).get("unsafe_count", 0) > 0:
            advice = [
                "Link Checker พบว่า URL นี้เข้าข่ายไม่ปลอดภัย ควรหลีกเลี่ยงการคลิกทันที",
                "อย่าให้ข้อมูลส่วนตัว รหัส OTP หรือข้อมูลทางการเงินบนลิงก์นี้",
            ] + advice

        reply = self.build_llm_detect_reply(
            text=text,
            label=final_label,
            indicators=indicators,
            reasons=reasons,
            session_id=session_id,
        )

        result = {
            "ok": True,
            "mode": "detect",
            "input_text": text,
            "final_label": final_label,
            "final_color": final_color,
            "reply": reply,
            "reasons": reasons,
            "indicators": indicators,
            "link_signals": link_signals,
            "advice": advice,
            "link_check": link_report,
            "model": {
                "raw_prediction": str(model_result.raw_prediction),
                "is_scam": model_result.is_scam,
            },
            "structured_features": structured,
            "extra_patterns": extra,
            "show_next_step_actions": final_color in {"SUSPICIOUS", "REVIEW"},
            "next_step_situations": [
                {"key": "not_clicked", "label": "ยังไม่ได้กดลิงก์"},
                {"key": "clicked_link", "label": "กดลิงก์ไปแล้ว"},
                {"key": "shared_info", "label": "ให้ข้อมูลไปแล้ว"},
                {"key": "sent_money", "label": "โอนเงินไปแล้ว"},
            ] if final_color in {"SUSPICIOUS", "REVIEW"} else [],
        }

        topic = self.infer_topic(text, mode="detect")
        self.memory.update_state(
            session_id,
            last_topic=topic,
            last_mode="detect",
            last_result=final_label,
            detect_payload=self.build_compact_detect_payload(result),
        )
        self.refresh_memory_summary(session_id)

        return result

    # =========================
    # KNOWLEDGE MODE
    # =========================
    def ask_knowledge(self, question: str, session_id: str = "anonymous") -> dict:
        question = str(question).strip()
        if not question:
            return {"ok": False, "message": "กรุณาพิมพ์คำถามก่อน"}

        try:
            retrieved = self.rag_store.retrieve_context(question, k=4, fetch_k=8)
            context_text = retrieved["context_text"][:1600]
            sources = retrieved["sources"]

            if not context_text.strip():
                answer = "ตอนนี้ยังไม่พบข้อมูลที่เกี่ยวข้องเพียงพอในฐานความรู้ครับ"
                self.memory.update_state(
                    session_id,
                    last_topic=self.infer_topic(question, mode="knowledge"),
                    last_mode="knowledge",
                    last_result="ไม่พบข้อมูลเพียงพอในฐานความรู้",
                )
                self.refresh_memory_summary(session_id)

                return {
                    "ok": True,
                    "mode": "knowledge",
                    "question": question,
                    "answer": answer,
                    "sources": [],
                }

            if not self.ollama.is_available():
                answer = "ผมพบข้อมูลที่เกี่ยวข้องจากฐานความรู้แล้วครับ\n\n" + context_text
                self.memory.update_state(
                    session_id,
                    last_topic=self.infer_topic(question, mode="knowledge"),
                    last_mode="knowledge",
                    last_result="ตอบจากฐานความรู้โดยตรง",
                )
                self.refresh_memory_summary(session_id)

                return {
                    "ok": True,
                    "mode": "knowledge",
                    "question": question,
                    "answer": answer,
                    "sources": sources,
                }

            memory_context = self.build_memory_context_text(session_id)
            prompt = f"""คุณคือผู้ช่วย AI ของระบบ ScamGuard AI ที่ช่วยตอบคำถามเกี่ยวกับการตรวจสอบและความรู้เกี่ยวกับ Scam โดยอ้างอิงจากข้อมูลในฐานความรู้ที่มีอยู่เท่านั้น
[ขั้นตอนการทำงานและกฎข้อบังคับ]
1. วิเคราะห์เจตนา (Intent Analysis): ประเมินคำถามของผู้ใช้ก่อนว่าเข้าข่ายความเสี่ยง Scam หรือไม่ **(คำเตือน: การชวนลงทุน, อ้างว่ารวยเร็ว, ให้เงินฟรี, ลิงก์แปลกปลอม หรือแชทน่าสงสัย ถือว่า "เกี่ยวข้องกับ Scam" ทั้งสิ้น)**
2. หากคำถามเกี่ยวข้องกับ Scam: ให้ตอบโดยวิเคราะห์จากข้อมูลใน Context เท่านั้น **ห้ามพิมพ์ประโยคปฏิเสธ (เช่น "ขออภัย ฉันสามารถให้ข้อมูล...") นำหน้าคำตอบเด็ดขาด** ให้ตอบเข้าประเด็นได้เลย
3. หากคำถาม "ไม่เกี่ยวข้อง" กับ Scam เลย ให้ตอบว่า "ขออภัย ฉันสามารถให้ข้อมูลที่เกี่ยวข้องกับการตรวจสอบและความรู้เกี่ยวกับ Scam เท่านั้นครับ" และ **หยุดทำงานทันที** ห้ามอธิบายอะไรต่อ
4. กรณีข้อมูลไม่เพียงพอ: หากเป็นเรื่อง Scam แต่ใน Context ไม่มีข้อมูลตอบได้ ให้ตอบแค่ว่า "ขออภัย ยังไม่พบข้อมูลที่เกี่ยวข้องเพียงพอในฐานความรู้ครับ" และหยุดตอบทันที
5. ข้อห้ามเด็ดขาด (Safety): ห้ามให้คำแนะนำที่ส่งเสริม สอน หรือสนับสนุนการหลอกลวง ขโมยเงิน ฟิชชิง หรือการกระทำผิดกฎหมายทุกกรณี
6. คำถามเชิงนิยาม เช่น "คืออะไร", "หมายถึงอะไร", "อธิบาย", "ป้องกันยังไง" ถือว่าเป็นคำถามที่ตอบได้ หากเกี่ยวข้องกับ scam และมีข้อมูลใน Context แต่ถ้าคำถามเชิงขอความช่วยเหลือ เช่น "ทำยังไงดี", "ควรทำยังไง", "ช่วยบอกหน่อย" ให้ตอบได้ถ้ามีข้อมูลใน Context แต่ถ้าไม่มีข้อมูลใน Context ให้ตอบแค่ว่า "ขออภัย ยังไม่พบข้อมูลที่เกี่ยวข้องเพียงพอในฐานความรู้ครับ" และหยุดตอบทันที

[น้ำเสียงและรูปแบบการตอบ]
- ลักษณะการตอบต้องเป็นมืออาชีพ สุภาพ และเป็นธรรมชาติ ไม่ใช่โทนทางการหรือหุ่นยนต์จนเกินไปให้ตอบฟิลเพื่อน
- ถามแค่ไหน ตอบแค่นั้นและถ้าถามเชิงขอความช่วยเหลือ ให้คำตอบที่เป็นประโยชน์และให้กำลังใจ 
- ใช้ภาษาไทยที่เข้าใจง่าย ชัดเจน สุภาพ และเป็นธรรมชาติเหมือนคนทั่วไป
- ตอบให้กระชับ ตรงประเด็น ไม่เยิ่นเย้อ
- ถ้าผู้ใช้ถามต่อจากเรื่องเดิม ให้เชื่อมบริบทจาก memory ได้ แต่ห้ามเดาเกิน Context

{memory_context}

คำถาม:
{question}

ข้อมูลอ้างอิง:
{context_text}

คำตอบ:
""".strip()

            try:
                answer = self.ollama.generate(prompt)
                if not answer:
                    answer = "ขออภัย ยังไม่พบข้อมูลที่เกี่ยวข้องเพียงพอในฐานความรู้ครับ"
            except Exception:
                answer = "ขออภัย ยังไม่พบข้อมูลที่เกี่ยวข้องเพียงพอในฐานความรู้ครับ"

            self.memory.update_state(
                session_id,
                last_topic=self.infer_topic(question, mode="knowledge"),
                last_mode="knowledge",
                last_result="ตอบด้วย knowledge mode",
            )
            self.refresh_memory_summary(session_id)

            return {
                "ok": True,
                "mode": "knowledge",
                "question": question,
                "answer": answer,
                "sources": sources,
            }

        except Exception as e:
            return {
                "ok": False,
                "message": f"เกิดข้อผิดพลาดในโหมดถามความรู้: {str(e)}"
            }

    # =========================
    # NEXT STEP GUIDANCE
    # =========================
    def build_next_step_guidance(self, situation: str, detect_payload: dict) -> dict:
        final_color = str(detect_payload.get("final_color", ""))
        indicators = [str(x) for x in detect_payload.get("indicators", [])]
        reasons = [str(x) for x in detect_payload.get("reasons", [])]
        unsafe_count = int(detect_payload.get("link_unsafe_count", 0))

        has_link = any("ลิงก์" in x or "URL" in x for x in indicators)
        has_personal = any("ข้อมูลส่วนตัว" in x for x in indicators)
        has_money = any("เงิน" in x or "รางวัล" in x or "โปรโมชั่น" in x for x in indicators)
        has_impersonation = any("แอบอ้างหน่วยงาน" in x for x in indicators)

        base = {
            "ok": True,
            "mode": "detect_next_step",
            "situation": situation,
            "situation_label": self.SITUATION_LABELS.get(situation, situation),
            "based_on_label": detect_payload.get("final_label", ""),
            "priority": "medium",
            "title": "",
            "warning": "",
            "steps": [],
            "notes": [],
        }

        if situation == "not_clicked":
            base["title"] = "คำแนะนำเมื่อยังไม่ได้กดลิงก์"
            base["priority"] = "medium" if final_color == "REVIEW" else "high"
            base["warning"] = "ตอนนี้ยังมีโอกาสหยุดความเสียหายได้มากที่สุด ถ้ายังไม่ได้คลิกหรือยังไม่ได้ตอบกลับ"

            steps = [
                "อย่าคลิกลิงก์ อย่ากดปุ่ม และอย่าตอบกลับข้อความนี้",
                "อย่าให้ข้อมูลส่วนตัว รหัส OTP รหัสผ่าน หรือเลขบัญชีเพิ่มเติม",
                "ตรวจสอบกับหน่วยงานหรือผู้ส่งผ่านช่องทางทางการเท่านั้น",
                "เก็บข้อความ ลิงก์ หรือภาพหน้าจอไว้เป็นหลักฐานเผื่อจำเป็นต้องใช้",
            ]

            if has_impersonation:
                steps.append("หากมีการอ้างว่าเป็นธนาคาร ตำรวจ หรือหน่วยงานรัฐ ให้ติดต่อกลับด้วยเบอร์ทางการด้วยตัวเอง")
            if has_money:
                steps.append("หากมีการเร่งให้โอนเงินหรือรับรางวัล ให้ตั้งข้อสงสัยไว้ก่อนและอย่าตัดสินใจภายใต้ความกดดัน")

            base["steps"] = steps

        elif situation == "clicked_link":
            base["title"] = "คำแนะนำเมื่อกดลิงก์ไปแล้ว"
            base["priority"] = "high"
            base["warning"] = "หากเพิ่งกดลิงก์ ให้รีบหยุดใช้งานหน้านั้นทันที โดยเฉพาะถ้ามีการขอให้ล็อกอินหรือดาวน์โหลดไฟล์"

            steps = [
                "ปิดหน้าเว็บหรือแอปนั้นทันที และอย่ากรอกข้อมูลเพิ่ม",
                "หากมีการล็อกอินไปแล้ว ให้เปลี่ยนรหัสผ่านของบัญชีนั้นทันที",
                "ตรวจสอบธุรกรรม การแจ้งเตือน และกิจกรรมผิดปกติของบัญชีที่เกี่ยวข้อง",
                "หลีกเลี่ยงการติดตั้งแอปหรือไฟล์ใด ๆ ที่ลิงก์นั้นชวนให้ดาวน์โหลด",
            ]

            if unsafe_count > 0 or has_link:
                steps.append("ถ้าลิงก์นั้นเปิดไปยังหน้าแปลก ๆ หรือมีการดาวน์โหลดอัตโนมัติ ควรสแกนเครื่องหรือให้ผู้เชี่ยวชาญช่วยตรวจสอบอุปกรณ์")
            if has_personal:
                steps.append("หากหน้าเว็บมีการขอข้อมูลส่วนตัว ให้ถือว่าเสี่ยงสูงและรีบเปลี่ยนรหัสผ่านบัญชีสำคัญที่เกี่ยวข้อง")

            base["steps"] = steps

        elif situation == "shared_info":
            base["title"] = "คำแนะนำเมื่อให้ข้อมูลไปแล้ว"
            base["priority"] = "high"
            base["warning"] = "หากให้ข้อมูลสำคัญไปแล้ว เช่น OTP รหัสผ่าน เลขบัญชี หรือข้อมูลยืนยันตัวตน ควรรีบดำเนินการทันที"

            steps = [
                "เปลี่ยนรหัสผ่านของบัญชีที่เกี่ยวข้องทันที โดยเฉพาะอีเมล ธนาคาร และโซเชียลมีเดีย",
                "หากให้ข้อมูลธนาคารหรือ OTP ไปแล้ว ให้รีบติดต่อธนาคารเพื่อขอคำแนะนำหรืออายัดความเสี่ยง",
                "ตรวจสอบธุรกรรมย้อนหลังและเปิดการแจ้งเตือนความเคลื่อนไหวของบัญชี",
                "ระวังการถูกหลอกซ้ำจากบุคคลเดิมหรือผู้ที่ติดต่อมาอ้างว่าจะช่วยแก้ปัญหา",
            ]

            if has_impersonation:
                steps.append("หากอีกฝ่ายอ้างว่าเป็นหน่วยงานรัฐหรือธนาคาร ให้ติดต่อหน่วยงานนั้นผ่านช่องทางทางการด้วยตัวเอง")
            if has_personal:
                steps.append("ถ้าให้ข้อมูลยืนยันตัวตน เช่น เลขบัตรประชาชนหรือข้อมูลส่วนตัว ควรเฝ้าระวังการสวมรอยหรือการนำข้อมูลไปใช้ต่อ")

            base["steps"] = steps

        elif situation == "sent_money":
            base["title"] = "คำแนะนำเมื่อโอนเงินไปแล้ว"
            base["priority"] = "critical"
            base["warning"] = "กรณีโอนเงินไปแล้ว ความเร็วสำคัญมาก ควรรีบติดต่อธนาคารและรวบรวมหลักฐานทันที"

            steps = [
                "รีบติดต่อธนาคารหรือผู้ให้บริการทางการเงินทันที เพื่อแจ้งเหตุและสอบถามการอายัดหรือระงับธุรกรรม",
                "รวบรวมหลักฐานทั้งหมด เช่น สลิปโอนเงิน ข้อความสนทนา ลิงก์ และเบอร์ที่ใช้ติดต่อ",
                "หยุดโอนเงินเพิ่มทุกกรณี แม้อีกฝ่ายจะอ้างว่าจะได้เงินคืนหรือให้โอนเพื่อปลดล็อกยอด",
                "แจ้งความหรือแจ้งหน่วยงานที่เกี่ยวข้องโดยเร็ว พร้อมนำหลักฐานทั้งหมดไปด้วย",
            ]

            if has_money:
                steps.append("ถ้าอีกฝ่ายอ้างเรื่องรางวัล การลงทุน หรือโปรโมชัน ให้ระวังการถูกหลอกให้โอนซ้ำ")
            if has_impersonation:
                steps.append("ถ้ามีการแอบอ้างเป็นธนาคารหรือตำรวจ ให้แจ้งข้อเท็จจริงกับหน่วยงานจริงผ่านช่องทางทางการ")

            base["steps"] = steps
            base["notes"] = [
                "อย่าเชื่อผู้ที่ติดต่อกลับมาอ้างว่าช่วยกู้เงินคืนได้ทันทีโดยให้โอนเงินเพิ่ม",
                "เก็บหลักฐานทุกอย่างไว้เป็นลำดับเวลา จะช่วยตอนแจ้งเหตุได้มาก",
            ]

        else:
            return {
                "ok": False,
                "message": "ไม่พบสถานการณ์ที่เลือก"
            }

        if final_color == "SUSPICIOUS":
            base["notes"].append("ผลตรวจล่าสุดของระบบอยู่ในระดับน่าสงสัยค่อนข้างสูง ควรดำเนินการอย่างระมัดระวังทันที")
        elif final_color == "REVIEW":
            base["notes"].append("ผลตรวจล่าสุดอยู่ในระดับควรตรวจสอบเพิ่มเติม แม้ยังไม่ฟันธง แต่ควรระวังไว้ก่อน")

        if reasons:
            base["notes"].append("สาเหตุหลักที่ระบบกังวล: " + " / ".join(reasons[:2]))

        return base

    def handle_next_step(self, session_id: str, situation: str) -> dict:
        session_id = str(session_id).strip() or "anonymous"
        situation = str(situation).strip()

        if situation not in self.SITUATION_LABELS:
            return {
                "ok": False,
                "message": "สถานการณ์ไม่ถูกต้อง"
            }

        detect_payload = self.memory.get_last_detect_payload(session_id)
        if not detect_payload:
            return {
                "ok": False,
                "message": "ยังไม่พบผลการตรวจข้อความล่าสุดของ session นี้ กรุณาตรวจข้อความก่อน"
            }

        result = self.build_next_step_guidance(situation, detect_payload)

        if result.get("ok"):
            self.memory.add_message(
                session_id,
                role="assistant",
                content=f"คำแนะนำต่อสถานการณ์: {self.SITUATION_LABELS[situation]}",
                mode="detect",
            )
            self.memory.update_state(
                session_id,
                last_topic=f"คำแนะนำต่อสถานการณ์: {self.SITUATION_LABELS[situation]}",
                last_mode="detect",
                last_result=result.get("title", "คำแนะนำถัดไป"),
            )
            self.refresh_memory_summary(session_id)

        return result

    # =========================
    # MAIN ROUTER
    # =========================
    def handle_chat(self, text: str, mode: str = "detect", session_id: str = "anonymous") -> dict:
        text = str(text).strip()
        mode = str(mode).strip().lower()
        session_id = str(session_id).strip() or "anonymous"

        self.memory.ensure_session(session_id)
        self.memory.update_preferences(session_id, default_mode=mode)
        self.memory.add_message(session_id, role="user", content=text, mode=mode)

        if self.is_harmful_request(text, mode=mode):
            refusal = self.get_safe_refusal()

            if mode == "knowledge":
                self.memory.add_message(session_id, role="assistant", content=refusal, mode=mode)
                self.memory.update_state(
                    session_id,
                    last_topic="คำขออันตราย / ปฏิเสธการตอบ",
                    last_mode=mode,
                    last_result="blocked",
                )
                self.refresh_memory_summary(session_id)

                return {
                    "ok": True,
                    "mode": "knowledge",
                    "question": text,
                    "answer": refusal,
                    "sources": [],
                }

            self.memory.add_message(session_id, role="assistant", content=refusal, mode=mode)
            self.memory.update_state(
                session_id,
                last_topic="คำขออันตราย / ปฏิเสธการตอบ",
                last_mode=mode,
                last_result="blocked",
            )
            self.refresh_memory_summary(session_id)

            return {
                "ok": True,
                "mode": "detect",
                "input_text": text,
                "final_label": "🟡 ควรตรวจสอบเพิ่มเติม",
                "final_color": "REVIEW",
                "reply": refusal,
                "reasons": [
                    "ระบบปฏิเสธคำขอที่มีลักษณะอาจนำไปใช้หลอกลวงหรือทำอันตรายผู้อื่น"
                ],
                "indicators": [],
                "link_signals": [],
                "advice": [
                    "ผมช่วยอธิบายสัญญาณเตือน วิธีป้องกัน และแนวทางรับมืออย่างปลอดภัยได้"
                ],
                "model": {
                    "raw_prediction": "blocked",
                    "is_scam": False,
                },
                "structured_features": {},
                "extra_patterns": {},
                "show_next_step_actions": False,
                "next_step_situations": [],
            }

        if mode == "knowledge":
            result = self.ask_knowledge(text, session_id=session_id)
            if result.get("ok"):
                self.memory.add_message(
                    session_id,
                    role="assistant",
                    content=result.get("answer", ""),
                    mode=mode,
                )
                self.refresh_memory_summary(session_id)
            return result

        result = self.analyze_message(text, session_id=session_id)
        if result.get("ok"):
            self.memory.add_message(
                session_id,
                role="assistant",
                content=result.get("reply", ""),
                mode=mode,
            )
            self.refresh_memory_summary(session_id)
        return result