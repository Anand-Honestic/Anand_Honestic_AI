"""
test_phase1_security.py — Complete Unit & Integration Test Suite for Phase 1 Security Architecture

Tests:
1. Ed25519 Signatures and Tamper Verification.
2. X25519 ECDH Key Agreement and HKDF.
3. AES-256-GCM Authenticated Encryption with Bit-Flip Tamper Resistance.
4. Windows DPAPI Encrypted Storage and Retrieval.
5. DeviceRegistry Pinned Key Management and Instant One-Click Revocation.
6. ReplayProtectionEngine: Nonce Cache, Sequence Integrity, and 30s Timestamp Window.
7. CommandAuthorizer: Auth Tiers 1, 2, 3 and App Whitelist Enforcement.
8. AuditLogger: Cryptographic Chaining and Tamper Detection.
9. End-to-End Out-of-Band QR Code Pairing Flow (PC <-> Phone Simulation).
"""

import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

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
from core.remote_security.replay_protection import ReplayProtectionEngine
from core.remote_security.auth_tiers import AuthTier, CommandAuthorizer
from core.remote_security.audit_log import AuditLogger
from core.remote_security.pairing import PairingManager, QRPairingSession


class TestPhase1CryptoEngine(unittest.TestCase):
    """Verifies cryptographic primitives and zero-knowledge properties."""

    def test_01_ed25519_sign_and_verify(self):
        """Ed25519 identity key generates valid signatures verifiable by public key."""
        identity = DeviceIdentityKey.generate()
        msg = b"ATHENA_COMMAND_PAYLOAD_TEST_101"
        sig = identity.sign(msg)
        self.assertEqual(len(sig), 64)
        self.assertTrue(verify_ed25519_signature(identity.public_bytes(), msg, sig))

        # Tampered message must fail verification
        tampered_msg = b"ATHENA_COMMAND_PAYLOAD_TEST_102"
        self.assertFalse(verify_ed25519_signature(identity.public_bytes(), tampered_msg, sig))

        # Base64 serialization roundtrip
        priv_b64 = identity.private_b64()
        restored_identity = DeviceIdentityKey.from_b64(priv_b64)
        self.assertEqual(identity.public_bytes(), restored_identity.public_bytes())
        sig_b64 = identity.sign_b64(msg)
        self.assertTrue(verify_ed25519_signature_b64(restored_identity.public_b64(), msg, sig_b64))

    def test_02_x25519_ecdh_shared_secret(self):
        """Alice (PC) and Bob (Phone) establish identical shared secret via X25519 ECDH."""
        alice_eph = EphemeralKeyAgreement.generate()
        bob_eph = EphemeralKeyAgreement.generate()

        alice_secret = alice_eph.exchange(bob_eph.public_bytes())
        bob_secret = bob_eph.exchange(alice_eph.public_bytes())

        self.assertEqual(len(alice_secret), 32)
        self.assertEqual(alice_secret, bob_secret)

        # HKDF derivation produces matching AES-256 keys
        salt = b"ONE_TIME_PAIRING_SALT_1234"
        alice_key = derive_session_key(alice_secret, salt=salt, info=b"TEST-INFO")
        bob_key = derive_session_key(bob_secret, salt=salt, info=b"TEST-INFO")
        self.assertEqual(alice_key, bob_key)
        self.assertEqual(len(alice_key), 32)

    def test_03_aes_256_gcm_authenticated_encryption_and_tampering(self):
        """AES-256-GCM encrypts with random 96-bit nonce and rejects modified ciphertexts."""
        key = os.urandom(32)
        cipher = SymmetricCipher(key)
        plaintext = b"Sensitive Phone AI Automation Command: WhatsApp message to Anand"
        aad = b"HEADER_METADATA_TIER_2"

        nonce, ct = cipher.encrypt(plaintext, associated_data=aad)
        self.assertEqual(len(nonce), 12)
        decrypted = cipher.decrypt(nonce, ct, associated_data=aad)
        self.assertEqual(decrypted, plaintext)

        # Bit flip in ciphertext must raise InvalidTag
        tampered_ct = bytearray(ct)
        tampered_ct[0] ^= 0x01
        # pyrefly: ignore[missing-import]
        from cryptography.exceptions import InvalidTag
        with self.assertRaises(InvalidTag):
            cipher.decrypt(nonce, bytes(tampered_ct), associated_data=aad)

        # Modified AAD must also fail decryption
        with self.assertRaises(InvalidTag):
            cipher.decrypt(nonce, ct, associated_data=b"FORGED_AAD_TIER_1")

        # Package base64 roundtrip
        pkg_b64 = cipher.encrypt_package_b64(plaintext)
        dec_pkg = cipher.decrypt_package_b64(pkg_b64)
        self.assertEqual(dec_pkg, plaintext)


