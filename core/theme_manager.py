"""
core/theme_manager.py — HONESTIC OS Theme Engine & Modern Design System

Windows 11 Fluent / Copilot Glassmorphism Styling
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, Optional

from core.os_identity import THEMES

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"


class ThemeManager:
    _instance: Optional["ThemeManager"] = None

    def __init__(self):
        self._current_theme_key = "glass_blue"
        self._custom_accent = "#00d4ff"
        self._load_saved()

    @classmethod
    def get_instance(cls) -> "ThemeManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_saved(self):
        try:
            if CONFIG_PATH.exists():
                cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                saved = cfg.get("theme_name", "glass_blue")
                if saved in THEMES or saved == "custom":
                    self._current_theme_key = saved
                self._custom_accent = cfg.get("ui_color", "#00d4ff")
        except Exception:
            self._current_theme_key = "glass_blue"

    def get_current_theme_key(self) -> str:
        return self._current_theme_key

    def get_active_theme(self) -> Dict[str, Any]:
        return self.get_theme_data(self._current_theme_key)

    def get_theme_data(self, key: Optional[str] = None) -> Dict[str, Any]:
        k = key or self._current_theme_key
        if k == "custom":
            return {
                "name": "Custom Theme",
                "accent": self._custom_accent,
                "accent_dim": "#007a99",
                "accent_ghost": "#001f2e",
                "bg": "#02070f",
                "panel": "rgba(2, 12, 22, 0.82)",
                "panel2": "rgba(4, 20, 36, 0.88)",
                "border": "#0d3347",
                "border_b": "#1a5c7a",
                "text": "#e0f2fe",
                "text_dim": "#7dd3fc",
                "glow": "rgba(0, 212, 255, 0.28)",
                "desc": "User Custom Designed Palette",
            }
        return THEMES.get(k, THEMES["glass_blue"])

    def set_theme(self, key: str, custom_accent: Optional[str] = None) -> Dict[str, Any]:
        if key in THEMES or key == "custom":
            self._current_theme_key = key
        if custom_accent:
            self._custom_accent = custom_accent

        # Persist to config
        try:
            cfg = {}
            if CONFIG_PATH.exists():
                cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            cfg["theme_name"] = self._current_theme_key
            if custom_accent:
                cfg["ui_color"] = custom_accent
            CONFIG_PATH.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
        except Exception as e:
            print(f"[ThemeManager] Error saving theme: {e}")

        return self.get_theme_data()

    def apply_to_palette_class(self, C) -> None:
        """Update global class C used in ui.py for seamless backward compatibility."""
        td = self.get_theme_data()
        C.BG = td["bg"]
        C.PANEL = td.get("panel", "#010d14")
        C.PANEL2 = td.get("panel2", "#010f18")
        C.BORDER = td["border"]
        C.BORDER_B = td["border_b"]
        C.PRI = td["accent"]
        C.PRI_DIM = td["accent_dim"]
        C.PRI_GHO = td["accent_ghost"]
        C.TEXT = td["text"]
        C.TEXT_DIM = td["text_dim"]

    def get_fluent_stylesheet(self) -> str:
        """Returns comprehensive Windows 11 Fluent Glassmorphic stylesheet."""
        td = self.get_theme_data()
        pri = td["accent"]
        pri_dim = td["accent_dim"]
        pri_gho = td["accent_ghost"]
        bg = td["bg"]
        border = td["border"]
        border_b = td["border_b"]
        text = td["text"]
        text_dim = td["text_dim"]

        return f"""
            /* HONESTIC OS — Windows 11 Fluent / Copilot Glass Theme */
            QWidget {{
                color: {text};
                font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif;
            }}

            /* Scrollbars */
            QScrollBar:vertical {{
                border: none;
                background: rgba(0, 0, 0, 0.2);
                width: 6px;
                border-radius: 3px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {border_b};
                min-height: 24px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {pri};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}

            /* Modern Buttons */
            QPushButton {{
                background: rgba(255, 255, 255, 0.04);
                color: {text};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {pri_gho};
                border-color: {pri};
                color: #ffffff;
            }}
            QPushButton:pressed {{
                background: {pri_dim};
                border-color: {pri};
            }}
            QPushButton:checked {{
                background: {pri_gho};
                border-color: {pri};
                color: {pri};
            }}

            /* Modern Inputs */
            QLineEdit, QTextEdit {{
                background: rgba(5, 12, 20, 0.85);
                color: #ffffff;
                border: 1.5px solid {border};
                border-radius: 8px;
                padding: 6px 10px;
                selection-background-color: {pri};
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border: 1.5px solid {pri};
                background: rgba(8, 16, 28, 0.95);
            }}

            /* Tooltips */
            QToolTip {{
                background: #030a14;
                color: {text};
                border: 1px solid {border_b};
                border-radius: 6px;
                padding: 5px 8px;
            }}

            /* Modern Cards / Frames */
            QFrame.card {{
                background: rgba(2, 14, 26, 0.65);
                border: 1px solid {border};
                border-radius: 12px;
            }}
            QFrame.card:hover {{
                border-color: {border_b};
            }}
        """
