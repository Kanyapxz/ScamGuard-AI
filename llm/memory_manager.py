from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any


class MemoryManager:
    """
    SQLite-based memory manager
    - เก็บประวัติแชทต่อ session
    - เก็บ preference ผู้ใช้
    - เก็บ last topic / last result / summary
    - เก็บ detect payload ล่าสุดไว้ใช้กับฟีเจอร์ next-step
    """

    def __init__(self, db_path: str | Path | None = None, max_history: int = 12):
        self.max_history = max_history

        if db_path is None:
            current_dir = Path(__file__).resolve().parent
            self.db_path = current_dir / "memory.db"
        else:
            self.db_path = Path(db_path)

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    # ─────────────────────────────
    # DB INIT
    # ─────────────────────────────
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        names = {row["name"] for row in rows}
        if column not in names:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    mode TEXT,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS session_state (
                    session_id TEXT PRIMARY KEY,
                    last_topic TEXT,
                    last_mode TEXT,
                    last_result TEXT,
                    summary TEXT,
                    detect_payload TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id)
                )
            """)

            self._ensure_column(conn, "session_state", "detect_payload", "detect_payload TEXT")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    session_id TEXT PRIMARY KEY,
                    default_mode TEXT DEFAULT 'detect',
                    response_style TEXT DEFAULT 'normal',
                    language TEXT DEFAULT 'th',
                    FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id)
                )
            """)

            conn.commit()

    # ─────────────────────────────
    # HELPERS
    # ─────────────────────────────
    @staticmethod
    def sanitize_text(text: str, max_len: int = 1200) -> str:
        text = str(text or "").strip()

        text = re.sub(r"https?://\S+|www\.\S+", "[URL]", text, flags=re.I)
        text = re.sub(r"\b\d{6}\b", "[OTP]", text)
        text = re.sub(r"\b\d{10,16}\b", "[NUMBER]", text)
        text = re.sub(r"\s+", " ", text).strip()

        if len(text) > max_len:
            text = text[:max_len] + "..."
        return text

    @staticmethod
    def sanitize_detect_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
        if not payload:
            return {}

        safe = {
            "final_label": str(payload.get("final_label", "")),
            "final_color": str(payload.get("final_color", "")),
            "reply": str(payload.get("reply", ""))[:500],
            "reasons": [str(x)[:220] for x in payload.get("reasons", [])[:8]],
            "indicators": [str(x)[:220] for x in payload.get("indicators", [])[:8]],
            "advice": [str(x)[:240] for x in payload.get("advice", [])[:8]],
            "link_signals": [str(x)[:220] for x in payload.get("link_signals", [])[:8]],
            "link_unsafe_count": int(payload.get("link_check", {}).get("summary", {}).get("unsafe_count", 0)),
        }
        return safe

    def ensure_session(self, session_id: str) -> None:
        session_id = str(session_id).strip() or "anonymous"

        with self._connect() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO chat_sessions(session_id)
                VALUES (?)
            """, (session_id,))

            conn.execute("""
                INSERT OR IGNORE INTO session_state(session_id, last_topic, last_mode, last_result, summary, detect_payload)
                VALUES (?, '', '', '', '', '{}')
            """, (session_id,))

            conn.execute("""
                INSERT OR IGNORE INTO user_preferences(session_id, default_mode, response_style, language)
                VALUES (?, 'detect', 'normal', 'th')
            """, (session_id,))

            conn.execute("""
                UPDATE chat_sessions
                SET updated_at = CURRENT_TIMESTAMP
                WHERE session_id = ?
            """, (session_id,))
            conn.commit()

    # ─────────────────────────────
    # MESSAGES
    # ─────────────────────────────
    def add_message(self, session_id: str, role: str, content: str, mode: str = "") -> None:
        self.ensure_session(session_id)
        clean_content = self.sanitize_text(content)

        with self._connect() as conn:
            conn.execute("""
                INSERT INTO chat_messages(session_id, role, mode, content)
                VALUES (?, ?, ?, ?)
            """, (session_id, role, mode, clean_content))

            conn.execute("""
                UPDATE chat_sessions
                SET updated_at = CURRENT_TIMESTAMP
                WHERE session_id = ?
            """, (session_id,))
            conn.commit()

    def get_recent_history(self, session_id: str, limit: int | None = None) -> list[dict[str, Any]]:
        self.ensure_session(session_id)
        limit = limit or self.max_history

        with self._connect() as conn:
            rows = conn.execute("""
                SELECT role, mode, content, created_at
                FROM chat_messages
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
            """, (session_id, limit)).fetchall()

        return [dict(row) for row in reversed(rows)]

    def format_recent_history(self, session_id: str, limit: int = 6) -> str:
        history = self.get_recent_history(session_id, limit=limit)
        if not history:
            return "-"

        lines = []
        for item in history:
            role = "ผู้ใช้" if item["role"] == "user" else "ผู้ช่วย"
            content = item["content"]
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    # ─────────────────────────────
    # STATE
    # ─────────────────────────────
    def update_state(
        self,
        session_id: str,
        *,
        last_topic: str | None = None,
        last_mode: str | None = None,
        last_result: str | None = None,
        summary: str | None = None,
        detect_payload: dict[str, Any] | None = None,
    ) -> None:
        self.ensure_session(session_id)

        current = self.get_state(session_id)

        next_topic = current.get("last_topic", "") if last_topic is None else last_topic
        next_mode = current.get("last_mode", "") if last_mode is None else last_mode
        next_result = current.get("last_result", "") if last_result is None else last_result
        next_summary = current.get("summary", "") if summary is None else summary

        if detect_payload is None:
            next_detect_payload = current.get("detect_payload", {})
        else:
            next_detect_payload = self.sanitize_detect_payload(detect_payload)

        with self._connect() as conn:
            conn.execute("""
                INSERT INTO session_state(session_id, last_topic, last_mode, last_result, summary, detect_payload, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(session_id) DO UPDATE SET
                    last_topic = excluded.last_topic,
                    last_mode = excluded.last_mode,
                    last_result = excluded.last_result,
                    summary = excluded.summary,
                    detect_payload = excluded.detect_payload,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                session_id,
                next_topic,
                next_mode,
                next_result,
                next_summary,
                json.dumps(next_detect_payload, ensure_ascii=False),
            ))
            conn.commit()

    def get_state(self, session_id: str) -> dict[str, Any]:
        self.ensure_session(session_id)

        with self._connect() as conn:
            row = conn.execute("""
                SELECT last_topic, last_mode, last_result, summary, detect_payload, updated_at
                FROM session_state
                WHERE session_id = ?
            """, (session_id,)).fetchone()

        if not row:
            return {
                "last_topic": "",
                "last_mode": "",
                "last_result": "",
                "summary": "",
                "detect_payload": {},
                "updated_at": "",
            }

        data = dict(row)
        raw_payload = data.get("detect_payload") or "{}"
        try:
            data["detect_payload"] = json.loads(raw_payload)
        except Exception:
            data["detect_payload"] = {}
        return data

    def get_last_detect_payload(self, session_id: str) -> dict[str, Any]:
        state = self.get_state(session_id)
        payload = state.get("detect_payload", {})
        return payload if isinstance(payload, dict) else {}

    # ─────────────────────────────
    # PREFERENCES
    # ─────────────────────────────
    def get_preferences(self, session_id: str) -> dict[str, Any]:
        self.ensure_session(session_id)

        with self._connect() as conn:
            row = conn.execute("""
                SELECT default_mode, response_style, language
                FROM user_preferences
                WHERE session_id = ?
            """, (session_id,)).fetchone()

        if not row:
            return {
                "default_mode": "detect",
                "response_style": "normal",
                "language": "th",
            }

        return dict(row)

    def update_preferences(
        self,
        session_id: str,
        *,
        default_mode: str | None = None,
        response_style: str | None = None,
        language: str | None = None,
    ) -> None:
        self.ensure_session(session_id)
        current = self.get_preferences(session_id)

        next_default_mode = current["default_mode"] if default_mode is None else default_mode
        next_response_style = current["response_style"] if response_style is None else response_style
        next_language = current["language"] if language is None else language

        with self._connect() as conn:
            conn.execute("""
                INSERT INTO user_preferences(session_id, default_mode, response_style, language)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    default_mode = excluded.default_mode,
                    response_style = excluded.response_style,
                    language = excluded.language
            """, (session_id, next_default_mode, next_response_style, next_language))
            conn.commit()

    # ─────────────────────────────
    # SUMMARY / CONTEXT
    # ─────────────────────────────
    def build_lightweight_summary(self, session_id: str) -> str:
        state = self.get_state(session_id)
        prefs = self.get_preferences(session_id)
        history = self.get_recent_history(session_id, limit=5)

        if not history:
            return "ยังไม่มีประวัติการสนทนา"

        topic = state.get("last_topic") or "ยังไม่ระบุหัวข้อ"
        last_result = state.get("last_result") or "ยังไม่มีผลล่าสุด"
        default_mode = prefs.get("default_mode", "detect")

        user_messages = [h["content"] for h in history if h["role"] == "user"]
        last_user = user_messages[-1] if user_messages else "-"

        return (
            f"หัวข้อล่าสุด: {topic} | "
            f"ผลล่าสุด: {last_result} | "
            f"โหมดหลัก: {default_mode} | "
            f"ข้อความล่าสุดของผู้ใช้: {last_user}"
        )

    def get_context_bundle(self, session_id: str) -> dict[str, Any]:
        self.ensure_session(session_id)
        state = self.get_state(session_id)
        prefs = self.get_preferences(session_id)
        history = self.get_recent_history(session_id, limit=self.max_history)
        history_text = self.format_recent_history(session_id, limit=6)

        if not state.get("summary"):
            auto_summary = self.build_lightweight_summary(session_id)
            self.update_state(session_id, summary=auto_summary)
            state = self.get_state(session_id)

        return {
            "session_id": session_id,
            "state": state,
            "preferences": prefs,
            "history": history,
            "history_text": history_text,
        }

    # ─────────────────────────────
    # DEBUG / EXPORT
    # ─────────────────────────────
    def export_session(self, session_id: str) -> dict[str, Any]:
        return self.get_context_bundle(session_id)

    def export_session_json(self, session_id: str) -> str:
        return json.dumps(self.export_session(session_id), ensure_ascii=False, indent=2)