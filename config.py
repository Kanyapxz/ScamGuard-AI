from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# Core paths
MODEL_PATH = BASE_DIR / "model.pkl"
TFIDF_PATH = BASE_DIR / "tfidf.pkl"

# RAG files (ไว้ใช้ต่อภายหลัง)
KNOWLEDGE_PATH = BASE_DIR / "rag" / "knowledge_base.txt"
CHROMA_DIR = BASE_DIR / "rag" / "chroma_db"

# Flask
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", 5000))
DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"

# Ollama
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

# Optional external APIs
LINK_API_KEY = os.getenv("LINK_API_KEY", "")
PHONE_API_KEY = os.getenv("PHONE_API_KEY", "")


GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

SAFE_BROWSING_API_KEY = os.getenv("SAFE_BROWSING_API_KEY", "")
LINK_CHECK_TIMEOUT = int(os.getenv("LINK_CHECK_TIMEOUT", 8))

VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY", "")