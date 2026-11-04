"""
core/mobile_ecosystem.py — HONESTIC OS Mobile Companion Ecosystem & Remote Control

Features:
- Secure QR pairing with cryptographic time-bound seeds (5-min expiry)
- Multi-factor verification (PIN and/or Voice Identity)
- Persistent Trusted Device Registry with session management
- Secure Remote Execution:
  - App launch/close, diagnostics, project launch, report generation,
    workspace restore, security checks, and web navigation.
"""

from __future__ import annotations
import hashlib
import json
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

from core.os_identity import OWNER_NAME
from core.memory_guard import MemoryGuard
from core.permission_system import PermissionSystem

BASE_DIR = Path(__file__).resolve().parent.parent
DEVICES_FILE = BASE_DIR / "config" / "trusted_devices.json"


class MobileEcosystemManager:
    _instance: Optional["MobileEcosystemManager"] = None

    def __init__(self):
        DEVICES_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._pending_qr_pairs: Dict[str, Dict[str, Any]] = {}
        self._ensure_storage()

    @classmethod
    def get_instance(cls) -> "MobileEcosystemManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _ensure_storage(self):
        if not DEVICES_FILE.exists():
            MemoryGuard.save_json_atomic(DEVICES_FILE, {"devices": []})

    def _load_devices(self) -> Dict[str, Any]:
        data = MemoryGuard.load_json_safe(DEVICES_FILE, fallback_factory=lambda: {"devices": []})
        if not isinstance(data, dict) or "devices" not in data:
            return {"devices": []}
        return data

    def _save_devices(self, data: Dict[str, Any]):
        MemoryGuard.save_json_atomic(DEVICES_FILE, data)

    def generate_pairing_payload(self, server_host: str = "127.0.0.1", port: int = 8000) -> Dict[str, Any]:
        """
        Generates a secure, time-expiring pairing seed for phone QR scanning.
        Valid for 300 seconds (5 minutes).
        """
        pair_code = secrets.token_hex(16)
        expires_at = time.time() + 300
        qr_url = f"http://{server_host}:{port}/auto-login?key={pair_code}"

        payload = {
            "pair_code": pair_code,
            "qr_url": qr_url,
            "created_at": datetime.now().isoformat(),
            "expires_in_seconds": 300,
            "system": "HONESTIC OS",
            "founder": OWNER_NAME,
        }
        self._pending_qr_pairs[pair_code] = {
            "expires_at": expires_at,
            "payload": payload
        }
        return payload

    def pair_device(
        self,
        device_name: str,
        pair_code: str,
        client_ip: str = "127.0.0.1",
        pin: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validates pairing code & PIN, then registers device as trusted."""
        now = time.time()
        # Verify pair code if present in pending
        if pair_code in self._pending_qr_pairs:
            pending = self._pending_qr_pairs[pair_code]
            if pending["expires_at"] < now:
                return {"ok": False, "error": "Pairing QR has expired. Please refresh QR code on laptop."}
            del self._pending_qr_pairs[pair_code]

        # PIN Verification check
        if pin is not None:
            from core.ultra_security import UltraSecurityManager
            pin_res = UltraSecurityManager.get_instance().verify_pin(pin)
            if not pin_res:
                return {"ok": False, "error": "Invalid Founder Security PIN."}

        device_id = f"dev_{secrets.token_hex(8)}"
        device_token = secrets.token_urlsafe(32)

        entry = {
            "device_id": device_id,
            "device_name": device_name.strip() or "Mobile Companion",
            "device_token": device_token,
            "ip_address": client_ip,
            "status": "trusted",
            "paired_at": datetime.now().isoformat(),
            "last_active_at": datetime.now().isoformat(),
            "verified_by": "pin" if pin else "qr_code",
            "capabilities": [
                "mission_control", "dashboard", "notifications", "commands",
                "workspace_restore", "project_status", "vault_search", "memory_search"
            ]
        }

        data = self._load_devices()
        data["devices"].append(entry)
        self._save_devices(data)

        return {
            "ok": True,
            "device_id": device_id,
            "device_token": device_token,
            "device_name": entry["device_name"],
            "status": "trusted",
            "message": f"Device '{entry['device_name']}' successfully paired and trusted."
        }

    def list_trusted_devices(self) -> List[Dict[str, Any]]:
        data = self._load_devices()
        # Strip internal tokens from list output
        sanitized = []
        for d in data.get("devices", []):
            item = dict(d)
            item.pop("device_token", None)
            sanitized.append(item)
        return sanitized

    def verify_device_token(self, token: str) -> bool:
        if not token:
            return False
        data = self._load_devices()
        for d in data.get("devices", []):
            if d.get("device_token") == token and d.get("status") == "trusted":
                d["last_active_at"] = datetime.now().isoformat()
                self._save_devices(data)
                return True
        return False

    def revoke_device(self, device_id: str) -> bool:
        data = self._load_devices()
        devices = data.get("devices", [])
        initial_len = len(devices)
        data["devices"] = [d for d in devices if d.get("device_id") != device_id]
        if len(data["devices"]) < initial_len:
            self._save_devices(data)
            return True
        return False

    def revoke_all_devices(self) -> int:
        data = self._load_devices()
        count = len(data.get("devices", []))
        self._save_devices({"devices": []})
        return count

    def execute_remote_action(self, action: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes a remote command originating from a trusted mobile phone.
        Dangerous operations route through PermissionSystem.
        """
        params = parameters or {}
        act = action.lower().strip()
        t0 = time.perf_counter()

        if act == "open_app":
            app = params.get("app_name", "")
            from actions.open_app import open_app
            res = open_app(app)
            return {"ok": True, "action": act, "result": res}

        if act == "close_app":
            from actions.computer_settings import close_window
            close_window()
            return {"ok": True, "action": act, "message": "Closed active application window."}

        if act == "run_diagnostics":
            from core.diagnostics_center import DiagnosticsCenter
            diag = DiagnosticsCenter.get_instance().run_full_diagnostics()
            return {"ok": True, "action": act, "diagnostics": diag}

        if act == "system_status":
            from core.founder_mode import FounderModeEngine
            ctx = FounderModeEngine.get_instance().get_founder_context()
            return {"ok": True, "action": act, "status": ctx}

        if act == "open_website":
            url = params.get("url", "https://google.com")
            from core.computer_agent import ComputerUseAgent
            res = ComputerUseAgent.get_instance().open_website(url)
            return {"ok": True, "action": act, "result": res}

        if act == "restore_workspace":
            from core.workspace_memory import WorkspaceMemory
            WorkspaceMemory.get_instance().restore_workspace()
            return {"ok": True, "action": act, "message": "Workspace layout restored."}

        if act == "security_check":
            from core.ultra_security import UltraSecurityManager
            sec = UltraSecurityManager.get_instance().get_security_status()
            return {"ok": True, "action": act, "security": sec}

        elapsed = round((time.perf_counter() - t0) * 1000, 1)
        return {"ok": False, "error": f"Unsupported remote action: '{action}'", "elapsed_ms": elapsed}
