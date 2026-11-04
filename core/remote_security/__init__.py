"""
core/remote_security package — Cryptographic security, pairing, and access control for ATHENA and Phone AI.
"""

from core.remote_security.crypto import (
    DeviceIdentityKey,
    EphemeralKeyAgreement,
    SymmetricCipher,
    derive_session_key,
    verify_ed25519_signature,
    verify_ed25519_signature_b64,
    b64_encode,
    b64_decode,
)
from core.remote_security.dpapi_storage import DPAPIStorage
from core.remote_security.device_registry import DeviceRegistry, DeviceRecord
from core.remote_security.auth_tiers import AuthTier, CommandAuthorizer, DEFAULT_ALLOWED_PACKAGES
from core.remote_security.replay_protection import ReplayProtectionEngine
from core.remote_security.pairing import PairingManager, QRPairingSession
from core.remote_security.audit_log import AuditLogger

__all__ = [
    "DeviceIdentityKey",
    "EphemeralKeyAgreement",
    "SymmetricCipher",
    "derive_session_key",
    "verify_ed25519_signature",
    "verify_ed25519_signature_b64",
    "b64_encode",
    "b64_decode",
    "DPAPIStorage",
    "DeviceRegistry",
    "DeviceRecord",
    "AuthTier",
    "CommandAuthorizer",
    "DEFAULT_ALLOWED_PACKAGES",
    "ReplayProtectionEngine",
    "PairingManager",
    "QRPairingSession",
    "AuditLogger",
]

