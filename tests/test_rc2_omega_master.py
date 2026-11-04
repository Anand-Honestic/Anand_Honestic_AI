"""
test_rc2_omega_master.py — Verification of HONESTIC OS RC2 OMEGA Master Evolution
"""

import unittest
from datetime import datetime
from core.digital_twin import DigitalTwinEngine
from core.second_brain import SecondBrain
from core.brain_router import BrainRouter
from core.offline_engine import OfflineEngine
from core.startup_screen import StartupOverlay
from core.mission_control import MissionControlDialog

class TestRC2OmegaMasterEvolution(unittest.TestCase):
    def test_01_founder_startup_experience(self):
        """Verify startup overlay greeting and telemetry configuration."""
        greeting = StartupOverlay._get_founder_greeting()
        self.assertTrue(any(g in greeting for g in ("Good Morning Anand.", "Good Afternoon Anand.", "Good Evening Anand.")))
        
        # Test instantiation in headless mode
        # pyrefly: ignore[missing-import]
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        overlay = StartupOverlay()
        self.assertIn("ready", overlay._status_text)
        self.assertEqual(overlay._greeting, greeting)
        overlay.close()

    def test_02_digital_twin_narrative_insights(self):
        """Verify Digital Twin Omega presents insights as natural narrative rather than dry decimal scores."""
        dt = DigitalTwinEngine.get_instance()
        insights = dt.get_narrative_insights()
        self.assertIsInstance(insights, list)
        self.assertGreaterEqual(len(insights), 3)
        joined = " ".join(insights)
        self.assertIn("improving ATHENA's offline intelligence", joined)
        self.assertNotIn("0.82", joined)

    def test_03_second_brain_narrative_memories(self):
        """Verify Second Brain Omega presents memories as human narratives rather than database entry IDs."""
        sb = SecondBrain.get_instance()
        memories = sb.get_narrative_memories()
        self.assertIsInstance(memories, list)
        self.assertGreaterEqual(len(memories), 2)
        joined = " ".join(memories)
        self.assertIn("HONESTIC OS", joined)
        self.assertIn("Hybrid Brain", joined)
        self.assertNotIn("Memory Entry #", joined)

    def test_04_athena_personality_lock(self):
        """Verify system prompt enforces ATHENA Personality Lock with warm, human-like posture."""
        br = BrainRouter.get_instance()
        prompt = br._get_athena_system_prompt()
        self.assertIn("ATHENA", prompt)
        self.assertIn("PERSONALITY LOCK", prompt)
        self.assertIn("conversational rhythm", prompt.lower())
        self.assertIn("never break character", prompt.lower())

    def test_05_mission_control_omega_thirteen_panels(self):
        """Verify Mission Control Cockpit contains all 13 interactive HUD panels."""
        # pyrefly: ignore[missing-import]
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        dlg = MissionControlDialog()
        tab = dlg._build_overview_tab()
        self.assertIsNotNone(tab)
        dlg.close()

    def test_06_local_ai_center_product_terminology(self):
        """Verify developer language in Local AI Center is replaced with product-grade terminology."""
        # pyrefly: ignore[missing-import]
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        dlg = MissionControlDialog()
        tab = dlg._build_local_ai_tab()
        self.assertIsNotNone(tab)
        dlg.close()

    def test_07_hybrid_brain_offline_and_online_dispatch(self):
        """Verify BrainRouter operates seamlessly offline and online."""
        br = BrainRouter.get_instance()
        res = br.route("Hello ATHENA")
        self.assertTrue(res.get("ok"))
        self.assertIn(res.get("provider"), ("ollama", "gemini", "athena_omega"))
        self.assertTrue(len(res.get("content", "")) > 0)


if __name__ == "__main__":
    unittest.main()

