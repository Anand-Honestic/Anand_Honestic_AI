"""
core/remote_intent_router.py — Dual-AI Distributed Intent Router & Conflict Resolver

Coordinates execution between ATHENA (PC) and Phone AI:
1. Classifies natural language requests into PC-Target, Phone-Target, or Ambiguous.
2. Context & Attention Engine: routes ambiguous commands based on active device focus.
3. Distributed Mutex & Idempotency: guarantees actions are never executed concurrently or twice.
"""

import re
import time
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any


class ExecutionTarget(str, Enum):
    PC = "PC"
    PHONE = "PHONE"
    AMBIGUOUS = "AMBIGUOUS"


# Keyword & Pattern Matching Rules for Fast Deterministic Routing
_PHONE_PATTERNS = [
    r"\b(?:call|phone|ring|dial)\s+([a-zA-Z0-9_\s]+)",
    r"\b(?:send|whatsapp|text|sms|message)\s+(?:to\s+)?([a-zA-Z0-9_\s]+)",
    r"\b(?:phone\s+battery|battery\s+on\s+(?:my\s+)?phone)\b",
    r"\b(?:phone\s+camera|take\s+a\s+photo|snap\s+picture)\b",
    r"\b(?:turn\s+on|turn\s+off|toggle)\s+(?:phone\s+)?(?:torch|flashlight|hotspot)\b",
    r"\b(?:open\s+whatsapp|open\s+instagram|open\s+swiggy|open\s+zomato)\b",
    r"\b(?:phone\s+settings|phone\s+volume)\b",
]

_PC_PATTERNS = [
    r"\b(?:open|launch)\s+(?:chrome|vs\s*code|visual\s*studio|terminal|powershell|cmd|notepad|explorer)\b",
    r"\b(?:compile|build|git\s+commit|git\s+push|run\s+test|debug)\b",
    r"\b(?:pc\s+volume|pc\s+battery|laptop\s+battery|system\s+status)\b",
    r"\b(?:screenshot|screen\s+record|capture\s+screen)\b",
    r"\b(?:close\s+window|minimize|maximize|switch\s+window|kill\s+process)\b",
    r"\b(?:search\s+memory|knowledge\s+vault|project\s+builder)\b",
]


class DistributedActionLock:
    """Distributed lock manager preventing simultaneous cross-device collisions."""

    def __init__(self, default_ttl_sec: float = 10.0):
        self.default_ttl = default_ttl_sec
        # lock_name -> (holder_device_id, expires_at)
        self._locks: Dict[str, Tuple[str, float]] = {}

    def acquire(self, lock_name: str, device_id: str, ttl_sec: Optional[float] = None) -> bool:
        """Attempts to acquire a named lock. Returns True if granted."""
        now = time.time()
        ttl = ttl_sec or self.default_ttl
        current = self._locks.get(lock_name)

        if current:
            holder, expires_at = current
            if now < expires_at and holder != device_id:
                # Lock is active and held by another device
                return False

        # Grant or renew lock
        self._locks[lock_name] = (device_id, now + ttl)
        return True

    def release(self, lock_name: str, device_id: str) -> bool:
        """Releases lock if held by the requesting device."""
        current = self._locks.get(lock_name)
        if current and current[0] == device_id:
            del self._locks[lock_name]
            return True
        return False

    def is_locked(self, lock_name: str) -> bool:
        current = self._locks.get(lock_name)
        if not current:
            return False
        return time.time() < current[1]


class DualAIIntentRouter:
    """Routes commands between ATHENA PC and Phone AI companion."""

    _instance: Optional["DualAIIntentRouter"] = None

    def __init__(self):
        self.action_lock = DistributedActionLock()
        self._processed_idempotency_keys: Dict[str, float] = {}
        self.last_pc_interaction_time = time.time()
        self.last_phone_interaction_time = 0.0

    @classmethod
    def get_instance(cls) -> "DualAIIntentRouter":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def note_interaction(self, device: ExecutionTarget) -> None:
        """Updates user attention timestamps."""
        now = time.time()
        if device == ExecutionTarget.PC:
            self.last_pc_interaction_time = now
        elif device == ExecutionTarget.PHONE:
            self.last_phone_interaction_time = now

    def classify_intent(self, text_command: str) -> Tuple[ExecutionTarget, str]:
        """
        Classifies user prompt into PC, PHONE, or AMBIGUOUS.
        Returns: (target: ExecutionTarget, normalized_action: str)
        """
        raw = text_command.strip()
        low = raw.lower()

        # Check explicit Phone patterns
        for pattern in _PHONE_PATTERNS:
            match = re.search(pattern, low)
            if match:
                action_type = "PHONE_AUTOMATION"
                if "call" in low or "dial" in low or "ring" in low:
                    action_type = "PHONE_CALL"
                elif "battery" in low:
                    action_type = "GET_BATTERY_STATUS"
                elif "whatsapp" in low or "message" in low or "text" in low:
                    action_type = "SEND_MESSAGE"
                elif "open" in low:
                    action_type = "OPEN_APP"
                elif "camera" in low or "photo" in low:
                    action_type = "TAKE_PHOTO"
                return ExecutionTarget.PHONE, action_type

        # Check explicit PC patterns
        for pattern in _PC_PATTERNS:
            if re.search(pattern, low):
                return ExecutionTarget.PC, "PC_LOCAL_ACTION"

        # Ambiguous commands
        return ExecutionTarget.AMBIGUOUS, "AMBIGUOUS_ACTION"

    def resolve_target(self, text_command: str) -> Tuple[ExecutionTarget, str, str]:
        """
        Resolves final destination using intent classification + attention context.
        Returns: (target: ExecutionTarget, action_type: str, reason: str)
        """
        target, action_type = self.classify_intent(text_command)

        if target != ExecutionTarget.AMBIGUOUS:
            return target, action_type, f"Deterministic rule matched for {target.value}"

        # Resolve ambiguous using user attention model
        now = time.time()
        pc_delta = now - self.last_pc_interaction_time
        phone_delta = now - self.last_phone_interaction_time

        # If user touched PC within last 30s and phone has been idle
        if pc_delta < 30.0 and phone_delta > 60.0:
            return ExecutionTarget.PC, action_type, "Active PC user attention context"

        # If user touched Phone recently and PC is idle
        if phone_delta < 30.0 and pc_delta > 60.0:
            return ExecutionTarget.PHONE, action_type, "Active Phone user attention context"

        # Both active or both idle -> Ask user or default to coordinator (PC)
        return ExecutionTarget.PC, action_type, "Defaulting to ATHENA primary coordinator"

    def check_and_record_idempotency(self, idempotency_key: str, ttl_sec: float = 300.0) -> bool:
        """
        Returns True if this key is fresh and records it.
        Returns False if duplicate (replay/duplicate action within TTL).
        """
        now = time.time()
        # Clean expired keys
        self._processed_idempotency_keys = {
            k: exp for k, exp in self._processed_idempotency_keys.items() if exp > now
        }

        if idempotency_key in self._processed_idempotency_keys:
            return False  # Already executed

        self._processed_idempotency_keys[idempotency_key] = now + ttl_sec
        return True
