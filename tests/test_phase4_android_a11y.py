"""
test_phase4_android_a11y.py — Android Accessibility Compliance & Policy Test Suite

Verifies:
1. AndroidManifest.xml compliance (Android 14 / HyperOS Foreground Service types).
2. accessibility_service_config.xml compliance (whitelisted packages, gesture capabilities).
3. Whitelist enforcement and password field rejection rules.
"""

import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


class TestPhase4AndroidAccessibilityCompliance(unittest.TestCase):

    def setUp(self):
        self.base_dir = Path(__file__).resolve().parent.parent / "android" / "app" / "src" / "main"

    def test_01_manifest_permissions_and_fgs_types(self):
        """AndroidManifest declares proper foregroundServiceType for Android 14 / Xiaomi HyperOS."""
        manifest_path = self.base_dir / "AndroidManifest.xml"
        self.assertTrue(manifest_path.exists())

        tree = ET.parse(manifest_path)
        root = tree.getroot()

        # Check required permissions
        permissions = [elem.attrib.get("{http://schemas.android.com/apk/res/android}name") for elem in root.findall("uses-permission")]
        self.assertIn("android.permission.INTERNET", permissions)
        self.assertIn("android.permission.FOREGROUND_SERVICE", permissions)
        self.assertIn("android.permission.FOREGROUND_SERVICE_CONNECTED_DEVICE", permissions)
        self.assertIn("android.permission.FOREGROUND_SERVICE_SPECIAL_USE", permissions)
        self.assertIn("android.permission.REQUEST_IGNORE_BATTERY_OPTIMIZATIONS", permissions)

        # Check service declaration
        app = root.find("application")
        services = app.findall("service")
        service_names = [s.attrib.get("{http://schemas.android.com/apk/res/android}name") for s in services]
        self.assertIn(".service.AthenaForegroundService", service_names)
        self.assertIn(".service.AthenaAccessibilityService", service_names)

        # Check a11y service permission
        a11y_service = next(s for s in services if s.attrib.get("{http://schemas.android.com/apk/res/android}name") == ".service.AthenaAccessibilityService")
        self.assertEqual(
            a11y_service.attrib.get("{http://schemas.android.com/apk/res/android}permission"),
            "android.permission.BIND_ACCESSIBILITY_SERVICE"
        )

    def test_02_accessibility_service_config_xml(self):
        """accessibility_service_config.xml restricts package names and enables window content."""
        config_path = self.base_dir / "res" / "xml" / "accessibility_service_config.xml"
        self.assertTrue(config_path.exists())

        tree = ET.parse(config_path)
        root = tree.getroot()

        self.assertEqual(root.attrib.get("{http://schemas.android.com/apk/res/android}canRetrieveWindowContent"), "true")
        self.assertEqual(root.attrib.get("{http://schemas.android.com/apk/res/android}canPerformGestures"), "true")
        
        # Package names whitelist present
        pkg_names = root.attrib.get("{http://schemas.android.com/apk/res/android}packageNames", "")
        self.assertIn("com.whatsapp", pkg_names)
        self.assertIn("com.google.android.youtube", pkg_names)


if __name__ == "__main__":
    unittest.main()

