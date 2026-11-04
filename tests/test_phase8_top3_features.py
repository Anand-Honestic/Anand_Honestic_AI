"""
test_phase8_top3_features.py — Unit & Integration Test Suite for Top 3 Additional Features

Tests:
1. Feature 1: Bi-directional Clipboard Sync with sensitive data scrubbing.
2. Feature 2: Emergency Kill Switch immediate session termination.
3. Feature 3: App Whitelist UI & programmatic enforcement.
"""

import unittest
from core.remote_clipboard import ClipboardManager
from core.remote_companion_server import RemoteCompanionHub
from core.remote_security.auth_tiers import CommandAuthorizer


class TestPhase8Top3Features(unittest.TestCase):

    def test_01_clipboard_safe_text_sync(self):
        """Standard text snippets sync across devices cleanly."""
        clipboard = ClipboardManager()
        res = clipboard.set_local_clipboard("https://github.com/honestic/athena-phone-ai")
        self.assertTrue(res["can_sync"])
        self.assertEqual(res["text"], "https://github.com/honestic/athena-phone-ai")

        applied = clipboard.receive_remote_clipboard("Meeting notes: sync PC and phone by 4 PM")
        self.assertTrue(applied)
        self.assertEqual(clipboard.get_current_text(), "Meeting notes: sync PC and phone by 4 PM")

    def test_02_clipboard_sensitive_data_scrubbing(self):
        """Credit cards, private keys, and long API tokens are blocked from cross-device sync."""
        clipboard = ClipboardManager()

        # Credit card
        cc_res = clipboard.set_local_clipboard("4111111111111111")
        self.assertFalse(cc_res["can_sync"])
        self.assertIn("Sensitive content detected", cc_res["reason"])

        # Private key header
        pk_res = clipboard.set_local_clipboard("-----BEGIN RSA PRIVATE KEY----- MIIEowIBAAKCAQEA0...")
        self.assertFalse(pk_res["can_sync"])

        # High-entropy API bearer token
        jwt_res = clipboard.set_local_clipboard("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c")
        self.assertFalse(jwt_res["can_sync"])

    def test_03_emergency_kill_switch(self):
        """Emergency Kill Switch flushes all active companion sessions immediately."""
        hub = RemoteCompanionHub.get_instance()
        hub._active_sessions["dummy-phone-1"] = None
        hub._active_sessions["dummy-phone-2"] = None

        kill_res = hub.emergency_kill_switch()
        self.assertEqual(kill_res["status"], "KILL_SWITCH_ACTIVE")
        self.assertEqual(kill_res["dropped_sessions"], 2)
        self.assertEqual(len(hub.list_active_device_ids()), 0)

    def test_04_app_whitelist_enforcement(self):
        """Programmatic whitelist authorizer strictly allows whitelisted apps and rejects unapproved packages."""
        authorizer = CommandAuthorizer(allowed_packages=["com.whatsapp", "com.google.android.youtube"])

        # Whitelisted
        ok, _ = authorizer.validate_command_intent("OPEN_APP", {"package": "com.whatsapp"}, declared_tier=1)
        self.assertTrue(ok)

        # Unapproved
        ok, err = authorizer.validate_command_intent("OPEN_APP", {"package": "com.unknown.trojan"}, declared_tier=1)
        self.assertFalse(ok)
        self.assertIn("not in the approved app whitelist", err)


if __name__ == "__main__":
    unittest.main()

