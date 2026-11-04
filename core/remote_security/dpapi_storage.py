"""
core/remote_security/dpapi_storage.py — Secure Storage via Windows DPAPI

Provides hardware-bound encrypted persistent storage for:
- ATHENA's master Ed25519 identity private key.
- Pinned paired phone keys and device registry.
- One-time secrets and active session credentials.
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional, Any, Dict

# Platform detection
_HAS_WIN32CRYPT = False
if sys.platform == "win32":
    try:
        import win32crypt
        _HAS_WIN32CRYPT = True
    except ImportError:
        pass


class DPAPIStorage:
    """Manages encrypted data at rest using Windows DPAPI (CryptProtectData)."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or (Path(__file__).resolve().parent.parent.parent / "data" / "secure_vault")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def protect_bytes(self, plaintext: bytes, description: str = "HONESTIC-OS-ATHENA") -> bytes:
        """Encrypts data using current Windows user's DPAPI credentials."""
        if not plaintext:
            return b""
        if _HAS_WIN32CRYPT:
            # win32crypt.CryptProtectData(data, description, optionalEntropy, reserved, promptStruct, flags)
            return win32crypt.CryptProtectData(plaintext, description, None, None, None, 0)
        else:
            # Non-Windows or testing fallback (obfuscation layer for local testing environments)
            import base64
            return b"PLAINTEXT_FALLBACK:" + base64.b64encode(plaintext)

    def unprotect_bytes(self, ciphertext: bytes) -> bytes:
        """Decrypts data previously encrypted by this Windows user."""
        if not ciphertext:
            return b""
        if _HAS_WIN32CRYPT and not ciphertext.startswith(b"PLAINTEXT_FALLBACK:"):
            _, data = win32crypt.CryptUnprotectData(ciphertext, None, None, None, 0)
            return data
        else:
            import base64
            if ciphertext.startswith(b"PLAINTEXT_FALLBACK:"):
                return base64.b64decode(ciphertext[len(b"PLAINTEXT_FALLBACK:"):])
            return ciphertext

    def save_encrypted_json(self, filename: str, data: Dict[str, Any]) -> Path:
        """Serializes dictionary to JSON and encrypts with DPAPI before writing to disk."""
        target_path = self.base_dir / filename
        payload_bytes = json.dumps(data, indent=2, sort_keys=True).encode("utf-8")
        encrypted = self.protect_bytes(payload_bytes, description=f"ATHENA:{filename}")
        temp_path = self.base_dir / f"{filename}.tmp"
        with open(temp_path, "wb") as f:
            f.write(encrypted)
        temp_path.replace(target_path)
        return target_path

    def load_encrypted_json(self, filename: str) -> Optional[Dict[str, Any]]:
        """Reads encrypted file from disk, decrypts via DPAPI, and parses JSON."""
        target_path = self.base_dir / filename
        if not target_path.exists():
            return None
        try:
            with open(target_path, "rb") as f:
                ciphertext = f.read()
            if not ciphertext:
                return None
            decrypted = self.unprotect_bytes(ciphertext)
            return json.loads(decrypted.decode("utf-8"))
        except Exception as e:
            print(f"[DPAPIStorage] ⚠️ Failed to decrypt {filename}: {e}")
            return None

    def delete_secure_file(self, filename: str) -> bool:
        target_path = self.base_dir / filename
        if target_path.exists():
            try:
                target_path.unlink()
                return True
            except OSError:
                return False
        return False

