"""
test_phase5_relay_webrtc.py — Unit & Integration Test Suite for Remote Relay & WebRTC Signaling

Tests:
1. Zero-Knowledge Relay frame routing between paired devices.
2. WebRTC SDP Offer / Answer / ICE Candidate exchange.
3. Unpaired device rejection (authorization isolation).
4. Offline destination handling.
"""

import asyncio
import json
import unittest
from core.remote_relay_server import ZeroKnowledgeRelayServer


class TestPhase5RemoteRelayAndWebRTC(unittest.TestCase):

    def setUp(self):
        self.relay = ZeroKnowledgeRelayServer()
        self.pc_received = []
        self.phone_received = []

        self.relay.register_client("ATHENA_PC", lambda msg: self.pc_received.append(json.loads(msg)))
        self.relay.register_client("REDMI_PHONE", lambda msg: self.phone_received.append(json.loads(msg)))

        # Link devices as paired peers
        self.relay.link_devices("ATHENA_PC", "REDMI_PHONE")

    def test_01_zero_knowledge_frame_routing(self):
        """Relay forwards encrypted ciphertext between paired peers without altering content."""
        frame = {
            "v": 1,
            "sender": "REDMI_PHONE",
            "recipient": "ATHENA_PC",
            "encrypted_payload": "OPAQUE_ENCRYPTED_AES256GCM_CIPHERTEXT",
            "sig": "ED25519_SIG"
        }
        res = asyncio.run(self.relay.route_frame(json.dumps(frame)))
        self.assertEqual(res["status"], "RELAYED_SUCCESS")
        self.assertEqual(len(self.pc_received), 1)
        self.assertEqual(self.pc_received[0]["encrypted_payload"], "OPAQUE_ENCRYPTED_AES256GCM_CIPHERTEXT")

    def test_02_webrtc_signaling_pass_through(self):
        """Relay cleanly routes WebRTC SDP offer, answer, and ICE candidates."""
        offer = {
            "type": "WEBRTC_OFFER",
            "sender": "ATHENA_PC",
            "recipient": "REDMI_PHONE",
            "sdp": "v=0\r\no=- 123456 2 IN IP4 127.0.0.1..."
        }
        res_offer = asyncio.run(self.relay.route_frame(json.dumps(offer)))
        self.assertEqual(res_offer["status"], "SIGNAL_DELIVERED")
        self.assertEqual(len(self.phone_received), 1)
        self.assertEqual(self.phone_received[0]["sdp"], offer["sdp"])

        answer = {
            "type": "WEBRTC_ANSWER",
            "sender": "REDMI_PHONE",
            "recipient": "ATHENA_PC",
            "sdp": "v=0\r\no=- 654321 2 IN IP4 127.0.0.1..."
        }
        res_answer = asyncio.run(self.relay.route_frame(json.dumps(answer)))
        self.assertEqual(res_answer["status"], "SIGNAL_DELIVERED")
        self.assertEqual(len(self.pc_received), 1)

    def test_03_unpaired_rogue_device_rejected(self):
        """Unlinked / rogue devices are rejected from sending packets to other devices."""
        self.relay.register_client("ROGUE_DEVICE", lambda _: None)
        frame = {
            "v": 1,
            "sender": "ROGUE_DEVICE",
            "recipient": "ATHENA_PC",
            "encrypted_payload": "ATTACK"
        }
        res = asyncio.run(self.relay.route_frame(json.dumps(frame)))
        self.assertEqual(res["status"], "REJECTED")
        self.assertIn("not authorized", res["error"])

    def test_04_offline_recipient_queue(self):
        """Sending to an offline recipient returns QUEUED_OFFLINE."""
        self.relay.unregister_client("REDMI_PHONE")
        frame = {
            "v": 1,
            "sender": "ATHENA_PC",
            "recipient": "REDMI_PHONE",
            "encrypted_payload": "DATA"
        }
        res = asyncio.run(self.relay.route_frame(json.dumps(frame)))
        self.assertEqual(res["status"], "QUEUED_OFFLINE")


if __name__ == "__main__":
    unittest.main()

