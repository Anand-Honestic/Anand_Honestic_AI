"""
core/permission_system.py — HONESTIC OS Safety Gate & Permission System

Enforces mandatory user authorization before dangerous or irreversible actions:
- File Deletion (delete, unlink, rmdir)
- File Overwrite (replacing existing data)
- System Power (Shutdown, Restart)
- Disk formatting / Partition operations
- Firewall & Security Rule Alterations

Requires explicit "Approve? Yes / No" user confirmation via UI dialog,
Web Dashboard, or voice confirmation.
"""

from __future__ import annotations
import secrets
import threading
import time
from datetime import datetime
from typing import Dict, Any, Callable, Optional, Tuple

DANGEROUS_ACTIONS = {
    "delete_file": "Delete file permanently",
    "delete_folder": "Delete folder and all child contents",
    "overwrite_file": "Overwrite existing file content",
    "shutdown_computer": "Shut down the operating system",
    "restart_computer": "Restart the operating system",
    "format_drive": "Format storage disk or partition",
    "modify_firewall": "Alter Windows Defender Firewall inbound/outbound rules",
    "kill_critical_process": "Terminate critical system process",
}


class PermissionSystem:
    _instance: Optional["PermissionSystem"] = None

    def __init__(self):
        self._pending: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "PermissionSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def is_dangerous(self, action_name: str) -> bool:
        """Returns True if the action requires explicit human confirmation."""
        clean = action_name.lower().strip()
        return any(k in clean for k in DANGEROUS_ACTIONS.keys())

    def request_approval(
        self,
        action: str,
        target_resource: str,
        execute_callback: Optional[Callable[[], Any]] = None,
        timeout_sec: float = 60.0
    ) -> Dict[str, Any]:
        """
        Creates a permission gate. Returns approval token and prompt.
        If action is safe, executes immediately.
        """
        if not self.is_dangerous(action):
            res = execute_callback() if execute_callback else None
            return {"needs_approval": False, "approved": True, "result": res}

        token = secrets.token_hex(4).upper()
        desc = DANGEROUS_ACTIONS.get(action, f"Dangerous operation: {action}")
        prompt = f"Approve {desc} on '{target_resource}'? [Yes / No]"

        with self._lock:
            self._pending[token] = {
                "token": token,
                "action": action,
                "target": target_resource,
                "description": desc,
                "prompt": prompt,
                "callback": execute_callback,
                "created_at": time.time(),
                "timeout_sec": timeout_sec,
                "status": "pending",
            }

        return {
            "needs_approval": True,
            "token": token,
            "prompt": prompt,
            "action": action,
            "target": target_resource,
            "description": desc,
            "message": f"CONFIRMATION_REQUIRED: {prompt}"
        }

    def resolve(self, token: str, approved: bool) -> Dict[str, Any]:
        """Resolves an approval token with Yes or No."""
        with self._lock:
            clean_token = token.strip().upper()
            req = self._pending.pop(clean_token, None)

        if not req:
            return {"ok": False, "error": f"Token '{token}' not found or already expired."}

        # Check expiration
        if time.time() - req["created_at"] > req["timeout_sec"]:
            return {"ok": False, "error": f"Token '{token}' has expired."}

        if approved:
            cb = req.get("callback")
            result = None
            if callable(cb):
                try:
                    result = cb()
                except Exception as e:
                    return {"ok": False, "approved": True, "error": f"Execution error: {e}"}
            return {
                "ok": True,
                "approved": True,
                "action": req["action"],
                "target": req["target"],
                "result": result,
                "message": f"Approved and executed: {req['description']} on {req['target']}."
            }
        else:
            return {
                "ok": True,
                "approved": False,
                "action": req["action"],
                "target": req["target"],
                "message": f"Action cancelled by user: {req['description']} on {req['target']}."
            }

    def get_pending_requests(self) -> list[Dict[str, Any]]:
        """Returns all currently waiting approval requests."""
        now = time.time()
        with self._lock:
            # Purge expired
            self._pending = {k: v for k, v in self._pending.items() if (now - v["created_at"]) <= v["timeout_sec"]}
            return [
                {
                    "token": v["token"],
                    "action": v["action"],
                    "target": v["target"],
                    "prompt": v["prompt"],
                    "remaining_sec": int(v["timeout_sec"] - (now - v["created_at"])),
                }
                for v in self._pending.values()
            ]
