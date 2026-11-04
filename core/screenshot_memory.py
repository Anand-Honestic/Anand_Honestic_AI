"""
core/screenshot_memory.py — HONESTIC OS Visual Screenshot Memory Engine

Allows ATHENA to remember and visually anchor the computer screen:
- Captures high-res screen snapshot on command ("remember this screen")
- Detects foreground application, project name, active document, and window title
- Saves compressed snapshot into memory/screenshots/
- Attaches custom notes and links node to the Second Brain Knowledge Graph
- Provides instant retrieval by project or tag
"""

from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from core.context_engine import ContextEngine
from core.second_brain import SecondBrain
from core.memory_guard import MemoryGuard

BASE_DIR = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = BASE_DIR / "memory" / "screenshots"
MANIFEST_FILE = SCREENSHOTS_DIR / "manifest.json"


class ScreenshotMemoryEngine:
    _instance: Optional["ScreenshotMemoryEngine"] = None

    def __init__(self):
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        self._manifest: List[Dict[str, Any]] = self._load_manifest()

    @classmethod
    def get_instance(cls) -> "ScreenshotMemoryEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_manifest(self) -> List[Dict[str, Any]]:
        return MemoryGuard.load_json_safe(MANIFEST_FILE, fallback_factory=list)

    def _save_manifest(self):
        MemoryGuard.save_json_atomic(MANIFEST_FILE, self._manifest)

    def remember_screen(self, note: str = "") -> Dict[str, Any]:
        """
        Captures current screen and stores it with context awareness and Second Brain linkage.
        """
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        img_filename = f"screen_{ts}.jpg"
        img_path = SCREENSHOTS_DIR / img_filename

        # 1. Capture screen using screen_processor
        from actions.screen_processor import _capture_screen
        img_bytes, mime_t = _capture_screen()
        img_path.write_bytes(img_bytes)

        # 2. Extract context
        ctx = ContextEngine.get_instance().get_active_context()
        app_name = ctx.get("app_name", "Desktop")
        window_title = ctx.get("window_title", "Active Window")
        project = ctx.get("project", "HONESTIC OS")
        file_name = ctx.get("file", "")

        entry = {
            "id": f"shot_{ts}",
            "filename": img_filename,
            "filepath": str(img_path),
            "timestamp": datetime.now().isoformat(),
            "note": note.strip() or f"Screen memory captured during {ctx.get('activity', 'Work')}",
            "context": {
                "app": app_name,
                "window": window_title,
                "project": project,
                "file": file_name,
            },
            "tags": ["screenshot", app_name.lower().replace(" ", "_"), project.lower().replace(" ", "_")]
        }

        self._manifest.insert(0, entry)
        if len(self._manifest) > 100:
            self._manifest = self._manifest[:100]
        self._save_manifest()

        # 3. Link to Second Brain Knowledge Graph
        try:
            sb = SecondBrain.get_instance()
            sb_node = sb.add_node(
                node_type="screenshot",
                title=f"Visual Memory: {app_name} ({ts})",
                content=f"Window: {window_title}\nNote: {entry['note']}\nFile: {file_name}",
                tags=entry["tags"]
            )
            # Find and link to project node if exists
            for n in sb.get_graph_export().get("nodes", []):
                if n.get("type") == "project" and project.lower() in n.get("title", "").lower():
                    sb.link_nodes(sb_node["id"], n["id"], relation="visual_snapshot")
                    break
        except Exception as e:
            print(f"[ScreenshotMemory] ⚠️ Second Brain link notice: {e}")

        return {
            "ok": True,
            "id": entry["id"],
            "filename": img_filename,
            "filepath": str(img_path),
            "app": app_name,
            "project": project,
            "note": entry["note"],
            "message": f"Screen remembered and catalogued for project '{project}'."
        }

    def get_recent_screenshots(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self._manifest[:limit]
