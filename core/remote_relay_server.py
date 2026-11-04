"""
core/remote_relay_server.py — Zero-Knowledge Remote Relay & WebRTC Signaling Server

Provides remote cross-network access when PC and Phone are not on the same Wi-Fi.
Non-Negotiable Architecture Rules:
1. Zero-Knowledge: Relay sees only outer routing headers (sender, recipient, message_id).
2. It NEVER has access to session keys or plaintext command payloads.
3. Facilitates WebRTC SDP offer/answer and ICE candidate exchange for P2P DataChannels.
4. Falls back to relaying encrypted WebSocket frames if direct P2P NAT hole-punching fails.
"""

import asyncio
import json
import time
from typing import Dict, Set, Optional, Callable, Any


class RelayClientSession:
    """Represents a connected device endpoint on the relay."""

    def __init__(self, device_id: str, send_fn: Callable[[str], Any]):
        self.device_id = device_id
        self.send_fn = send_fn
        self.connected_at = time.time()
        self.last_seen = time.time()


class ZeroKnowledgeRelayServer:
    """Multiplexes encrypted packets between paired devices without plaintext access."""

    def __init__(self):
        # device_id -> RelayClientSession
        self._connected_clients: Dict[str, RelayClientSession] = {}
        # Pairing relationships: device_id -> set of authorized paired peer device_ids
        self._paired_links: Dict[str, Set[str]] = {}

    def link_devices(self, device_a: str, device_b: str) -> None:
        """Configures authorization for two devices to route packets to each other."""
        self._paired_links.setdefault(device_a, set()).add(device_b)
        self._paired_links.setdefault(device_b, set()).add(device_a)

    def register_client(self, device_id: str, send_fn: Callable[[str], Any]) -> RelayClientSession:
        """Registers a connected client socket."""
        session = RelayClientSession(device_id, send_fn)
        self._connected_clients[device_id] = session
        print(f"[RelayServer] 🌐 Client registered: {device_id}")
        return session

    def unregister_client(self, device_id: str) -> None:
        if device_id in self._connected_clients:
            del self._connected_clients[device_id]
            print(f"[RelayServer] 🔌 Client disconnected: {device_id}")

    def is_client_online(self, device_id: str) -> bool:
        return device_id in self._connected_clients

    async def route_frame(self, raw_frame_str: str) -> Dict[str, Any]:
        """
        Parses outer framing and forwards encrypted packet to target recipient.
        Guarantees: Payload is never inspected or modified.
        """
        try:
            envelope = json.loads(raw_frame_str)
        except Exception:
            return {"status": "ERROR", "error": "Invalid JSON frame"}

        msg_type = envelope.get("type", "ENCRYPTED_FRAME")
        sender = envelope.get("sender", "")
        recipient = envelope.get("recipient", "")

        if not sender or not recipient:
            return {"status": "ERROR", "error": "Missing sender or recipient"}

        # Security check: Are these devices paired?
        allowed_peers = self._paired_links.get(sender, set())
        if recipient not in allowed_peers:
            return {"status": "REJECTED", "error": f"Sender {sender} is not authorized to communicate with {recipient}"}

        target_client = self._connected_clients.get(recipient)
        if not target_client:
            return {"status": "QUEUED_OFFLINE", "message": f"Recipient {recipient} is offline"}

        # WebRTC Signaling Pass-Through (SDP Offer / Answer / ICE Candidates)
        if msg_type in ("WEBRTC_OFFER", "WEBRTC_ANSWER", "WEBRTC_ICE"):
            import inspect
            if inspect.iscoroutinefunction(target_client.send_fn):
                await target_client.send_fn(raw_frame_str)
            else:
                target_client.send_fn(raw_frame_str)
            return {"status": "SIGNAL_DELIVERED", "type": msg_type}

        # Zero-Knowledge Data Relay
        import inspect
        if inspect.iscoroutinefunction(target_client.send_fn):
            await target_client.send_fn(raw_frame_str)
        else:
            target_client.send_fn(raw_frame_str)

        return {"status": "RELAYED_SUCCESS", "recipient": recipient}

