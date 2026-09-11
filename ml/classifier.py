import pickle
from dataclasses import dataclass, asdict
from scipy.sparse import csr_matrix, hstack

from config import MODEL_PATH, TFIDF_PATH
from nlp.preprocess import clean_text
from nlp.feature_extractor import extract_structured_features


@dataclass
class ClassifierResult:
    text: str
    cleaned_text: str
    raw_prediction: object
    is_scam: bool
    structured_features: dict

    def to_dict(self):
        return asdict(self)


class ScamClassifier:
    def __init__(self):
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"ไม่พบไฟล์โมเดล: {MODEL_PATH}")
        if not TFIDF_PATH.exists():
            raise FileNotFoundError(f"ไม่พบไฟล์ TF-IDF: {TFIDF_PATH}")

        with open(MODEL_PATH, "rb") as f:
            self.model = pickle.load(f)

        with open(TFIDF_PATH, "rb") as f:
            self.tfidf = pickle.load(f)

    @staticmethod
    def normalize_prediction(raw_pred) -> bool:
        if isinstance(raw_pred, str):
            return raw_pred.strip().lower() in {"1", "scam", "true", "yes"}

        try:
            return int(raw_pred) == 1
        except Exception:
            return False

    def predict(self, text: str) -> ClassifierResult:
        cleaned = clean_text(text)
        features = extract_structured_features(text) # ใช้ text ดิบในการตรวจจับ pattern เพื่อให้ได้สัญญาณที่ครบถ้วนที่สุด

        x_text = self.tfidf.transform([cleaned]) # ใช้ cleaned text ในการแปลง TF-IDF เพื่อให้ได้ฟีเจอร์ที่สอดคล้องกับตอน train
        x_struct = csr_matrix([[  # ต้องรักษาลำดับให้ตรงกับตอน train:
            features["msg_length"], #ความยาวข้อความ
            features["word_count"], #จำนวนคำในข้อความ
            features["has_url"], #มี URL หรือไม่
            features["has_phone"], #มีหมายเลขโทรศัพท์หรือไม่
            features["has_urgency"],#มีคำที่แสดงถึงความเร่งด่วนหรือไม่
            features["has_money"],#มีคำที่เกี่ยวข้องกับเงินหรือไม่
            features["has_personal_info_request"],#มีคำที่ขอข้อมูลส่วนตัวหรือไม่
        ]])

        x_input = hstack([x_text, x_struct]) # รวมฟีเจอร์ข้อความและฟีเจอร์เชิงโครงสร้างเข้าด้วยกัน
        raw_prediction = self.model.predict(x_input)[0]
        is_scam = self.normalize_prediction(raw_prediction)

        return ClassifierResult(  
            text=text,
            cleaned_text=cleaned,
            raw_prediction=raw_prediction,
            is_scam=is_scam,
            structured_features=features,
        )