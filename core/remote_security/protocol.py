"""
core/remote_security/protocol.py — End-to-End Encrypted Binary/JSON Wire Protocol

Handles:
1. Packaging plaintext command dicts into signed, encrypted, replay-protected wire packets.
2. Unpacking, validating signatures, checking replay protection, and decrypting incoming wire packets.
3. Protocol versioning (v1).
"""

import json
import time
import uuid
from typing import Dict, Any, Optional, Tuple

from core.remote_security.crypto import (
    DeviceIdentityKey,
    SymmetricCipher,
    verify_ed25519_signature_b64,
    b64_encode,
    b64_decode,
)
from core.remote_security.replay_protection import ReplayProtectionEngine


PROTOCOL_VERSION = 1


class SecureFrame:
    """Represents a validated, decrypted cross-device message."""

    def __init__(
        self,
        msg_id: str,
        seq: int,
        ts_ms: int,
        sender_id: str,
        recipient_id: str,
        auth_tier: int,
        payload: Dict[str, Any],
        raw_envelope: Dict[str, Any]
    ):
        self.msg_id = msg_id
        self.seq = seq
        self.ts_ms = ts_ms
        self.sender_id = sender_id
        self.recipient_id = recipient_id
        self.auth_tier = auth_tier
        self.payload = payload
        self.raw_envelope = raw_envelope


class ProtocolEngine:
    """Packs and unpacks secure wire frames according to the HONESTIC OS protocol spec."""

    def __init__(
        self,
        local_device_id: str,
        identity_key: DeviceIdentityKey,
        replay_engine: Optional[ReplayProtectionEngine] = None
    ):
        self.local_device_id = local_device_id
        self.identity_key = identity_key
        self.replay_engine = replay_engine or ReplayProtectionEngine()
        self._current_seq = 0

    def get_next_seq(self) -> int:
        self._current_seq += 1
        return self._current_seq

    def pack_message(
        self,
        recipient_id: str,
        payload_dict: Dict[str, Any],
        symmetric_cipher: SymmetricCipher,
        auth_tier: int = 1,
        msg_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Packs a plaintext command dictionary into an authenticated, encrypted wire envelope.
        """
        msg_id = msg_id or str(uuid.uuid4())
        seq = self.get_next_seq()
        ts_ms = int(time.time() * 1000)

        # 1. Encrypt payload with AES-256-GCM
        payload_bytes = json.dumps(payload_dict, sort_keys=True).encode("utf-8")
        nonce, ciphertext = symmetric_cipher.encrypt(payload_bytes)
        nonce_b64 = b64_encode(nonce)
        enc_payload_b64 = b64_encode(ciphertext)

        # 2. Build header envelope to sign
        header_to_sign = {
            "v": PROTOCOL_VERSION,
            "id": msg_id,
            "seq": seq,
            "ts": ts_ms,
            "sender": self.local_device_id,
            "recipient": recipient_id,
            "nonce": nonce_b64,
            "auth_tier": auth_tier,
            "encrypted_payload": enc_payload_b64,
        }
        canonical_header = json.dumps(header_to_sign, sort_keys=True).encode("utf-8")

        # 3. Generate Ed25519 digital signature over canonical header + ciphertext
        sig_b64 = self.identity_key.sign_b64(canonical_header)
        header_to_sign["sig"] = sig_b64

        return header_to_sign

    def unpack_message(
        self,
        envelope: Dict[str, Any],
        sender_ed25519_pub_b64: str,
        symmetric_cipher: SymmetricCipher
    ) -> Tuple[bool, str, Optional[SecureFrame]]:
        """
        Unpacks and validates an incoming wire envelope:
        1. Checks protocol version.
        2. Validates Ed25519 digital signature.
        3. Validates replay protection (timestamp drift, duplicate nonce, monotonic sequence).
        4. Decrypts AES-256-GCM payload.
        Returns: (success: bool, error_reason: str, secure_frame: Optional[SecureFrame])
        """
        if envelope.get("v") != PROTOCOL_VERSION:
            return False, f"Unsupported protocol version: {envelope.get('v')}", None

        sig_b64 = envelope.get("sig", "")
        if not sig_b64:
            return False, "Missing cryptographic signature in envelope", None

        # Prepare envelope for signature verification by excluding 'sig'
        envelope_copy = dict(envelope)
        envelope_copy.pop("sig", None)
        canonical_header = json.dumps(envelope_copy, sort_keys=True).encode("utf-8")

        if not verify_ed25519_signature_b64(sender_ed25519_pub_b64, canonical_header, sig_b64):
            return False, "Digital signature verification failed: packet altered or forged", None

        sender_id = envelope.get("sender", "")
        seq = envelope.get("seq", 0)
        ts_ms = envelope.get("ts", 0)
        nonce_b64 = envelope.get("nonce", "")

        # Replay protection check
        is_fresh, replay_err = self.replay_engine.validate_and_record(
            device_id=sender_id,
            seq=seq,
            ts_ms=ts_ms,
            nonce_b64=nonce_b64
        )
        if not is_fresh:
            return False, f"Replay defense rejected message: {replay_err}", None

        # Decrypt payload
        try:
            nonce = b64_decode(nonce_b64)
            ciphertext = b64_decode(envelope.get("encrypted_payload", ""))
            plaintext_bytes = symmetric_cipher.decrypt(nonce, ciphertext)
            payload_dict = json.loads(plaintext_bytes.decode("utf-8"))
        except Exception as e:
            return False, f"Payload decryption failed: {e}", None

        frame = SecureFrame(
            msg_id=envelope.get("id", ""),
            seq=seq,
            ts_ms=ts_ms,
            sender_id=sender_id,
            recipient_id=envelope.get("recipient", ""),
            auth_tier=envelope.get("auth_tier", 1),
            payload=payload_dict,
            raw_envelope=envelope
        )
        return True, "OK", frame