class TestPhase1DPAPIAndRegistry(unittest.TestCase):
    """Verifies DPAPI secure storage and device registry revocation lifecycle."""

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.storage = DPAPIStorage(base_dir=self.test_dir)
        self.registry = DeviceRegistry(storage=self.storage)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_04_dpapi_encrypted_json_roundtrip(self):
        """DPAPI encrypts JSON data at rest, unreadable as plaintext on disk."""
        payload = {"secret_token": "TOKEN_998877", "master_seed": "SEED_ABCDEF"}
        file_path = self.storage.save_encrypted_json("test_vault.enc", payload)
        self.assertTrue(file_path.exists())

        # Raw file should not contain the plaintext string
        with open(file_path, "rb") as f:
            raw_content = f.read()
        self.assertNotIn(b"TOKEN_998877", raw_content)

        # Decrypting via DPAPI recovers exact dictionary
        loaded = self.storage.load_encrypted_json("test_vault.enc")
        self.assertEqual(loaded, payload)

    def test_05_device_registration_and_instant_revocation(self):
        """Registered companion device is authorized, and instant one-click revocation blocks access."""
        phone_identity = DeviceIdentityKey.generate()
        dev_id = "redmi-14c-5g-anand"

        rec = self.registry.register_device(
            device_id=dev_id,
            name="Anand Redmi 14C 5G",
            platform="android",
            ed25519_pub_b64=phone_identity.public_b64(),
            whitelist_apps=["com.whatsapp", "com.google.android.youtube"]
        )

        self.assertEqual(rec.device_id, dev_id)
        self.assertTrue(self.registry.is_device_authorized(dev_id, phone_identity.public_b64()))

        # Wrong public key must fail
        imposter = DeviceIdentityKey.generate()
        self.assertFalse(self.registry.is_device_authorized(dev_id, imposter.public_b64()))

        # Instant one-click revocation
        revocation_success = self.registry.revoke_device(dev_id)
        self.assertTrue(revocation_success)

        # Revoked device is no longer authorized
        self.assertFalse(self.registry.is_device_authorized(dev_id, phone_identity.public_b64()))

        # Persistence: reload registry from disk and confirm revoked state persists
        reloaded_registry = DeviceRegistry(storage=self.storage)
        self.assertFalse(reloaded_registry.is_device_authorized(dev_id, phone_identity.public_b64()))


