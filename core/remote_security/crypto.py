"""
core/remote_security/crypto.py — Cryptographic Engine for HONESTIC OS & Phone AI

Implements:
1. Ed25519 Digital Signatures for mutual device identity & frame authentication.
2. X25519 ECDH Key Agreement for zero-knowledge forward-secure session keys.
3. HKDF-SHA256 (RFC 5869) key derivation.
4. AES-256-GCM authenticated symmetric encryption with unique 96-bit nonces.
5. Base64 URL-safe encoding/decoding utilities.
"""

import base64
import os
import secrets
from typing import Tuple, Optional
from cryptography.hazmat.primitives.asymmetric import ed25519, x25519
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidSignature, InvalidTag


# ── Base64 Serialization Helpers ───────────────────────────────────────────────

def b64_encode(data: bytes) -> str:
    """Encode bytes to URL-safe ASCII base64 without padding."""
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def b64_decode(data_str: str) -> bytes:
    """Decode URL-safe base64 string handling missing padding."""
    padding = len(data_str) % 4
    if padding:
        data_str += "=" * (4 - padding)
    return base64.urlsafe_b64decode(data_str.encode("ascii"))


# ── Ed25519 Device Identity & Signatures ───────────────────────────────────────

class DeviceIdentityKey:
    """Ed25519 private/public keypair representing a device's permanent identity."""

    def __init__(self, private_key: Optional[ed25519.Ed25519PrivateKey] = None):
        self._private_key = private_key or ed25519.Ed25519PrivateKey.generate()
        self._public_key = self._private_key.public_key()

    @classmethod
    def generate(cls) -> "DeviceIdentityKey":
        return cls(ed25519.Ed25519PrivateKey.generate())

    @classmethod
    def from_bytes(cls, private_bytes: bytes) -> "DeviceIdentityKey":
        if len(private_bytes) != 32:
            raise ValueError(f"Ed25519 private key must be exactly 32 bytes, got {len(private_bytes)}")
        priv = ed25519.Ed25519PrivateKey.from_private_bytes(private_bytes)
        return cls(priv)

    @classmethod
    def from_b64(cls, b64_str: str) -> "DeviceIdentityKey":
        return cls.from_bytes(b64_decode(b64_str))

    def private_bytes(self) -> bytes:
        from cryptography.hazmat.primitives import serialization
        return self._private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )

    def public_bytes(self) -> bytes:
        from cryptography.hazmat.primitives import serialization
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    def private_b64(self) -> str:
        return b64_encode(self.private_bytes())

    def public_b64(self) -> str:
        return b64_encode(self.public_bytes())

    def sign(self, message: bytes) -> bytes:
        """Sign a message and return the 64-byte Ed25519 signature."""
        return self._private_key.sign(message)

    def sign_b64(self, message: bytes) -> str:
        return b64_encode(self.sign(message))


def verify_ed25519_signature(public_bytes: bytes, message: bytes, signature: bytes) -> bool:
    """Verify an Ed25519 signature against the sender's public key bytes."""
    if len(public_bytes) != 32 or len(signature) != 64:
        return False
    try:
        pub = ed25519.Ed25519PublicKey.from_public_bytes(public_bytes)
        pub.verify(signature, message)
        return True
    except (InvalidSignature, ValueError):
        return False


def verify_ed25519_signature_b64(public_b64_str: str, message: bytes, signature_b64_str: str) -> bool:
    try:
        pub_b = b64_decode(public_b64_str)
        sig_b = b64_decode(signature_b64_str)
        return verify_ed25519_signature(pub_b, message, sig_b)
    except Exception:
        return False


# ── X25519 Key Agreement (ECDH) & HKDF ─────────────────────────────────────────

