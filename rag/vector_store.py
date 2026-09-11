"""
═══════════════════════════════════════════════════════════════════════
 vector_store.py — หัวใจของ RAG (Retrieval-Augmented Generation)
═══════════════════════════════════════════════════════════════════════

ไฟล์นี้ทำหน้าที่ 4 อย่าง:
  1. โหลด chunks.json (139 chunks ที่ผ่าน preprocessing แล้วจาก notebook)
  2. แปลง chunks เป็น LangChain Document (เพิ่ม metadata)
  3. สร้าง/โหลด ChromaDB — vector database ที่ persist บน disk
  4. ค้นหา chunks ที่เกี่ยวข้องกับคำถาม (MMR retrieval)

Pipeline เต็ม:
  chunks.json → Documents → Embeddings → ChromaDB → Retriever → คืน context

ถูกเรียกใช้โดย: llm/reasoning.py → ask_knowledge()
"""

import os
import sys
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────
# ปิด telemetry ของ ChromaDB
# โดย default ChromaDB จะส่ง usage stats ไปยัง cloud
# เราปิดไว้เพื่อ (1) privacy (2) ป้องกัน warning รกใน terminal
# ─────────────────────────────────────────────────────────────────────
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"

# ─────────────────────────────────────────────────────────────────────
# เพิ่ม project root เข้า sys.path
# เพื่อให้ import `from config import ...` ได้จากทุกที่
# (ไฟล์นี้อยู่ใน rag/ แต่ต้องเข้าถึง config.py ที่ root)
# ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
from typing import List, Dict, Any

# ─────────────────────────────────────────────────────────────────────
# LangChain components — จุดเชื่อมต่อกับ RAG ecosystem
#   Document    : คลาสมาตรฐานสำหรับข้อความ 1 ชิ้น + metadata
#   Chroma      : wrapper ของ ChromaDB (vector database)
#   HuggingFaceEmbeddings : ใช้ sentence-transformers ฟรีจาก HuggingFace
# ─────────────────────────────────────────────────────────────────────
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from config import BASE_DIR, CHROMA_DIR


