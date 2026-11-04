"""
core/safe_mode.py — HONESTIC OS Safe Mode & Fault Tolerance System

Guarantees system availability and recovery in failure scenarios:
- Detects repeated startup crashes or explicit safe mode triggers
- In Safe Mode:
  - Disables non-essential 3rd-party plugins
  - Suspends heavy background file watchers and indexing
  - Loads minimal core services while keeping ATHENA online
- Provides self-healing controls to restore full operational state
"""

from __future__ import annotations
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
FLAG_FILE = CONFIG_DIR / "safe_mode.flag"
CRASH_GUARD_FILE = CONFIG_DIR / "crash_guard.json"


class SafeModeManager:
    _instance: Optional["SafeModeManager"] = None

    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self._is_active = self._evaluate_safe_mode()

    @classmethod
    def get_instance(cls) -> "SafeModeManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _evaluate_safe_mode(self) -> bool:
        """Determines if safe mode should be active."""
        # 1. Explicit CLI argument
        if "--safe-mode" in sys.argv:
            return True

        # 2. Environment variable
        if os.environ.get("HONESTIC_SAFE_MODE", "").strip().lower() in ("1", "true", "yes"):
            return True

        # 3. Explicit flag file
        if FLAG_FILE.exists():
            return True

        # 4. Crash loop detector (>2 abrupt terminations within 20s of launch)
        if CRASH_GUARD_FILE.exists():
            try:
                data = json.loads(CRASH_GUARD_FILE.read_text(encoding="utf-8"))
                failures = data.get("consecutive_crashes", 0)
                if failures >= 2:
                    print(f"[SafeMode] ⚠️ Detected {failures} consecutive startup crashes. Automatically activating Safe Mode.")
                    self.enable_safe_mode(reason=f"Auto-triggered: {failures} consecutive startup crashes")
                    return True
            except Exception:
                pass

        return False

    def is_safe_mode(self) -> bool:
        return self._is_active

    def record_boot_start(self):
        """Called at main startup entrypoint before heavy initializations."""
        try:
            data = {"last_start": time.time(), "consecutive_crashes": 0, "status": "booting"}
            if CRASH_GUARD_FILE.exists():
                try:
                    data = json.loads(CRASH_GUARD_FILE.read_text(encoding="utf-8"))
                except Exception:
                    pass
            data["consecutive_crashes"] = data.get("consecutive_crashes", 0) + 1
            data["last_start"] = time.time()
            data["status"] = "booting"
            CRASH_GUARD_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")
        except Exception:
            pass

    def record_successful_boot(self):
        """Called when system has initialized successfully and entered stable event loop."""
        try:
            data = {
                "last_start": time.time(),
                "last_healthy": datetime.now().isoformat(),
                "consecutive_crashes": 0,
                "status": "healthy"
            }
            CRASH_GUARD_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")
        except Exception:
            pass

    def enable_safe_mode(self, reason: str = "User requested"):
        self._is_active = True
        try:
            FLAG_FILE.write_text(json.dumps({
                "enabled_at": datetime.now().isoformat(),
                "reason": reason
            }, indent=4), encoding="utf-8")
        except Exception:
            pass

    def disable_safe_mode(self):
        self._is_active = False
        try:
            if FLAG_FILE.exists():
                FLAG_FILE.unlink(missing_ok=True)
            self.record_successful_boot()
        except Exception:
            pass

    def get_status(self) -> Dict[str, Any]:
        info = {
            "safe_mode_active": self._is_active,
            "is_safe_mode": self._is_active,
            "plugins_allowed": not self._is_active,
            "background_jobs_allowed": not self._is_active,
            "reason": "Normal operational state"
        }
        if self._is_active and FLAG_FILE.exists():
            try:
                d = json.loads(FLAG_FILE.read_text(encoding="utf-8"))
                info["reason"] = d.get("reason", "Safe Mode flag active")
                info["enabled_at"] = d.get("enabled_at", "")
            except Exception:
                pass
        return info
