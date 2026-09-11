import re


def clean_text(text: str) -> str:
    """
    ทำความสะอาดข้อความให้ใกล้เคียงกับตอน train model
    """
    text = str(text)
    text = re.sub(r"\[(Call|User)\]", "", text)
    text = re.sub(r"https?://\S+|www\.\S+", " URLTOKEN ", text, flags=re.I)
    text = re.sub(r"[()[\]{}<>]", " ", text)
    text = re.sub(r"[^\u0E00-\u0E7Fa-zA-Z0-9\s:/._#%-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def extract_urls(text: str):
    return re.findall(r"(https?://[^\s]+|www\.[^\s]+)", str(text), flags=re.I)