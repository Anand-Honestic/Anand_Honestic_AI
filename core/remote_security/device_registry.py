"""
core/remote_security/device_registry.py — Paired Device Registry & Identity Store

Manages:
1. ATHENA's persistent Ed25519 Identity Key.
2. Registry of paired phones (Redmi 14C 5G / iOS) with pinned public keys.
3. Instant revocation engine: revoking a device drops all active sessions & rejects future packets.
4. DPAPI encrypted state persistence.
"""

import time
import uuid
from typing import Dict, List, Optional, Any
from pathlib import Path
from core.remote_security.crypto import DeviceIdentityKey, b64_encode, b64_decode
from core.remote_security.dpapi_storage import DPAPIStorage


_IDENTITY_FILENAME = "athena_identity.enc"
_REGISTRY_FILENAME = "paired_devices.enc"


class DeviceRecord:
    """Represents a paired remote companion device."""

    def __init__(
        self,
        device_id: str,
        name: str,
        platform: str,
        ed25519_pub_b64: str,
        paired_at: float,
        last_seen: float = 0.0,
        is_revoked: bool = False,
        whitelist_apps: Optional[List[str]] = None,
        custom_metadata: Optional[Dict[str, Any]] = None
    ):
        self.device_id = device_id
        self.name = name
        self.platform = platform.lower()  # "android" or "ios"
        self.ed25519_pub_b64 = ed25519_pub_b64
        self.paired_at = paired_at
        self.last_seen = last_seen or paired_at
        self.is_revoked = is_revoked
        self.whitelist_apps = whitelist_apps or []
        self.custom_metadata = custom_metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "name": self.name,
            "platform": self.platform,
            "ed25519_pub_b64": self.ed25519_pub_b64,
            "paired_at": self.paired_at,
            "last_seen": self.last_seen,
            "is_revoked": self.is_revoked,
            "whitelist_apps": self.whitelist_apps,
            "custom_metadata": self.custom_metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeviceRecord":
        return cls(
            device_id=data["device_id"],
            name=data.get("name", "Unknown Phone"),
            platform=data.get("platform", "android"),
            ed25519_pub_b64=data["ed25519_pub_b64"],
            paired_at=data.get("paired_at", time.time()),
            last_seen=data.get("last_seen", time.time()),
            is_revoked=data.get("is_revoked", False),
            whitelist_apps=data.get("whitelist_apps", []),
            custom_metadata=data.get("custom_metadata", {}),
        )


class DeviceRegistry:
    """Central authority for ATHENA's identity and pinned paired devices."""

    _instance: Optional["DeviceRegistry"] = None

    def __init__(self, storage: Optional[DPAPIStorage] = None):
        self.storage = storage or DPAPIStorage()
        self._identity_key: Optional[DeviceIdentityKey] = None
        self._devices: Dict[str, DeviceRecord] = {}
        self._load_identity()
        self._load_registry()

    @classmethod
    def get_instance(cls, storage: Optional[DPAPIStorage] = None) -> "DeviceRegistry":
        if cls._instance is None:
            cls._instance = cls(storage)
        return cls._instance

    def _load_identity(self) -> None:
        """Loads master Ed25519 identity or generates and securely saves a new one."""
        data = self.storage.load_encrypted_json(_IDENTITY_FILENAME)
        if data and "ed25519_private_b64" in data:
            try:
                self._identity_key = DeviceIdentityKey.from_b64(data["ed25519_private_b64"])
                return
            except Exception as e:
                print(f"[DeviceRegistry] ⚠️ Failed loading existing identity, recreating: {e}")

        # Fresh identity generation
        self._identity_key = DeviceIdentityKey.generate()
        save_data = {
            "device_id": str(uuid.uuid4()),
            "created_at": time.time(),
            "ed25519_private_b64": self._identity_key.private_b64(),
            "ed25519_public_b64": self._identity_key.public_b64(),
        }
        self.storage.save_encrypted_json(_IDENTITY_FILENAME, save_data)
        print("[DeviceRegistry] 🔑 Created new persistent ATHENA Ed25519 identity key.")

    def _load_registry(self) -> None:
        """Loads paired devices from DPAPI storage."""
        data = self.storage.load_encrypted_json(_REGISTRY_FILENAME) or {}
        devices = {}
        for dev_id, rec_data in data.get("devices", {}).items():
            try:
                devices[dev_id] = DeviceRecord.from_dict(rec_data)
            except Exception:
                pass
        self._devices = devices

    def _save_registry(self) -> None:
        """Persists paired devices to DPAPI storage."""
        save_data = {
            "version": 1,
            "updated_at": time.time(),
            "devices": {dev_id: dev.to_dict() for dev_id, dev in self._devices.items()}
        }
        self.storage.save_encrypted_json(_REGISTRY_FILENAME, save_data)

    @property
    def identity_key(self) -> DeviceIdentityKey:
        assert self._identity_key is not None
        return self._identity_key

    @property
    def public_identity_b64(self) -> str:
        return self.identity_key.public_b64()

    def register_device(
        self,
        device_id: str,
        name: str,
        platform: str,
        ed25519_pub_b64: str,
        whitelist_apps: Optional[List[str]] = None
    ) -> DeviceRecord:
        """Registers and pins a newly paired device."""
        rec = DeviceRecord(
            device_id=device_id,
            name=name,
            platform=platform,
            ed25519_pub_b64=ed25519_pub_b64,
            paired_at=time.time(),
            last_seen=time.time(),
            is_revoked=False,
            whitelist_apps=whitelist_apps or ["com.whatsapp", "com.google.android.youtube"],
        )
        self._devices[device_id] = rec
        self._save_registry()
        print(f"[DeviceRegistry] 📱 Registered & pinned device: {name} ({device_id})")
        return rec

    def get_device(self, device_id: str) -> Optional[DeviceRecord]:
        return self._devices.get(device_id)

    def is_device_authorized(self, device_id: str, public_key_b64: str) -> bool:
        """Checks if device exists, matches pinned public key, and is not revoked."""
        rec = self.get_device(device_id)
        if not rec:
            return False
        if rec.is_revoked:
            return False
        return rec.ed25519_pub_b64 == public_key_b64

    def update_last_seen(self, device_id: str) -> None:
        rec = self.get_device(device_id)
        if rec:
            rec.last_seen = time.time()
            self._save_registry()

    def revoke_device(self, device_id: str) -> bool:
        """Instant one-click revocation: invalidates all access immediately."""
        rec = self.get_device(device_id)
        if rec:
            rec.is_revoked = True
            self._save_registry()
            print(f"[DeviceRegistry] 🚫 Revoked device {device_id} ({rec.name})")
            return True
        return False

    def unpair_device(self, device_id: str) -> bool:
        """Completely removes device from registry."""
        if device_id in self._devices:
            del self._devices[device_id]
            self._save_registry()
            print(f"[DeviceRegistry] 🗑️ Unpaired device {device_id}")
            return True
        return False

    def list_devices(self) -> List[DeviceRecord]:
        return list(self._devices.values())

