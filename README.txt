# ScamGuard AI — Web App Setup Guide
# ============================================================

## โครงสร้างโปรเจค

scamguard_app/
├── app.py              ← Flask server (backend)
├── model.pkl           ← Best ML Model (จาก Colab)
├── tfidf.pkl           ← TF-IDF Vectorizer (จาก Colab)
├── requirements.txt    ← Python dependencies
└── templates/
    └── index.html      ← Chat UI (frontend)

## ขั้นตอนติดตั้ง

### 1. วางไฟล์ model.pkl และ tfidf.pkl
ดาวน์โหลดจาก Colab แล้วใส่ใน folder scamguard_app/
(ต้องอยู่ระดับเดียวกับ app.py)

### 2. เปิด VS Code แล้วเปิด Terminal
Terminal → New Terminal

### 3. สร้าง Virtual Environment
python -m venv venv

### 4. Activate
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

### 5. ติดตั้ง dependencies
pip install -r requirements.txt

### 6. รัน App
python app.py

### 7. เปิดเบราว์เซอร์
http://localhost:5000
