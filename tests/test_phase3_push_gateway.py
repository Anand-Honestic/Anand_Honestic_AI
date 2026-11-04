"""
test_phase3_push_gateway.py — Unit & Security Invariant Test Suite for Push Notification Pipeline

Tests:
1. Push token registration (FCM Android & APNs iOS).
2. Zero-content wakeup ping creation.
3. Strict security invariant: zero sensitive data permitted in push payloads.
4. Dispatching wakeup pings via mock transport.
5. Error handling for unregistered devices.
"""

import unittest
from core.remote_push_gateway import PushNotificationGateway, PushPlatform


class TestPhase3PushNotificationPipeline(unittest.TestCase):

    def setUp(self):
        self.dispatched = []
        def mock_transport(platform, token, payload):
            self.dispatched.append({"platform": platform, "token": token, "payload": payload})
            return True

        self.gateway = PushNotificationGateway(transport_override=mock_transport)

    def test_01_token_registration(self):
        """Companion devices register FCM and APNs tokens properly."""
        self.gateway.register_push_token("redmi-14c-5g", "android", "fcm_token_redmi_12345")
        reg_android = self.gateway.get_registration("redmi-14c-5g")
        self.assertIsNotNone(reg_android)
        self.assertEqual(reg_android.platform, PushPlatform.FCM_ANDROID)
        self.assertEqual(reg_android.token, "fcm_token_redmi_12345")

        self.gateway.register_push_token("iphone-15", "ios", "apns_device_token_67890")
        reg_ios = self.gateway.get_registration("iphone-15")
        self.assertIsNotNone(reg_ios)
        self.assertEqual(reg_ios.platform, PushPlatform.APNS_IOS)

    def test_02_zero_content_wakeup_dispatch(self):
        """Wakeup ping dispatches zero sensitive data, only session_hint and timestamp."""
        self.gateway.register_push_token("redmi-14c-5g", "android", "fcm_token_redmi_12345")
        ok, msg, wakeup = self.gateway.dispatch_wakeup_ping("redmi-14c-5g")

        self.assertTrue(ok)
        self.assertEqual(wakeup["type"], "SYNC_PING")
        self.assertIn("session_hint", wakeup)
        self.assertIn("ts", wakeup)

        # Check mock transport received exact packet
        self.assertEqual(len(self.dispatched), 1)
        self.assertEqual(self.dispatched[0]["token"], "fcm_token_redmi_12345")
        self.assertEqual(self.dispatched[0]["payload"]["type"], "SYNC_PING")

    def test_03_sensitive_data_leak_invariant_blocked(self):
        """Security invariant: if any sensitive key leaks into a push payload, dispatch is refused."""
        forbidden_payload_1 = {"type": "SYNC_PING", "action": "OPEN_APP", "ts": 12345}
        self.assertFalse(self.gateway.sanitize_payload_check(forbidden_payload_1))

        forbidden_payload_2 = {"type": "SYNC_PING", "text": "Confidential Message", "ts": 12345}
        self.assertFalse(self.gateway.sanitize_payload_check(forbidden_payload_2))

        forbidden_payload_3 = {"type": "SYNC_PING", "secret": "ABCDEF", "ts": 12345}
        self.assertFalse(self.gateway.sanitize_payload_check(forbidden_payload_3))

        clean_payload = {"type": "SYNC_PING", "session_hint": "ephemeral-uuid", "ts": 12345}
        self.assertTrue(self.gateway.sanitize_payload_check(clean_payload))

    def test_04_unregistered_device_rejection(self):
        """Dispatch to unregistered device fails safely."""
        ok, err, wakeup = self.gateway.dispatch_wakeup_ping("unknown-device")
        self.assertFalse(ok)
        self.assertIn("No push token registered", err)
        self.assertIsNone(wakeup)


if __name__ == "__main__":
    unittest.main()

