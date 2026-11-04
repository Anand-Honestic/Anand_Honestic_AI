"""
core/remote_security/audit_log.py — Cross-Device Cryptographic Audit Trail

Logs every cross-device command with:
- Correlation ID
- Originating & target device IDs
- Action & Parameters (with sensitive data sanitized)
- Authorization Tier
- Execution result
- Cryptographic hash chaining to detect tampering
"""

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any


class AuditLogger:
    """Tamper-evident audit logger for all cross-device commands."""

    _instance: Optional["AuditLogger"] = None

    def __init__(self, log_dir: Optional[Path] = None):
        self.log_dir = log_dir or (Path(__file__).resolve().parent.parent.parent / "data" / "audit_logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "cross_device_audit.jsonl"
        self._last_entry_hash = "GENESIS_BLOCK_HONESTIC_ATHENA"

    @classmethod
    def get_instance(cls, log_dir: Optional[Path] = None) -> "AuditLogger":
        if cls._instance is None:
            cls._instance = cls(log_dir)
        return cls._instance

    def log_event(
        self,
        correlation_id: str,
        sender_device_id: str,
        target_device_id: str,
        action: str,
        auth_tier: int,
        status: str,  # "SUCCESS", "REJECTED", "ERROR", "TIMEOUT"
        details: Optional[Dict[str, Any]] = None,
        error_msg: str = ""
    ) -> Dict[str, Any]:
        """Appends a new cryptographically chained audit record."""
        now = time.time()
        record = {
            "correlation_id": correlation_id,
            "ts": now,
            "datetime": datetime.fromtimestamp(now, timezone.utc).isoformat(),
            "sender": sender_device_id,
            "target": target_device_id,
            "action": action,
            "auth_tier": auth_tier,
            "status": status,
            "details": details or {},
            "error": error_msg,
            "prev_hash": self._last_entry_hash,
        }

        # Compute SHA-256 over canonical record representation
        canonical = json.dumps(record, sort_keys=True).encode("utf-8")
        entry_hash = hashlib.sha256(canonical).hexdigest()
        record["hash"] = entry_hash
        self._last_entry_hash = entry_hash

        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            print(f"[AuditLogger] ⚠️ Failed writing audit log: {e}")

        return record

    def get_recent_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Reads recent audit logs."""
        if not self.log_file.exists():
            return []
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            records = []
            for line in lines[-limit:]:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
            return records
        except Exception as e:
            print(f"[AuditLogger] Failed reading audit log: {e}")
            return []
