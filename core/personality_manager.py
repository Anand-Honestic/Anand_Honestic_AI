"""
core/personality_manager.py — HONESTIC OS AI Personality & Persona Management

Supported Modes:
1. ATHENA — Intelligent female assistant, elegant, professional (Default)
2. AURA — Premium futuristic AI
3. NOVA — Modern AI companion
4. FRIDAY — Technical assistant
5. Custom Name — User-defined identity
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, Optional

from core.os_identity import PERSONALITIES, DEFAULT_AI_NAME

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"


class PersonalityManager:
    _instance: Optional["PersonalityManager"] = None

    def __init__(self):
        self._active_key = "ATHENA_OMEGA"
        self._custom_name = ""
        self._custom_prompt = ""
        self._load_saved()

    @classmethod
    def get_instance(cls) -> "PersonalityManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_saved(self):
        try:
            if CONFIG_PATH.exists():
                cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                saved = (cfg.get("ai_personality") or "ATHENA_OMEGA").strip().upper()
                if saved in PERSONALITIES:
                    self._active_key = saved
                else:
                    self._active_key = "ATHENA_OMEGA"
                self._custom_name = cfg.get("assistant_name", "")
                self._custom_prompt = cfg.get("custom_personality_prompt", "")
        except Exception:
            self._active_key = "ATHENA_OMEGA"

    def get_active_personality_key(self) -> str:
        return self._active_key

    def get_active_personality(self) -> Dict[str, Any]:
        return self.get_personality_data(self._active_key)

    def get_personality_data(self, key: Optional[str] = None) -> Dict[str, Any]:
        k = (key or self._active_key).upper()
        if k in PERSONALITIES:
            data = dict(PERSONALITIES[k])
            if k == "CUSTOM" and self._custom_name:
                data["name"] = self._custom_name
            return data
        return dict(PERSONALITIES.get("ATHENA_OMEGA", PERSONALITIES.get("ATHENA", {})))

    def get_display_name(self) -> str:
        if self._active_key == "CUSTOM" and self._custom_name:
            return self._custom_name
        return PERSONALITIES.get(self._active_key, {}).get("name", DEFAULT_AI_NAME)

    def get_prompt_injection(self) -> str:
        data = self.get_personality_data()
        addon = data.get("system_prompt_addon", "")
        if self._active_key == "CUSTOM" and self._custom_prompt:
            addon = self._custom_prompt
        return f"\n[AI PERSONALITY: {self.get_display_name()}]\n{addon}\n"

    def set_personality(
        self,
        key: str,
        custom_name: Optional[str] = None,
        custom_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        k = key.strip().upper()
        if k in PERSONALITIES or k == "CUSTOM":
            self._active_key = k
        if custom_name is not None:
            self._custom_name = custom_name.strip()
        if custom_prompt is not None:
            self._custom_prompt = custom_prompt.strip()

        # Update config
        try:
            cfg = {}
            if CONFIG_PATH.exists():
                cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            cfg["ai_personality"] = self._active_key
            cfg["assistant_name"] = self.get_display_name()
            if self._custom_prompt:
                cfg["custom_personality_prompt"] = self._custom_prompt
            CONFIG_PATH.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
        except Exception as e:
            print(f"[PersonalityManager] Error saving config: {e}")

        return self.get_personality_data()
