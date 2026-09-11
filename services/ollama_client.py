import os
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL


class OllamaClient:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)
        self.model = GROQ_MODEL

    def is_available(self) -> bool:
        try:
            return bool(GROQ_API_KEY)
        except Exception:
            return False

    def generate(self, prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"ขออภัยครับ เกิดข้อผิดพลาด: {str(e)}"

# import requests
# from config import OLLAMA_BASE_URL, OLLAMA_MODEL


# class OllamaClient:
#     def __init__(self, base_url: str = OLLAMA_BASE_URL, model: str = OLLAMA_MODEL):
#         self.base_url = base_url.rstrip("/")
#         self.model = model

#     def is_available(self) -> bool:
#         try:
#             res = requests.get(f"{self.base_url}/api/tags", timeout=3)
#             return res.status_code == 200
#         except Exception:
#             return False

#     def generate(self, prompt: str) -> str:
#         payload = {
#             "model": self.model,
#             "prompt": prompt,
#             "stream": False,
#             "keep_alive": "10m",
#             "options": {
#                 "num_predict": 150,
#                 "temperature": 0.3,
#                 "num_ctx": 1024,
#             }
#         }

#         res = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=60)
#         res.raise_for_status()
#         data = res.json()
#         return data.get("response", "").strip()