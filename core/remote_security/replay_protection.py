"""
core/remote_security/replay_protection.py — Anti-Replay Defense Engine

Enforces:
1. Timestamp sliding window check: rejects packets where |t_now - t_msg| > 30.0s.
2. Monotonic sequence counters per device endpoint.
3. LRU Nonce deduplication cache to block replay of captured packets within the valid time window.
"""

import time
from typing import Dict, Set, Tuple
from collections import OrderedDict


_MAX_TIME_DRIFT_SEC = 30.0
_NONCE_CACHE_MAX_ENTRIES = 10_000


class ReplayProtectionEngine:
    """Validates packet freshness and sequence integrity per device."""

    def __init__(self, max_time_drift_sec: float = _MAX_TIME_DRIFT_SEC):
        self.max_time_drift = max_time_drift_sec
        # device_id -> highest sequence number observed
        self._device_seq: Dict[str, int] = {}
        # Ordered dictionary of seen nonces for O(1) deduplication and LRU eviction
        self._seen_nonces: OrderedDict[str, float] = OrderedDict()

    def validate_and_record(
        self,
        device_id: str,
        seq: int,
        ts_ms: int,
        nonce_b64: str,
        current_time_sec: float = 0.0
    ) -> Tuple[bool, str]:
        """
        Validates whether an incoming message is fresh and has not been replayed.
        Returns: (is_valid: bool, error_reason: str)
        """
        now = current_time_sec or time.time()
        msg_time_sec = ts_ms / 1000.0

        # 1. Timestamp Freshness Check (Sliding Window <= 30 seconds)
        time_diff = abs(now - msg_time_sec)
        if time_diff > self.max_time_drift:
            return False, f"Timestamp expired or excessive clock drift ({time_diff:.1f}s > {self.max_time_drift}s)"

        # 2. Nonce Deduplication Check
        if nonce_b64 in self._seen_nonces:
            return False, f"Replay detected: nonce {nonce_b64[:12]} already consumed"

        # 3. Monotonic Sequence Check
        last_seq = self._device_seq.get(device_id, -1)
        if seq <= last_seq:
            return False, f"Replay detected: sequence {seq} <= last seen {last_seq}"

        # Record Sequence and Nonce
        self._device_seq[device_id] = seq
        self._seen_nonces[nonce_b64] = now

        # Prune old nonces if cache exceeds capacity
        if len(self._seen_nonces) > _NONCE_CACHE_MAX_ENTRIES:
            # Pop oldest 1000 items
            for _ in range(1000):
                self._seen_nonces.popitem(last=False)

        return True, ""

    def reset_device(self, device_id: str) -> None:
        """Resets sequence tracking on session renegotiation."""
        if device_id in self._device_seq:
            del self._device_seq[device_id]
