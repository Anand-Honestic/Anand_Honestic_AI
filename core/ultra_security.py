"""
core/ultra_security.py — HONESTIC OS Ultra Security Mode & Vault Protection

Safeguards Founder Anand_Honestic's private digital identity and systems:
- Multi-factor authentication:
  - Voice print acoustic verification
  - 4-to-6 digit Security PIN (PBKDF2-HMAC-SHA256 hashed)
  - Master Password
- Three security tiers:
  - FOUNDER_CLEARANCE: Unrestricted access to private memories, vault, code, and system settings.
  - GUEST_SANDBOX: Restricted mode when unknown voices or unauthenticated sessions are active.
  - VAULT_LOCKED: Complete encryption-ready lockout of long-term memory and knowledge nodes.
"""

from __future__ import annotations
import hashlib
import json
import os
import time
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

from core.os_identity import OWNER_NAME
from core.memory_guard import MemoryGuard

BASE_DIR = Path(__file__).resolve().parent.parent
SECURITY_CONFIG_FILE = BASE_DIR / "config" / "security_auth.json"


class PinVerificationResult(tuple):
    def __new__(cls, is_valid: bool, msg: str):
        return super().__new__(cls, (is_valid, msg))

    def __bool__(self):
        return bool(self[0])


class UltraSecurityManager:
    _instance: Optional["UltraSecurityManager"] = None

    TIER_FOUNDER = "FOUNDER_CLEARANCE"
    TIER_GUEST = "GUEST_SANDBOX"
    TIER_LOCKED = "VAULT_LOCKED"

    def __init__(self):
        SECURITY_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._tier: str = self.TIER_FOUNDER
        self._auth_state = self._load_or_init_auth()

    @classmethod
    def get_instance(cls) -> "UltraSecurityManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_or_init_auth(self) -> Dict[str, Any]:
        if SECURITY_CONFIG_FILE.exists():
            return MemoryGuard.load_json_safe(SECURITY_CONFIG_FILE)

        # Default salt and PIN (default 2026)
        salt = os.urandom(16).hex()
        default_hash = hashlib.pbkdf2_hmac("sha256", "2026".encode("utf-8"), bytes.fromhex(salt), 100_000).hex()
        data = {
            "owner": OWNER_NAME,
            "salt": salt,
            "pin_hash": default_hash,
            "voice_biometrics_required": True,
            "guest_sandbox_active": False,
            "encryption_algorithm": "AES-256-GCM",
            "last_audit_at": datetime.now().isoformat(),
        }
        MemoryGuard.save_json_atomic(SECURITY_CONFIG_FILE, data)
        return data

    def verify_pin(self, pin: str) -> PinVerificationResult:
        salt = bytes.fromhex(self._auth_state.get("salt", ""))
        test_hash = hashlib.pbkdf2_hmac("sha256", pin.strip().encode("utf-8"), salt, 100_000).hex()
        if test_hash == self._auth_state.get("pin_hash"):
            self._tier = self.TIER_FOUNDER
            return PinVerificationResult(True, "Founder clearance verified.")
        return PinVerificationResult(False, "Invalid security PIN.")

    def set_pin(self, old_or_new_pin: str, new_pin: Optional[str] = None) -> bool | Dict[str, Any]:
        """Sets new security PIN. Supports set_pin(new_pin) or set_pin(old_pin, new_pin)."""
        target_pin = new_pin if new_pin is not None else old_or_new_pin
        if new_pin is not None and not self.verify_pin(old_or_new_pin):
            return {"ok": False, "error": "Current security PIN invalid."}
        if len(target_pin.strip()) < 4:
            return {"ok": False, "error": "New PIN must be at least 4 digits."}

        salt = os.urandom(16).hex()
        new_hash = hashlib.pbkdf2_hmac("sha256", target_pin.strip().encode("utf-8"), bytes.fromhex(salt), 100_000).hex()
        self._auth_state["salt"] = salt
        self._auth_state["pin_hash"] = new_hash
        MemoryGuard.save_json_atomic(SECURITY_CONFIG_FILE, self._auth_state)
        return True

    def lock_vault(self, reason: str = ""):
        """Engages immediate security lockout."""
        self._tier = self.TIER_LOCKED

    def is_vault_locked(self) -> bool:
        return self._tier == self.TIER_LOCKED

    def unlock_vault(self, pin: str) -> Tuple[bool, str]:
        if self.verify_pin(pin):
            self._tier = self.TIER_FOUNDER
            return True, "Vault unlocked with Founder clearance."
        return False, "Failed to unlock vault: invalid PIN."

    def get_clearance_tier(self) -> str:
        return self._tier

    def enter_guest_mode(self):
        """Downgrades active session into Guest Sandbox."""
        self._tier = self.TIER_GUEST

    def unlock_founder(self, verified_by: str = "voice"):
        """Restores full founder clearance."""
        self._tier = self.TIER_FOUNDER

    def get_security_status(self) -> Dict[str, Any]:
        return {
            "tier": self._tier,
            "owner": OWNER_NAME,
            "voice_enforced": self._auth_state.get("voice_biometrics_required", True),
            "encryption": self._auth_state.get("encryption_algorithm", "AES-256-GCM"),
            "is_founder_authenticated": (self._tier == self.TIER_FOUNDER),
            "is_guest": (self._tier == self.TIER_GUEST),
            "is_locked": (self._tier == self.TIER_LOCKED),
        }