class RAGVectorStore:
    """
    ตัวจัดการ vector store ทั้งหมด — ใช้เป็น singleton ผ่าน ScamReasoner
    (สร้าง 1 instance ต่อ 1 Flask app เพื่อประหยัด RAM)
    """

    def __init__(
        self,
        chunks_path: Path | None = None,
        persist_directory: Path | None = None,
        # ══════════════════════════════════════════════════════════
        #  EMBEDDING MODEL — ตัวแปลงข้อความเป็น vector
        # ══════════════════════════════════════════════════════════
        # "paraphrase-multilingual-MiniLM-L12-v2" มีข้อดี:
        #   ✅ รองรับ 50+ ภาษา รวมไทย (สำคัญที่สุด!)
        #   ✅ ฟรี 100% — ไม่ต้องใช้ OpenAI API key
        #   ✅ เร็ว + เบา (22M parameters)
        #   ✅ ทำงาน offline ได้ ไม่ส่งข้อมูลออก internet
        # Output: vector มิติ 384 ต่อ chunk
        embedding_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        # ══════════════════════════════════════════════════════════
        #  RETRIEVAL PARAMETERS — ควบคุมการค้นหา
        # ══════════════════════════════════════════════════════════
        default_k: int = 4,          # จำนวน chunks ที่ส่งให้ LLM ในที่สุด
        default_fetch_k: int = 8,    # จำนวน candidates ที่ MMR เอามาพิจารณาก่อนคัดเหลือ k
    ):
        # กำหนด path สำคัญ ๆ
        self.rag_dir = BASE_DIR / "rag"                          # rag/
        self.chunks_path = chunks_path or self._resolve_chunks_path()  # rag/chunks.json
        self.persist_directory = persist_directory or CHROMA_DIR       # rag/chroma_db/
        self.embedding_model_name = embedding_model_name
        self.default_k = default_k
        self.default_fetch_k = default_fetch_k

        # สร้างโฟลเดอร์ chroma_db ถ้ายังไม่มี
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        # โหลด embedding model เข้า RAM (~80MB, ใช้เวลาครั้งแรก 3-5 วินาที)
        # หลังจากนี้การ embed ข้อความใหม่จะเร็วมาก
        self.embeddings = HuggingFaceEmbeddings(
            model_name=self.embedding_model_name
        )

        # vector store จะถูกสร้าง/โหลด ตอนเรียก build_vector_store() ครั้งแรก
        # (lazy init — ประหยัด RAM ถ้ายังไม่มีการค้นหา)
        self.vectorstore: Chroma | None = None

    # ═══════════════════════════════════════════════════════════════
    #  PHASE 1 — LOADING: โหลด chunks.json จาก disk
    # ═══════════════════════════════════════════════════════════════

    def _resolve_chunks_path(self) -> Path:
        """
        หาไฟล์ chunks ใน rag/ โดยลอง 2 ชื่อ
        (รองรับทั้งชื่อ chunks.json และ chunks (3).json เผื่อมีการรันใหม่จาก notebook)
        """
        candidates = [
            self.rag_dir / "chunks.json",
            self.rag_dir / "chunks (3).json",
        ]
        for path in candidates:
            if path.exists():
                return path
        raise FileNotFoundError("ไม่พบไฟล์ chunks.json หรือ chunks (3).json ในโฟลเดอร์ rag/")

    def load_chunks(self) -> List[Dict[str, Any]]:
        """
        อ่าน chunks.json → คืน list ของ dict
        ตัวอย่าง 1 chunk ในไฟล์:
          {
            "section_id": "SEC_001",
            "title": "Scammer คือ",
            "chunk_id": "SEC_001_chunk_1",
            "chunk_text": "สแกมเมอร์คือบุคคล...",
            "chunk_word_count": 176
          }
        """
        if not self.chunks_path.exists():
            raise FileNotFoundError(f"ไม่พบไฟล์ chunks: {self.chunks_path}")

        with open(self.chunks_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # validate schema — ต้องเป็น list ของ objects
        if not isinstance(data, list):
            raise ValueError("ไฟล์ chunks ต้องเป็น list ของ objects")

        return data

    # ═══════════════════════════════════════════════════════════════
    #  PHASE 2 — TRANSFORMATION: chunks → LangChain Documents
    # ═══════════════════════════════════════════════════════════════

    def chunks_to_documents(self, chunks: List[Dict[str, Any]]) -> List[Document]:
        """
        แปลง chunks (dict) → Document (LangChain class มาตรฐาน)

        ทำไมต้องแปลง?
          - Document เป็นรูปแบบกลางที่ LangChain components ทุกตัวเข้าใจ
          - metadata จะติดไปด้วยทุกขั้น — ใช้แสดงแหล่งที่มาตอน retrieve ได้
          - สำคัญต่อ UX: ผู้ใช้เห็นว่าคำตอบมาจาก chunk ไหน/หัวข้ออะไร
        """
        documents: List[Document] = []

        for item in chunks:
            chunk_text = str(item.get("chunk_text", "")).strip()

            # ข้าม chunk ว่าง (safeguard — ไม่ควรเจอถ้า notebook ทำ QA แล้ว)
            if not chunk_text:
                continue

            # เก็บ metadata ครบถ้วนเพื่อ trace กลับไปหาแหล่งที่มาได้
            metadata = {
                "section_id": item.get("section_id", ""),
                "title": item.get("title", ""),
                "chunk_id": item.get("chunk_id", ""),
                "chunk_char_count": item.get("chunk_char_count", 0),
                "chunk_word_count": item.get("chunk_word_count", 0),
                "source_title": item.get("source_title", ""),
            }

            documents.append(
                Document(
                    page_content=chunk_text,  # เนื้อความที่จะ embed
                    metadata=metadata,         # ติดไปด้วยทุกขั้น
                )
            )

        return documents

    # ═══════════════════════════════════════════════════════════════
    #  PHASE 3 — VECTOR STORE: สร้าง/โหลด ChromaDB
    # ═══════════════════════════════════════════════════════════════

    def build_vector_store(self, force_rebuild: bool = False) -> Chroma:
        """
        กลยุทธ์: ถ้ามี ChromaDB แล้ว → โหลดกลับจาก disk (เร็ว)
                 ถ้ายังไม่มี หรือสั่ง rebuild → embed ใหม่ + save ลง disk

        ผลคือ: Flask start ครั้งแรก = ช้า (embed 139 chunks)
               Flask start ครั้งถัด ๆ ไป = เร็ว (แค่โหลด index)
        """
        # ตรวจว่ามี index เดิมอยู่บน disk ไหม
        has_existing_index = (
            self.persist_directory.exists()
            and any(self.persist_directory.iterdir())
        )

        if has_existing_index and not force_rebuild:
            # ───────────────────────────────────
            # CASE A: มีแล้ว → โหลดกลับมา (fast path)
            # ───────────────────────────────────
            # ไม่ต้อง embed ใหม่ — ประหยัดเวลา ~10-30 วินาที
            self.vectorstore = Chroma(
                persist_directory=str(self.persist_directory),
                embedding_function=self.embeddings,
            )
            return self.vectorstore

        # ───────────────────────────────────────────────
        # CASE B: ไม่มี / สั่ง rebuild → สร้างใหม่ทั้งหมด
        # ───────────────────────────────────────────────
        chunks = self.load_chunks()                     # 1. โหลด chunks.json
        documents = self.chunks_to_documents(chunks)    # 2. แปลงเป็น Document

        if not documents:
            raise ValueError("ไม่พบ documents ที่ใช้สร้าง vector store")

        # 3. Embed ทั้ง 139 chunks → vectors → save ลง ChromaDB
        #    ขั้นนี้ใช้เวลา ~10-30 วินาที (ครั้งเดียวชั่วชีวิต index)
        self.vectorstore = Chroma.from_documents(
            documents=documents,                        # chunks ที่จะ embed
            embedding=self.embeddings,                  # MiniLM model
            persist_directory=str(self.persist_directory),  # save ที่ rag/chroma_db/
        )
        return self.vectorstore

    def rebuild(self) -> Chroma:
        """บังคับสร้างใหม่ — ใช้ตอน update chunks.json"""
        return self.build_vector_store(force_rebuild=True)

    def load_or_build(self) -> Chroma:
        """โหลดถ้ามี สร้างถ้าไม่มี — pattern ที่ใช้บ่อยสุด"""
        return self.build_vector_store(force_rebuild=False)

    # ═══════════════════════════════════════════════════════════════
    #  PHASE 4 — RETRIEVAL: ค้นหา chunks ที่เกี่ยวข้องกับคำถาม
    # ═══════════════════════════════════════════════════════════════

    def get_retriever(self, k: int | None = None, fetch_k: int | None = None):
        """
        สร้าง retriever แบบ MMR (Maximal Marginal Relevance)

        MMR vs Similarity ธรรมดา:
          - Similarity: เอา top-k ที่คล้ายที่สุด → อาจได้ chunks ซ้ำ ๆ เรื่องเดียวกัน
          - MMR: เอา top-k ที่ "คล้าย + หลากหลาย" → ได้มุมมองครบกว่า

        กระบวนการ MMR:
          1. หา fetch_k candidates (8 ตัว) ที่คล้าย query มากสุด
          2. เลือก 1 ตัวแรกที่คล้ายที่สุด
          3. เลือกตัวถัดไปที่ "คล้าย query แต่ต่างจากที่เลือกแล้ว"
          4. ทำซ้ำจนได้ k ตัว (4 ตัว)
        """
        # lazy init: ถ้ายังไม่มี vectorstore ก็สร้าง/โหลดเอาตอนนี้
        if self.vectorstore is None:
            self.load_or_build()

        k = k or self.default_k
        fetch_k = fetch_k or self.default_fetch_k

        # safeguard: fetch_k ต้องมากกว่า k เสมอ ไม่งั้น MMR ไม่มีทางเลือก
        if fetch_k < k:
            fetch_k = k * 2

        return self.vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": k,              # จำนวน chunks ที่คืนออกไป
                "fetch_k": fetch_k,  # จำนวน candidates ที่พิจารณาก่อนคัด
            },
        )

    def similarity_search(self, query: str, k: int | None = None) -> List[Document]:
        """
        Similarity search ธรรมดา — ใช้เป็น fallback ถ้า MMR มีปัญหา
        """
        if self.vectorstore is None:
            self.load_or_build()

        k = k or self.default_k
        return self.vectorstore.similarity_search(query, k=k)

    def retrieve_documents(
        self,
        query: str,
        k: int | None = None,
        fetch_k: int | None = None,
    ) -> List[Document]:
        """
        ฟังก์ชันหลักสำหรับดึง chunks — มี fallback ในตัว

        Flow:
          1. ลองใช้ MMR retriever ก่อน (default)
          2. ถ้าพัง → fallback ไป similarity search ธรรมดา
        """
        query = str(query or "").strip()
        if not query:
            return []

        if self.vectorstore is None:
            self.load_or_build()

        k = k or self.default_k
        fetch_k = fetch_k or self.default_fetch_k

        try:
            # ลอง MMR ก่อน
            retriever = self.get_retriever(k=k, fetch_k=fetch_k)
            docs = retriever.invoke(query)
            return docs if docs else []
        except Exception:
            # ถ้า MMR มีปัญหา (เช่น fetch_k ใหญ่เกิน) → fallback
            return self.similarity_search(query, k=k)

    def retrieve_context(
        self,
        query: str,
        k: int | None = None,
        fetch_k: int | None = None,
    ) -> Dict[str, Any]:
        """
        เป็น wrapper ที่ reasoning.py เรียกใช้โดยตรง

        Input:
          query = "Scammer คืออะไร?"

        Output:
          {
            "query": "Scammer คืออะไร?",
            "documents": [Document, Document, ...],    # raw docs
            "context_text": "[เอกสารที่ 1] หัวข้อ: ...\n[เอกสารที่ 2] ...",
            "sources": [{"title": "...", "chunk_id": "..."}, ...]
          }

        ฟังก์ชันนี้:
          - รวม 4 chunks เป็น context_text ก้อนเดียว (ยัดเข้า prompt ได้เลย)
          - แยก sources ออกมา (ให้ frontend แสดงเป็น reference ใต้คำตอบ)
        """
        docs = self.retrieve_documents(query=query, k=k, fetch_k=fetch_k)

        context_blocks: List[str] = []
        sources: List[Dict[str, Any]] = []

        for i, doc in enumerate(docs, start=1):
            # ดึง title จาก metadata (มี 2 key สำรอง)
            title = (
                doc.metadata.get("title")
                or doc.metadata.get("source_title")
                or "ไม่ระบุหัวข้อ"
            )
            chunk_id = doc.metadata.get("chunk_id", "")
            content = str(doc.page_content or "").strip()

            # ฟอร์แมตเป็นบล็อกที่อ่านง่าย ใส่เลขเอกสาร
            # ตัวอย่างที่ LLM จะเห็น:
            #   [เอกสารที่ 1] หัวข้อ: Scammer คือ
            #   Chunk: SEC_001_chunk_1
            #   เนื้อหา: สแกมเมอร์คือบุคคล...
            context_blocks.append(
                f"[เอกสารที่ {i}] หัวข้อ: {title}\n"
                f"Chunk: {chunk_id}\n"
                f"เนื้อหา: {content}"
            )

            # sources จะถูกส่งกลับไปที่ frontend เพื่อแสดงใต้คำตอบ
            sources.append({
                "title": title,
                "chunk_id": chunk_id,
                "section_id": doc.metadata.get("section_id", ""),
                "chunk_word_count": doc.metadata.get("chunk_word_count", 0),
            })

        return {
            "query": query,
            "documents": docs,
            "context_text": "\n\n".join(context_blocks),
            "sources": sources,
        }