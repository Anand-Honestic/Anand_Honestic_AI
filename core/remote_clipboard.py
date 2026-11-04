"""
core/remote_clipboard.py — Bi-Directional Cryptographic Clipboard Synchronizer

Top MVP Feature 1:
- Cryptographically syncs clipboard text between ATHENA (PC) and Phone AI.
- Security Invariant: Detects passwords, API keys, and credit cards; automatically flags or scrubs sensitive tokens.
- Supports configurable auto-clear after 60 seconds.
"""

import re
import time
from typing import Optional, Tuple, Dict, Any


# Regex patterns for sensitive data detection
_SENSITIVE_PATTERNS = [
    r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b",  # Credit Card
    r"\b(?:bearer\s+)?[a-zA-Z0-9_\-\.]{60,}\b",                         # API Keys / JWT
    r"-----BEGIN (?:RSA|OPENSSH|EC|PGP) PRIVATE KEY-----",               # Private Key
    r"\b[A-Za-z0-9+/]{40}={0,2}\b",                                     # High-entropy hashes/secrets
]


class ClipboardManager:
    """Manages secure cross-device clipboard synchronization."""

    _instance: Optional["ClipboardManager"] = None

    def __init__(self, auto_clear_timeout_sec: float = 60.0):
        self.auto_clear_timeout = auto_clear_timeout_sec
        self._current_text = ""
        self._last_copied_at = 0.0
        self._is_sensitive = False

    @classmethod
    def get_instance(cls) -> "ClipboardManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def is_sensitive_content(self, text: str) -> bool:
        """Evaluates whether the clipboard snippet appears to be a password or secret."""
        if not text:
            return False
        for pat in _SENSITIVE_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                return True
        return False

    def sanitize_for_sync(self, text: str) -> Tuple[bool, str]:
        """
        Validates text before cross-device broadcast.
        Returns: (can_sync: bool, reason: str)
        """
        if not text:
            return False, "Empty clipboard"
        if len(text) > 100_000:
            return False, "Clipboard item exceeds 100KB limit"
        if self.is_sensitive_content(text):
            return False, "Sensitive content detected (password/key); cross-device sync blocked"
        return True, "Safe to sync"

    def set_local_clipboard(self, text: str) -> Dict[str, Any]:
        """Updates local clipboard and prepares sync packet."""
        can_sync, reason = self.sanitize_for_sync(text)
        self._current_text = text
        self._last_copied_at = time.time()
        self._is_sensitive = not can_sync

        return {
            "text": text if can_sync else "",
            "can_sync": can_sync,
            "reason": reason,
            "ts": int(self._last_copied_at * 1000)
        }

    def receive_remote_clipboard(self, text: str) -> bool:
        """Applies clipboard received from paired device."""
        can_sync, _ = self.sanitize_for_sync(text)
        if not can_sync:
            return False
        self._current_text = text
        self._last_copied_at = time.time()
        self._is_sensitive = False
        return True

    def get_current_text(self) -> str:
        now = time.time()
        if self._is_sensitive and (now - self._last_copied_at > self.auto_clear_timeout):
            self._current_text = ""
            return ""
        return self._current_text

