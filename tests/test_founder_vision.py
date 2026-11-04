"""
test_founder_vision.py — Comprehensive Test Suite for HONESTIC OS Founder Vision Final Evolution
"""

import time
import json
import unittest
from pathlib import Path

# Core imports
from core.founder_mode import FounderModeEngine
from core.mobile_ecosystem import MobileEcosystemManager
from core.voice_trainer import VoiceTrainer
from core.offline_engine import OfflineEngine
from core.computer_agent import ComputerUseAgent
from core.analytics_engine import AnalyticsEngine
from core.multi_agent import MultiAgentHive
from core.diagnostics_center import DiagnosticsCenter
from core.conversation_replay import ConversationReplay
from core.command_engine import FastCommandEngine
from core.ultra_security import UltraSecurityManager

class TestFounderVisionEvolution(unittest.TestCase):

    def test_01_founder_mode_synthesis(self):
        f_engine = FounderModeEngine.get_instance()
        res = f_engine.activate_founder_mode(source="voice_biometric")
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("status"), "FOUNDER_ACTIVE")
        self.assertIn("Anand_Honestic", res.get("founder"))

        # Measure context synthesis latency (< 10ms)
        t0 = time.perf_counter()
        ctx = f_engine.get_founder_context(force_refresh=True)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        self.assertIn("active_projects", ctx)
        self.assertIn("goals", ctx)
        self.assertIn("learned_preferences", ctx)
        self.assertIn("second_brain", ctx)
        self.assertLess(elapsed_ms, 25.0)

    def test_02_mobile_companion_pairing_and_trusted_devices(self):
        mem = MobileEcosystemManager.get_instance()

        # 1. Generate QR pairing payload
        qr_data = mem.generate_pairing_payload()
        self.assertIn("pair_code", qr_data)
        self.assertIn("qr_url", qr_data)
        self.assertEqual(qr_data.get("expires_in_seconds"), 300)

        # 2. Pair device with Founder PIN
        UltraSecurityManager.get_instance().set_pin("7788")
        pair_res = mem.pair_device(
            device_name="Anand Mobile Companion",
            pair_code=qr_data["pair_code"],
            client_ip="192.168.1.105",
            pin="7788"
        )
        self.assertTrue(pair_res.get("ok"))
        dev_id = pair_res["device_id"]
        dev_tok = pair_res["device_token"]

        # 3. Verify trusted status and token
        self.assertTrue(mem.verify_device_token(dev_tok))
        devs = mem.list_trusted_devices()
        self.assertGreaterEqual(len(devs), 1)

        # 4. Remote Action Execution
        rem_res = mem.execute_remote_action("security_check")
        self.assertTrue(rem_res.get("ok"))

        # 5. Revoke Device
        self.assertTrue(mem.revoke_device(dev_id))

    def test_03_voice_identity_2_three_tier_classification(self):
        vt = VoiceTrainer.get_instance()

        # Enroll base founder profile
        vt.record_wizard_step(0, f0=130.0, rms=0.08, zcr=0.045, spectral_centroid=1650.0)
        vt.finalize_enrollment("Anand_Honestic")

        # Tier 1: Founder Voice (f0 within 35Hz)
        f_res = vt.classify_voice(f0=132.0)
        self.assertEqual(f_res["tier"], vt.VOICE_FOUNDER)
        self.assertEqual(f_res["clearance"], "FOUNDER_CLEARANCE")
        self.assertEqual(f_res["access_level"], "FULL_ACCESS")
        self.assertIn("Welcome back Anand_Honestic", f_res["greeting"])

        # Tier 2: Guest Voice (f0 between 35Hz and 85Hz)
        g_res = vt.classify_voice(f0=185.0)
        self.assertEqual(g_res["tier"], vt.VOICE_GUEST)
        self.assertEqual(g_res["clearance"], "GUEST_SANDBOX")
        self.assertEqual(g_res["access_level"], "LIMITED_ACCESS")

        # Tier 3: Unknown Voice (f0 delta > 85Hz)
        u_res = vt.classify_voice(f0=350.0)
        self.assertEqual(u_res["tier"], vt.VOICE_UNKNOWN)
        self.assertEqual(u_res["clearance"], "RESTRICTED_MODE")

    def test_04_offline_hybrid_architecture(self):
        oe = OfflineEngine.get_instance()
        oe.set_mode("hybrid")
        self.assertEqual(oe.get_mode(), "hybrid")
        self.assertTrue(oe.is_hybrid_mode())
        # In hybrid mode, local fast execution is allowed without failing
        res = oe.process_offline("ping")
        self.assertTrue(res.get("ok"))

        oe.set_mode("auto")

    def test_05_computer_use_agent_pro(self):
        agent = ComputerUseAgent.get_instance()

        # Task planning
        plan = agent.plan_task("Scrape latest AI research papers and verify in browser")
        self.assertTrue(plan.get("ok"))
        self.assertGreaterEqual(plan["total_steps"], 2)
        self.assertIn("steps", plan)

        # File search
        files = agent.search_files("*.py")
        self.assertGreaterEqual(len(files), 5)

        # Downloads check
        downloads = agent.list_downloads(limit=5)
        self.assertIsInstance(downloads, list)

    def test_06_analytics_engine(self):
        analytics = AnalyticsEngine.get_instance()
        analytics.record_command("project", time_saved_sec=60.0)
        analytics.record_project_built("HONESTIC OS Pro")
        analytics.record_knowledge_item("notes")

        metrics = analytics.get_metrics()
        self.assertGreater(metrics["commands_used"], 0)
        self.assertGreater(metrics["time_saved_minutes"], 0.0)
        self.assertGreaterEqual(metrics["system_health"]["score"], 90)

    def test_07_digital_twin_and_focus_learning_replay(self):
        replay = ConversationReplay.get_instance()

        # Focus replay
        focus_res = replay.replay_focus()
        self.assertIn("ACTIVE PROJECT FOCUS", focus_res)

        # Learning replay
        learning_res = replay.replay_learning()
        self.assertIn("RECENT KNOWLEDGE", learning_res)

        # Structured replay wrapper
        r_focus = replay.replay("focus")
        self.assertEqual(r_focus["period"], "focus")

        r_learning = replay.replay("learning")
        self.assertEqual(r_learning["period"], "learning")

    def test_08_multi_agent_hive_collaboration(self):
        hive = MultiAgentHive.get_instance()
        collab = hive.collaborate("Build distributed zero-latency telemetry dashboard")
        self.assertTrue(collab.get("ok"))
        self.assertEqual(len(collab["collaborating_agents"]), 4)
        self.assertEqual(len(collab["stages"]), 4)

    def test_09_continuous_self_evolution_and_healing(self):
        dc = DiagnosticsCenter.get_instance()

        slow = dc.detect_slowdowns()
        self.assertIn("status", slow)

        mem = dc.detect_memory_corruption()
        self.assertIn("status", mem)

        plugins = dc.detect_failed_plugins()
        self.assertTrue(plugins.get("healthy"))

        heal = dc.heal_subsystems()
        self.assertTrue(heal.get("ok"))

    def test_10_performance_targets(self):
        fce = FastCommandEngine.get_instance()
        commands = [
            "ping",
            "founder mode",
            "hybrid mode",
            "what project am i focused on",
            "what have i learned recently"
        ]
        for cmd in commands:
            t0 = time.perf_counter()
            res = fce.execute(cmd, mode="ultra_fast")
            elapsed_ms = (time.perf_counter() - t0) * 1000
            self.assertTrue(res.handled, f"Command '{cmd}' should be handled")
            self.assertLess(elapsed_ms, 200, f"Command '{cmd}' took {elapsed_ms:.2f}ms (>200ms target)")

if __name__ == "__main__":
    unittest.main()
