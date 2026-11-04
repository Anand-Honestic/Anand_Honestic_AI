"""
memory/screen_memory.py — HONESTIC OS Smart Screen Memory
Captures, indexes, and retrieves visual context alongside project metadata and notes.
"""

from __future__ import annotations
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from core.memory_guard import MemoryGuard

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_FILE = BASE_DIR / "data" / "screen_memory.json"
CAPTURES_DIR = BASE_DIR / "data" / "screen_captures"

class ScreenMemoryManager:
    _instance: Optional["ScreenMemoryManager"] = None

    def __init__(self):
        CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
        self._ensure_storage()

    @classmethod
    def get_instance(cls) -> "ScreenMemoryManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _ensure_storage(self):
        if not STORAGE_FILE.exists():
            MemoryGuard.save_json_atomic(STORAGE_FILE, {"captures": []})

    def _load_data(self) -> Dict[str, Any]:
        data = MemoryGuard.load_json_safe(STORAGE_FILE, fallback_factory=lambda: {"captures": []})
        if not isinstance(data, dict) or "captures" not in data:
            return {"captures": []}
        return data

    def _save_data(self, data: Dict[str, Any]):
        MemoryGuard.save_json_atomic(STORAGE_FILE, data)

    def record_screen_context(
        self,
        project: str = "General",
        notes: str = "",
        ocr_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Captures the current screen and attaches project context, notes, and timestamp.
        """
        capture_id = f"snap_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        now = datetime.now()
        image_path = CAPTURES_DIR / f"{capture_id}.png"

        # Attempt real screen capture
        captured = False
        try:
            import pyautogui
            screenshot = pyautogui.screenshot()
            screenshot.save(str(image_path))
            captured = True
        except Exception:
            # Fallback placeholder if headless or display unavailable
            image_path.write_bytes(b"")

        entry = {
            "id": capture_id,
            "timestamp": now.isoformat(),
            "time_str": now.strftime("%Y-%m-%d %H:%M:%S"),
            "project": project.strip() or "General",
            "notes": notes.strip(),
            "ocr_text": ocr_text or "",
            "image_path": str(image_path),
            "captured": captured
        }

        data = self._load_data()
        data["captures"].insert(0, entry)
        # Cap at 200 entries to prevent bloat
        data["captures"] = data["captures"][:200]
        self._save_data(data)

        return entry

    def search_screen_memory(self, query: str) -> List[Dict[str, Any]]:
        """Searches past captures by notes, project, OCR, or date."""
        q = query.lower().strip()
        data = self._load_data()
        results = []

        for item in data.get("captures", []):
            combined = f"{item.get('project', '')} {item.get('notes', '')} {item.get('ocr_text', '')} {item.get('time_str', '')}".lower()
            if q in combined:
                results.append(item)

        return results

    def get_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        data = self._load_data()
        return data.get("captures", [])[:limit]