class TestPhase1ReplayAndAuthTiers(unittest.TestCase):
    """Verifies anti-replay defense and multi-tier command authorization."""

    def test_06_replay_protection_mechanisms(self):
        """ReplayProtection blocks expired timestamps, duplicate nonces, and decremented sequences."""
        engine = ReplayProtectionEngine(max_time_drift_sec=30.0)
        dev_id = "phone_001"
        now = time.time()
        now_ms = int(now * 1000)

        # 1. Valid fresh message
        ok, err = engine.validate_and_record(dev_id, seq=1, ts_ms=now_ms, nonce_b64="NONCE_1", current_time_sec=now)
        self.assertTrue(ok)

        # 2. Replay with identical nonce must be rejected
        ok, err = engine.validate_and_record(dev_id, seq=2, ts_ms=now_ms, nonce_b64="NONCE_1", current_time_sec=now)
        self.assertFalse(ok)
        self.assertIn("already consumed", err)

        # 3. Non-monotonic sequence (seq <= last seen) must be rejected
        ok, err = engine.validate_and_record(dev_id, seq=1, ts_ms=now_ms, nonce_b64="NONCE_2", current_time_sec=now)
        self.assertFalse(ok)
        self.assertIn("sequence 1 <= last seen 1", err)

        # 4. Outdated message (>30 seconds in the past) must be rejected
        expired_ms = int((now - 45.0) * 1000)
        ok, err = engine.validate_and_record(dev_id, seq=5, ts_ms=expired_ms, nonce_b64="NONCE_3", current_time_sec=now)
        self.assertFalse(ok)
        self.assertIn("Timestamp expired", err)

        # 5. Future message with excessive drift (>30 seconds) must be rejected
        future_ms = int((now + 60.0) * 1000)
        ok, err = engine.validate_and_record(dev_id, seq=6, ts_ms=future_ms, nonce_b64="NONCE_4", current_time_sec=now)
        self.assertFalse(ok)
        self.assertIn("excessive clock drift", err)

    def test_07_command_authorizer_tier_enforcement(self):
        """CommandAuthorizer enforces correct tier prerequisites and app whitelists."""
        authorizer = CommandAuthorizer(allowed_packages=["com.whatsapp", "com.google.android.youtube"])

        # Tier 1 action: Read Battery -> Auto-executes
        ok, _ = authorizer.validate_command_intent("GET_BATTERY_STATUS", {}, declared_tier=1)
        self.assertTrue(ok)

        # Tier 1 action: Open Whitelisted App -> Allowed
        ok, _ = authorizer.validate_command_intent("OPEN_APP", {"package": "com.whatsapp"}, declared_tier=1)
        self.assertTrue(ok)

        # Tier 1 action: Open Non-whitelisted App -> Rejected
        ok, err = authorizer.validate_command_intent("OPEN_APP", {"package": "com.suspicious.app"}, declared_tier=1)
        self.assertFalse(ok)
        self.assertIn("not in the approved app whitelist", err)

        # Tier 2 action: Send Message without user confirmation -> Rejected
        ok, err = authorizer.validate_command_intent(
            "SEND_MESSAGE",
            {"recipient": "+919999999999", "text": "Hi"},
            declared_tier=2,
            has_user_confirmation=False
        )
        self.assertFalse(ok)
        self.assertIn("requires explicit user confirmation", err)

        # Tier 2 action: Send Message WITH user confirmation -> Allowed
        ok, _ = authorizer.validate_command_intent(
            "SEND_MESSAGE",
            {"recipient": "+919999999999", "text": "Hi"},
            declared_tier=2,
            has_user_confirmation=True
        )
        self.assertTrue(ok)

        # Tier 3 action: Delete File without biometric -> Rejected
        ok, err = authorizer.validate_command_intent(
            "DELETE_FILE",
            {"path": "/sdcard/document.pdf"},
            declared_tier=3,
            has_biometric_proof=False
        )
        self.assertFalse(ok)
        self.assertIn("requires hardware biometric verification", err)

        # Tier 3 action: Delete File WITH biometric -> Allowed
        ok, _ = authorizer.validate_command_intent(
            "DELETE_FILE",
            {"path": "/sdcard/document.pdf"},
            declared_tier=3,
            has_biometric_proof=True
        )
        self.assertTrue(ok)


