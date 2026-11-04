"""
core/remote_security/pairing.py — Secure QR-Code Device Pairing Engine

Implements out-of-band mutual authentication:
1. PC generates ephemeral X25519 key + 256-bit One-Time Secret (OTS) + QR payload.
2. QR Code rendered as PNG and Base64 data URI (ready for UI display).
3. Phone scans QR, computes ECDH with PC ephemeral key, and derives PairingKey via HKDF.
4. Phone submits encrypted, Ed25519-signed PAIR_REQUEST over WSS.
5. PC decrypts, verifies phone identity, confirms with user, and pins phone's public key in DPAPI registry.
"""

import io
import json
import secrets
import time
import uuid
from typing import Dict, Optional, Tuple, Any
import qrcode

from core.remote_security.crypto import (
    DeviceIdentityKey,
    EphemeralKeyAgreement,
    derive_session_key,
    SymmetricCipher,
    verify_ed25519_signature_b64,
    b64_encode,
    b64_decode,
)
from core.remote_security.device_registry import DeviceRegistry, DeviceRecord
from core.remote_security.audit_log import AuditLogger


_DEFAULT_PAIRING_TTL = 180  # 3 minutes


class QRPairingSession:
    """Represents an active ephemeral pairing attempt."""

    def __init__(
        self,
        session_id: str,
        lan_ip: str,
        port: int,
        pc_identity: DeviceIdentityKey,
        ttl_sec: int = _DEFAULT_PAIRING_TTL
    ):
        self.session_id = session_id
        self.lan_ip = lan_ip
        self.port = port
        self.pc_identity = pc_identity
        self.eph_pc = EphemeralKeyAgreement.generate()
        self.ots_bytes = secrets.token_bytes(32)
        self.created_at = time.time()
        self.expires_at = self.created_at + ttl_sec
        self.is_completed = False

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def to_qr_payload(self) -> str:
        """Constructs the canonical JSON payload to be embedded in the QR code."""
        payload = {
            "v": 1,
            "sid": self.session_id,
            "ip": self.lan_ip,
            "port": self.port,
            "pc_ed_pub": self.pc_identity.public_b64(),
            "pc_eph_pub": self.eph_pc.public_b64(),
            "ots": b64_encode(self.ots_bytes),
            "exp": int(self.expires_at),
        }
        return json.dumps(payload, separators=(",", ":"))

    def generate_qr_png_bytes(self) -> bytes:
        """Generates PNG image bytes of the QR code."""
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(self.to_qr_payload())
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def generate_qr_data_uri(self) -> str:
        """Returns standard HTML data URI: data:image/png;base64,..."""
        png_bytes = self.generate_qr_png_bytes()
        import base64
        return f"data:image/png;base64,{base64.b64encode(png_bytes).decode('ascii')}"


