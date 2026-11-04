"""
core/profile_manager.py — HONESTIC OS Multi-Profile System

Supports switching between Anand_Honestic (Founder/Owner), Guest, and custom profiles.
Each profile encapsulates voice, memory, theme, AI persona, and settings.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from core.os_identity import OWNER_NAME, DEFAULT_AI_NAME

BASE_DIR = Path(__file__).resolve().parent.parent
PROFILES_DIR = BASE_DIR / "memory" / "profiles"
CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"


class ProfileManager:
    _instance: Optional["ProfileManager"] = None

    def __init__(self):
        PROFILES_DIR.mkdir(parents=True, exist_ok=True)
        self._ensure_default_profiles()
        self._active_profile = self._get_saved_active_profile()

    @classmethod
    def get_instance(cls) -> "ProfileManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _ensure_default_profiles(self):
        # 1. Owner Profile: Anand_Honestic
        owner_file = PROFILES_DIR / f"{OWNER_NAME}.json"
        if not owner_file.exists():
            owner_data = {
                "profile_name": OWNER_NAME,
                "display_name": f"👑 {OWNER_NAME}",
                "role": "Founder & Owner",
                "assistant_name": DEFAULT_AI_NAME,
                "ai_personality": "ATHENA",
                "voice_name": "Athena",
                "theme_name": "glass_blue",
                "avatar_type": "female",
                "performance_mode": "ultra_fast",
                "is_owner": True,
                "created_at": datetime.now().isoformat(),
            }
            owner_file.write_text(json.dumps(owner_data, indent=4), encoding="utf-8")

        # 2. Guest Profile
        guest_file = PROFILES_DIR / "Guest.json"
        if not guest_file.exists():
            guest_data = {
                "profile_name": "Guest",
                "display_name": "👤 Guest User",
                "role": "Guest",
                "assistant_name": "NOVA",
                "ai_personality": "NOVA",
                "voice_name": "Nova",
                "theme_name": "midnight_black",
                "avatar_type": "minimal",
                "performance_mode": "normal",
                "is_owner": False,
                "created_at": datetime.now().isoformat(),
            }
            guest_file.write_text(json.dumps(guest_data, indent=4), encoding="utf-8")

    def _get_saved_active_profile(self) -> str:
        try:
            if CONFIG_PATH.exists():
                cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                saved = cfg.get("active_profile", OWNER_NAME)
                if (PROFILES_DIR / f"{saved}.json").exists():
                    return saved
        except Exception:
            pass
        return OWNER_NAME

    def list_profiles(self) -> List[Dict[str, Any]]:
        self._ensure_default_profiles()
        profiles = []
        for p in PROFILES_DIR.glob("*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                profiles.append(data)
            except Exception:
                pass
        profiles.sort(key=lambda x: (not x.get("is_owner", False), x.get("profile_name", "")))
        return profiles

    def get_active_profile(self) -> Dict[str, Any]:
        return self.get_active_profile_data()

    def get_active_profile_data(self) -> Dict[str, Any]:
        pfile = PROFILES_DIR / f"{self._active_profile}.json"
        if pfile.exists():
            try:
                return json.loads(pfile.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "profile_name": OWNER_NAME,
            "display_name": f"👑 {OWNER_NAME}",
            "role": "Founder & Owner",
            "assistant_name": DEFAULT_AI_NAME,
            "ai_personality": "ATHENA",
            "voice_name": "Athena",
            "theme_name": "glass_blue",
            "avatar_type": "female",
            "performance_mode": "ultra_fast",
            "is_owner": True,
        }

    def switch_profile(self, profile_name: str) -> Dict[str, Any]:
        pfile = PROFILES_DIR / f"{profile_name}.json"
        if not pfile.exists():
            return self.get_active_profile_data()

        try:
            pdata = json.loads(pfile.read_text(encoding="utf-8"))
            self._active_profile = profile_name

            # Synchronize to main config
            cfg = {}
            if CONFIG_PATH.exists():
                cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

            cfg["active_profile"] = profile_name
            cfg["user_name"] = pdata.get("profile_name", OWNER_NAME)
            cfg["assistant_name"] = pdata.get("assistant_name", DEFAULT_AI_NAME)
            cfg["ai_personality"] = pdata.get("ai_personality", "ATHENA")
            cfg["voice_name"] = pdata.get("voice_name", "Athena")
            cfg["theme_name"] = pdata.get("theme_name", "glass_blue")
            cfg["avatar_type"] = pdata.get("avatar_type", "female")
            cfg["performance_mode"] = pdata.get("performance_mode", "ultra_fast")

            CONFIG_PATH.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
            return pdata
        except Exception as e:
            print(f"[ProfileManager] Failed to switch profile: {e}")
            return self.get_active_profile_data()

    def create_profile(self, name: str, assistant_name: str = "ATHENA",
                       theme: str = "glass_blue", voice: str = "Athena") -> bool:
        clean_name = "".join(c for c in name if c.isalnum() or c in ("_", "-")).strip()
        if not clean_name:
            return False
        pfile = PROFILES_DIR / f"{clean_name}.json"
        data = {
            "profile_name": clean_name,
            "display_name": clean_name,
            "role": "User",
            "assistant_name": assistant_name,
            "ai_personality": "ATHENA",
            "voice_name": voice,
            "theme_name": theme,
            "avatar_type": "female",
            "performance_mode": "ultra_fast",
            "is_owner": False,
            "created_at": datetime.now().isoformat(),
        }
        pfile.write_text(json.dumps(data, indent=4), encoding="utf-8")
        return True