class EphemeralKeyAgreement:
    """X25519 Ephemeral keypair for forward-secure Diffie-Hellman key exchange."""

    def __init__(self, private_key: Optional[x25519.X25519PrivateKey] = None):
        self._private_key = private_key or x25519.X25519PrivateKey.generate()
        self._public_key = self._private_key.public_key()

    @classmethod
    def generate(cls) -> "EphemeralKeyAgreement":
        return cls(x25519.X25519PrivateKey.generate())

    @classmethod
    def from_bytes(cls, private_bytes: bytes) -> "EphemeralKeyAgreement":
        if len(private_bytes) != 32:
            raise ValueError(f"X25519 private key must be 32 bytes, got {len(private_bytes)}")
        return cls(x25519.X25519PrivateKey.from_private_bytes(private_bytes))

    def public_bytes(self) -> bytes:
        from cryptography.hazmat.primitives import serialization
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    def public_b64(self) -> str:
        return b64_encode(self.public_bytes())

    def exchange(self, peer_public_bytes: bytes) -> bytes:
        """Perform X25519 ECDH and return the 32-byte raw shared secret."""
        if len(peer_public_bytes) != 32:
            raise ValueError(f"Peer public key must be 32 bytes, got {len(peer_public_bytes)}")
        peer_pub = x25519.X25519PublicKey.from_public_bytes(peer_public_bytes)
        return self._private_key.exchange(peer_pub)


def derive_session_key(
    shared_secret: bytes,
    salt: Optional[bytes] = None,
    info: bytes = b"ATHENA-DUAL-AI-v1-SESSION",
    length: int = 32
) -> bytes:
    """Derive a high-entropy symmetric AES key from an ECDH shared secret using HKDF-SHA256."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=length,
        salt=salt or b"HONESTIC-OS-ATHENA-SALT",
        info=info,
    )
    return hkdf.derive(shared_secret)


# ── AES-256-GCM Authenticated Encryption ───────────────────────────────────────

class SymmetricCipher:
    """AES-256-GCM symmetric cipher with authenticated associated data (AAD)."""

    def __init__(self, key: bytes):
        if len(key) != 32:
            raise ValueError(f"AES-256 key must be 32 bytes, got {len(key)}")
        self._aesgcm = AESGCM(key)

    def encrypt(self, plaintext: bytes, associated_data: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        """
        Encrypts plaintext with a fresh random 96-bit (12-byte) nonce.
        Returns (nonce, ciphertext_with_tag).
        """
        nonce = secrets.token_bytes(12)
        ciphertext = self._aesgcm.encrypt(nonce, plaintext, associated_data)
        return nonce, ciphertext

    def encrypt_package(self, plaintext: bytes, associated_data: Optional[bytes] = None) -> bytes:
        """
        Packs nonce (12 bytes) + ciphertext into a single byte payload.
        """
        nonce, ct = self.encrypt(plaintext, associated_data)
        return nonce + ct

    def encrypt_package_b64(self, plaintext: bytes, associated_data: Optional[bytes] = None) -> str:
        return b64_encode(self.encrypt_package(plaintext, associated_data))

    def decrypt(self, nonce: bytes, ciphertext_with_tag: bytes, associated_data: Optional[bytes] = None) -> bytes:
        """Decrypts and authenticates AES-256-GCM payload. Raises InvalidTag if tampered."""
        if len(nonce) != 12:
            raise ValueError(f"AES-GCM nonce must be 12 bytes, got {len(nonce)}")
        return self._aesgcm.decrypt(nonce, ciphertext_with_tag, associated_data)

    def decrypt_package(self, package_bytes: bytes, associated_data: Optional[bytes] = None) -> bytes:
        if len(package_bytes) < 13:
            raise ValueError("Ciphertext package too short to contain nonce and tag")
        nonce = package_bytes[:12]
        ct = package_bytes[12:]
        return self.decrypt(nonce, ct, associated_data)

    def decrypt_package_b64(self, package_b64_str: str, associated_data: Optional[bytes] = None) -> bytes:
        raw = b64_decode(package_b64_str)
        return self.decrypt_package(raw, associated_data)

