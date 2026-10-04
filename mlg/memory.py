"""Pamięć MLG: fakty o szefie, historia rozmów, listy i przypomnienia (SQLite)."""

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS list_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    list_name TEXT NOT NULL,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    chat_id INTEGER NOT NULL,
    due_at TEXT NOT NULL,
    text TEXT NOT NULL,
    sent INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id, id);
CREATE INDEX IF NOT EXISTS idx_reminders_due ON reminders(sent, due_at);
"""

MAX_FACTS_IN_PROMPT = 60


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class Fact:
    id: int
    text: str


@dataclass
class Reminder:
    id: int
    user_id: int
    chat_id: int
    due_at: datetime
    text: str


class Memory:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.executescript(_SCHEMA)
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    # --- fakty ---

    def add_fact(self, user_id: int, text: str) -> Fact:
        text = text.strip()
        existing = self.db.execute(
            "SELECT id FROM facts WHERE user_id = ? AND lower(text) = lower(?)", (user_id, text)
        ).fetchone()
        if existing:
            return Fact(existing[0], text)
        cur = self.db.execute("INSERT INTO facts (user_id, text, created_at) VALUES (?, ?, ?)", (user_id, text, _now()))
        self.db.commit()
        return Fact(cur.lastrowid, text)

    def facts(self, user_id: int, limit: int | None = None) -> list[Fact]:
        sql = "SELECT id, text FROM facts WHERE user_id = ? ORDER BY id DESC"
        params: tuple = (user_id,)
        if limit:
            sql += " LIMIT ?"
            params += (limit,)
        rows = self.db.execute(sql, params).fetchall()
        return [Fact(r[0], r[1]) for r in reversed(rows)]

    def forget_fact(self, user_id: int, fact_id: int) -> bool:
        cur = self.db.execute("DELETE FROM facts WHERE user_id = ? AND id = ?", (user_id, fact_id))
        self.db.commit()
        return cur.rowcount > 0

    # --- historia rozmowy ---

    def add_message(self, user_id: int, role: str, content: str) -> None:
        self.db.execute(
            "INSERT INTO messages (user_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (user_id, role, content, _now()),
        )
        self.db.commit()

    def history(self, user_id: int, limit: int) -> list[dict]:
        rows = self.db.execute(
            "SELECT role, content FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit)
        ).fetchall()
        return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

    def clear_history(self, user_id: int) -> None:
        self.db.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
        self.db.commit()

    # --- listy (zakupy, TODO...) ---

    @staticmethod
    def _list_key(name: str) -> str:
        return name.strip().lower() or "ogólna"

    def add_list_item(self, user_id: int, list_name: str, text: str) -> None:
        self.db.execute(
            "INSERT INTO list_items (user_id, list_name, text, created_at) VALUES (?, ?, ?, ?)",
            (user_id, self._list_key(list_name), text.strip(), _now()),
        )
        self.db.commit()

    def list_items(self, user_id: int, list_name: str) -> list[str]:
        rows = self.db.execute(
            "SELECT text FROM list_items WHERE user_id = ? AND list_name = ? ORDER BY id",
            (user_id, self._list_key(list_name)),
        ).fetchall()
        return [r[0] for r in rows]

    def list_names(self, user_id: int) -> list[str]:
        rows = self.db.execute(
            "SELECT DISTINCT list_name FROM list_items WHERE user_id = ? ORDER BY list_name", (user_id,)
        ).fetchall()
        return [r[0] for r in rows]

    def remove_list_item(self, user_id: int, list_name: str, text: str) -> int:
        """Usuwa pozycje pasujące do tekstu (bez rozróżniania wielkości liter). Zwraca, ile usunięto."""
        cur = self.db.execute(
            "DELETE FROM list_items WHERE user_id = ? AND list_name = ? AND lower(text) LIKE lower(?)",
            (user_id, self._list_key(list_name), f"%{text.strip()}%"),
        )
        self.db.commit()
        return cur.rowcount

    def clear_list(self, user_id: int, list_name: str) -> int:
        cur = self.db.execute(
            "DELETE FROM list_items WHERE user_id = ? AND list_name = ?", (user_id, self._list_key(list_name))
        )
        self.db.commit()
        return cur.rowcount

    # --- przypomnienia ---

    def add_reminder(self, user_id: int, chat_id: int, due_at: datetime, text: str) -> int:
        cur = self.db.execute(
            "INSERT INTO reminders (user_id, chat_id, due_at, text) VALUES (?, ?, ?, ?)",
            (user_id, chat_id, due_at.isoformat(timespec="seconds"), text.strip()),
        )
        self.db.commit()
        return cur.lastrowid

    def pending_reminders(self, user_id: int) -> list[Reminder]:
        rows = self.db.execute(
            "SELECT id, user_id, chat_id, due_at, text FROM reminders WHERE user_id = ? AND sent = 0 ORDER BY due_at",
            (user_id,),
        ).fetchall()
        return [Reminder(r[0], r[1], r[2], datetime.fromisoformat(r[3]), r[4]) for r in rows]

    def due_reminders(self, now: datetime | None = None) -> list[Reminder]:
        now = now or datetime.now()
        rows = self.db.execute(
            "SELECT id, user_id, chat_id, due_at, text FROM reminders WHERE sent = 0 AND due_at <= ? ORDER BY due_at",
            (now.isoformat(timespec="seconds"),),
        ).fetchall()
        return [Reminder(r[0], r[1], r[2], datetime.fromisoformat(r[3]), r[4]) for r in rows]

    def mark_sent(self, reminder_id: int) -> None:
        self.db.execute("UPDATE reminders SET sent = 1 WHERE id = ?", (reminder_id,))
        self.db.commit()

    def cancel_reminder(self, user_id: int, reminder_id: int) -> bool:
        cur = self.db.execute(
            "DELETE FROM reminders WHERE user_id = ? AND id = ? AND sent = 0", (user_id, reminder_id)
        )
        self.db.commit()
        return cur.rowcount > 0
