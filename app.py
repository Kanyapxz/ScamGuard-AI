from flask import Flask, jsonify, render_template, request
from config import HOST, PORT, DEBUG
from llm.reasoning import ScamReasoner
from services.ocr_service import ocr_extract_from_upload, get_ocr_limits, OCRError

app = Flask(__name__)
reasoner = ScamReasoner()

# จำกัดขนาด request ทั้งก้อนที่ 6 MB (ให้เผื่อ overhead จาก 5MB limit ของรูป)
app.config["MAX_CONTENT_LENGTH"] = 6 * 1024 * 1024


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "message": "ScamGuard AI backend is running"})


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}

    message = str(data.get("message", "")).strip()
    mode = str(data.get("mode", "detect")).strip().lower()
    session_id = str(data.get("session_id", "")).strip() or "anonymous"

    if not message:
        return jsonify({
            "ok": False,
            "message": "กรุณาส่งข้อความหรือคำถาม"
        }), 400

    if mode not in {"detect", "knowledge"}:
        mode = "detect"

    try:
        result = reasoner.handle_chat(
            text=message,
            mode=mode,
            session_id=session_id,
        )
        return jsonify(result)

    except Exception as e:
        return jsonify({
            "ok": False,
            "message": f"เกิดข้อผิดพลาดในการประมวลผล: {str(e)}"
        }), 500


@app.route("/api/next-step", methods=["POST"])
def api_next_step():
    data = request.get_json(silent=True) or {}

    session_id = str(data.get("session_id", "")).strip() or "anonymous"
    situation = str(data.get("situation", "")).strip()

    if not situation:
        return jsonify({
            "ok": False,
            "message": "กรุณาเลือกสถานการณ์"
        }), 400

    try:
        result = reasoner.handle_next_step(
            session_id=session_id,
            situation=situation
        )
        status = 200 if result.get("ok") else 400
        return jsonify(result), status

    except Exception as e:
        return jsonify({
            "ok": False,
            "message": f"เกิดข้อผิดพลาดในการประมวลผลสถานการณ์ถัดไป: {str(e)}"
        }), 500


# ═════════════════════════════════════════════════════════════════
# OCR — แนบรูปภาพในโหมดตรวจสอบข้อความ
#
# Flow:
#   Frontend ส่ง multipart/form-data { image: <file> }
#   Backend อ่านด้วย EasyOCR (lazy load) คืน text ออกมา
#   Frontend เอา text ไปเติมใน textarea ให้ผู้ใช้แก้+ยืนยันก่อนส่งตรวจจริง
# ═════════════════════════════════════════════════════════════════
@app.route("/api/ocr", methods=["POST"])
def api_ocr():
    if "image" not in request.files:
        return jsonify({
            "ok": False,
            "message": "ไม่พบไฟล์รูปในคำขอ (ต้องส่งผ่าน field ชื่อ 'image')"
        }), 400

    file_storage = request.files["image"]

    try:
        text = ocr_extract_from_upload(file_storage)
    except OCRError as e:
        # Validation / OCR logical error — ส่งข้อความผู้ใช้อ่านได้
        return jsonify({"ok": False, "message": str(e)}), 400
    except Exception as e:
        return jsonify({
            "ok": False,
            "message": f"เกิดข้อผิดพลาดในการประมวลผลรูปภาพ: {str(e)}"
        }), 500

    return jsonify({
        "ok": True,
        "text": text,
        "char_count": len(text),
    })


@app.route("/api/ocr/limits", methods=["GET"])
def api_ocr_limits():
    """ให้ frontend รู้ขนาดไฟล์สูงสุดและนามสกุลที่รองรับ"""
    return jsonify({"ok": True, **get_ocr_limits()})


# Flask จะคืน 413 อัตโนมัติถ้าเกิน MAX_CONTENT_LENGTH — ห่อให้เป็น JSON
@app.errorhandler(413)
def _too_large(_e):
    return jsonify({
        "ok": False,
        "message": "ไฟล์ใหญ่เกินไป (จำกัด 5 MB)"
    }), 413


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=DEBUG)