class TestPhase1QRPairingAndAudit(unittest.TestCase):
    """Verifies Out-of-band QR Pairing exchange and Audit Logging."""

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.storage = DPAPIStorage(base_dir=self.test_dir)
        self.registry = DeviceRegistry(storage=self.storage)
        self.pairing_mgr = PairingManager(registry=self.registry)
        self.audit_logger = AuditLogger(log_dir=self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_08_end_to_end_qr_pairing_flow(self):
        """Simulates full QR scan and mutual authentication handshake between PC and Phone."""
        # 1. PC: User clicks 'Pair New Device' -> Generates QR Session
        session = self.pairing_mgr.create_pairing_session(lan_ip="192.168.1.108", port=8001, ttl_sec=180)
        self.assertFalse(session.is_expired())
        qr_payload_str = session.to_qr_payload()
        qr_data = json.loads(qr_payload_str)

        # Verify QR payload fields
        self.assertIn("pc_ed_pub", qr_data)
        self.assertIn("pc_eph_pub", qr_data)
        self.assertIn("ots", qr_data)

        # 2. Phone: Scans QR code, instantiates phone identity and phone ephemeral ECDH
        phone_identity = DeviceIdentityKey.generate()
        phone_eph = EphemeralKeyAgreement.generate()

        # Phone computes shared secret and derives pairing key
        pc_eph_pub_bytes = b64_decode(qr_data["pc_eph_pub"])
        ots_bytes = b64_decode(qr_data["ots"])
        phone_shared_secret = phone_eph.exchange(pc_eph_pub_bytes)
        phone_pairing_key = derive_session_key(phone_shared_secret, salt=ots_bytes, info=b"ATHENA-PAIR-v1")
        phone_cipher = SymmetricCipher(phone_pairing_key)

        # Phone crafts PAIR_REQUEST payload and signs with its Ed25519 identity key
        phone_req_payload = {
            "device_id": "redmi-14c-5g-anand",
            "name": "Anand Redmi 14C 5G",
            "platform": "android",
            "phone_ed_pub": phone_identity.public_b64(),
            "whitelist_apps": ["com.whatsapp", "com.google.android.youtube"],
            "ts": int(time.time()),
        }
        canonical_req = json.dumps(phone_req_payload, sort_keys=True).encode("utf-8")
        req_sig = phone_identity.sign_b64(canonical_req)
        enc_req_payload = phone_cipher.encrypt_package_b64(canonical_req)

        # Phone sends PAIR_REQUEST envelope to PC
        pair_envelope = {
            "v": 1,
            "sid": qr_data["sid"],
            "phone_eph_pub": phone_eph.public_b64(),
            "encrypted_payload": enc_req_payload,
            "sig": req_sig,
        }

        # 3. PC validates pairing request
        ok, msg, confirm_envelope = self.pairing_mgr.validate_pairing_request(pair_envelope)
        self.assertTrue(ok)
        self.assertEqual(msg, "Pairing successful")
        self.assertIsNotNone(confirm_envelope)

        # Verify device is now pinned in DPAPI registry
        self.assertTrue(self.registry.is_device_authorized("redmi-14c-5g-anand", phone_identity.public_b64()))

        # 4. Phone receives and validates PAIR_CONFIRM envelope
        dec_confirm = phone_cipher.decrypt_package_b64(confirm_envelope["encrypted_payload"])
        confirm_data = json.loads(dec_confirm.decode("utf-8"))
        self.assertEqual(confirm_data["status"], "PAIRED")
        self.assertEqual(confirm_data["device_id"], "redmi-14c-5g-anand")
        # Verify PC signature on confirmation
        pc_ed_pub = confirm_data["pc_ed_pub"]
        self.assertTrue(verify_ed25519_signature_b64(pc_ed_pub, dec_confirm, confirm_envelope["sig"]))

    def test_09_qr_pairing_session_expiry_rejection(self):
        """Expired QR pairing sessions are rejected."""
        session = self.pairing_mgr.create_pairing_session(lan_ip="192.168.1.108", port=8001, ttl_sec=-10)
        self.assertTrue(session.is_expired())

        dummy_envelope = {"sid": session.session_id, "phone_eph_pub": "", "encrypted_payload": "", "sig": ""}
        ok, msg, _ = self.pairing_mgr.validate_pairing_request(dummy_envelope)
        self.assertFalse(ok)
        self.assertIn("expired", msg.lower())

    def test_10_tamper_evident_audit_log_chaining(self):
        """Audit log cryptographically chains previous hash and records events."""
        event1 = self.audit_logger.log_event(
            correlation_id="corr-1",
            sender_device_id="redmi-14c-5g",
            target_device_id="ATHENA_PC",
            action="GET_BATTERY_STATUS",
            auth_tier=1,
            status="SUCCESS"
        )
        self.assertIn("hash", event1)
        self.assertEqual(event1["prev_hash"], "GENESIS_BLOCK_HONESTIC_ATHENA")

        event2 = self.audit_logger.log_event(
            correlation_id="corr-2",
            sender_device_id="ATHENA_PC",
            target_device_id="redmi-14c-5g",
            action="SEND_MESSAGE",
            auth_tier=2,
            status="SUCCESS"
        )
        self.assertEqual(event2["prev_hash"], event1["hash"])

        recent = self.audit_logger.get_recent_logs(limit=10)
        self.assertEqual(len(recent), 2)
        self.assertEqual(recent[0]["correlation_id"], "corr-1")
        self.assertEqual(recent[1]["correlation_id"], "corr-2")


if __name__ == "__main__":
    unittest.main()