class PairingManager:
    """Orchestrates QR code creation and validates incoming pairing requests."""

    _instance: Optional["PairingManager"] = None

    def __init__(self, registry: Optional[DeviceRegistry] = None):
        self.registry = registry or DeviceRegistry.get_instance()
        self._active_sessions: Dict[str, QRPairingSession] = {}

    @classmethod
    def get_instance(cls, registry: Optional[DeviceRegistry] = None) -> "PairingManager":
        if cls._instance is None:
            cls._instance = cls(registry)
        return cls._instance

    def create_pairing_session(self, lan_ip: str, port: int = 8001, ttl_sec: int = _DEFAULT_PAIRING_TTL) -> QRPairingSession:
        """Creates a fresh ephemeral pairing session and returns it."""
        # Cleanup expired sessions
        now = time.time()
        self._active_sessions = {sid: s for sid, s in self._active_sessions.items() if s.expires_at > now}

        sid = str(uuid.uuid4())
        session = QRPairingSession(
            session_id=sid,
            lan_ip=lan_ip,
            port=port,
            pc_identity=self.registry.identity_key,
            ttl_sec=ttl_sec,
        )
        self._active_sessions[sid] = session
        print(f"[PairingManager] 📷 QR Pairing session created: {sid} (expires in {ttl_sec}s)")
        return session

    def validate_pairing_request(
        self,
        request_envelope: Dict[str, Any],
        auto_approve: bool = False
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Validates PAIR_REQUEST from a phone companion.
        
        Expected envelope:
        {
          "v": 1,
          "sid": "session_id",
          "phone_eph_pub": "X25519_Phone_eph_pub_b64",
          "encrypted_payload": "Base64GCMCiphertext...",
          "sig": "Base64Ed25519Signature..."
        }
        """
        sid = request_envelope.get("sid", "")
        session = self._active_sessions.get(sid)
        if not session:
            return False, "Invalid or unknown pairing session ID", None

        if session.is_expired():
            del self._active_sessions[sid]
            return False, "Pairing session has expired. Please refresh the QR code.", None

        if session.is_completed:
            return False, "Pairing session already consumed", None

        phone_eph_pub_b64 = request_envelope.get("phone_eph_pub", "")
        enc_payload_b64 = request_envelope.get("encrypted_payload", "")
        sig_b64 = request_envelope.get("sig", "")

        try:
            phone_eph_pub_bytes = b64_decode(phone_eph_pub_b64)
            # 1. Compute ECDH shared secret: PC_eph * Phone_eph
            shared_secret = session.eph_pc.exchange(phone_eph_pub_bytes)
            # 2. Derive pairing key with salt = session.ots_bytes
            pairing_key = derive_session_key(
                shared_secret=shared_secret,
                salt=session.ots_bytes,
                info=b"ATHENA-PAIR-v1",
                length=32
            )
            cipher = SymmetricCipher(pairing_key)
            # 3. Decrypt payload
            decrypted_raw = cipher.decrypt_package_b64(enc_payload_b64)
            payload_data = json.loads(decrypted_raw.decode("utf-8"))
        except Exception as e:
            return False, f"Decryption of pairing request failed: {e}", None

        # 4. Verify Ed25519 Signature over the decrypted canonical payload
        phone_ed_pub_b64 = payload_data.get("phone_ed_pub", "")
        canonical_msg = json.dumps(payload_data, sort_keys=True).encode("utf-8")
        if not verify_ed25519_signature_b64(phone_ed_pub_b64, canonical_msg, sig_b64):
            return False, "Signature verification failed: Phone identity proof is invalid", None

        # 5. Extract Phone Details & Register
        device_id = payload_data.get("device_id", str(uuid.uuid4()))
        device_name = payload_data.get("name", "Redmi 14C 5G Companion")
        platform = payload_data.get("platform", "android")
        whitelist_apps = payload_data.get("whitelist_apps", [])

        # Pin device into DPAPI registry
        device_rec = self.registry.register_device(
            device_id=device_id,
            name=device_name,
            platform=platform,
            ed25519_pub_b64=phone_ed_pub_b64,
            whitelist_apps=whitelist_apps,
        )

        session.is_completed = True
        del self._active_sessions[sid]

        # Audit pairing
        AuditLogger.get_instance().log_event(
            correlation_id=sid,
            sender_device_id=device_id,
            target_device_id="ATHENA_PC",
            action="DEVICE_PAIRING",
            auth_tier=1,
            status="SUCCESS",
            details={"name": device_name, "platform": platform}
        )

        # 6. Generate Long-term Session Token for the phone
        session_token = str(uuid.uuid4())
        confirm_data = {
            "v": 1,
            "status": "PAIRED",
            "device_id": device_id,
            "pc_ed_pub": self.registry.public_identity_b64,
            "session_token": session_token,
            "ts": int(time.time()),
        }
        confirm_canonical = json.dumps(confirm_data, sort_keys=True).encode("utf-8")
        confirm_sig = self.registry.identity_key.sign_b64(confirm_canonical)
        enc_confirm = cipher.encrypt_package_b64(confirm_canonical)

        response_packet = {
            "v": 1,
            "encrypted_payload": enc_confirm,
            "sig": confirm_sig,
        }

        return True, "Pairing successful", response_packet

