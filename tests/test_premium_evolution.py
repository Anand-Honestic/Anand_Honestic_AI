"""
test_premium_evolution.py — Comprehensive Test Suite for HONESTIC OS Final Premium Evolution
"""

import time
import json
import unittest
from pathlib import Path

# Core imports
from core.offline_engine import OfflineEngine
from core.multi_agent import MultiAgentHive
from core.ultra_security import UltraSecurityManager
from core.voice_trainer import VoiceTrainer
from core.computer_agent import ComputerUseAgent
from core.visual_learning import VisualLearningEngine
from core.command_engine import FastCommandEngine
from core.project_manager import ProjectManager
from core.diagnostics_center import DiagnosticsCenter
from core.safe_mode import SafeModeManager
from core.conversation_replay import ConversationReplay
from memory.screen_memory import ScreenMemoryManager
from memory.digital_twin import DigitalTwinManager
from core.second_brain import SecondBrain

class TestPremiumEvolution(unittest.TestCase):

    def test_01_offline_mode_switching_and_routing(self):
        engine = OfflineEngine.get_instance()
        engine.set_mode("offline")
        self.assertEqual(engine.get_mode(), "offline")
        self.assertTrue(engine.is_currently_offline())

        # Test local offline command execution (< 350ms target under test suite load)
        engine.process_offline("volume 50")  # warm up volume COM subsystem
        t0 = time.perf_counter()
        res = engine.process_offline("volume 70")
        elapsed_ms = (time.perf_counter() - t0) * 1000
        self.assertTrue(res.get("ok"))
        self.assertTrue(res.get("offline"))
        self.assertLess(elapsed_ms, 350)

        # Test offline vault search
        res_vault = engine.process_offline("search vault python")
        self.assertTrue(res_vault.get("ok"))
        self.assertIn("knowledge_vault", res_vault.get("source"))

        # Test offline project metrics
        res_proj = engine.process_offline("project status")
        self.assertTrue(res_proj.get("ok"))
        self.assertIn(res_proj.get("source"), ("fast_command_engine", "project_manager"))

        # Reset to auto mode
        engine.set_mode("auto")
        self.assertEqual(engine.get_mode(), "auto")

    def test_02_voice_trainer_wizard_and_recognition(self):
        vt = VoiceTrainer.get_instance()
        prompts = vt.get_enrollment_prompts()
        self.assertEqual(len(prompts), 5)
        self.assertIn("Anand", prompts[0])

        # Simulate 5-step acoustic recording
        for i, p in enumerate(prompts):
            step = vt.record_wizard_step(
                step_idx=i,
                f0=125.0 + i,
                rms=0.08,
                zcr=0.045,
                spectral_centroid=1650.0 + (i * 10)
            )
            self.assertEqual(step["step"], i + 1)

        # Finalize profile
        prof = vt.finalize_enrollment(owner_name="Anand_Honestic")
        self.assertTrue(prof.get("enrolled"))
        self.assertEqual(prof.get("owner_name"), "Anand_Honestic")

        # Founder voice match verification
        match, msg, clearance = vt.verify_audio_features(127.0, 0.08, 0.045, 1670.0)
        self.assertTrue(match)
        self.assertIn("Welcome back Anand_Honestic", msg)
        self.assertEqual(clearance, "FOUNDER_CLEARANCE")

        # Non-matching voice -> Guest Mode
        guest_match, guest_msg, guest_clearance = vt.verify_audio_features(350.0, 0.01, 0.2, 4000.0)
        self.assertFalse(guest_match)
        self.assertIn(guest_clearance, ("GUEST_SANDBOX", "RESTRICTED_MODE"))

    def test_03_computer_use_agent_capabilities(self):
        agent = ComputerUseAgent.get_instance()

        # Keyboard test
        t_res = agent.keyboard_type("HONESTIC OS")
        self.assertTrue(t_res.get("ok"))

        # Hotkey test
        hk_res = agent.keyboard_hotkey("ctrl", "shift", "esc")
        self.assertTrue(hk_res.get("ok"))

        # Page search simulation
        s_res = agent.search_page("Anand_Honestic")
        self.assertTrue(s_res.get("ok"))

        # Scaffolding test
        scaff_res = agent.scaffold_project("Test_Module", "python")
        self.assertTrue(scaff_res.get("ok"))
        self.assertTrue(Path(scaff_res["project_path"]).exists())

    def test_04_visual_ai_eight_part_blueprints(self):
        v_engine = VisualLearningEngine.get_instance()
        topics = ["dns", "https", "linux", "python", "ai", "cyber security"]

        for t in topics:
            blueprint = v_engine.explain(t)
            self.assertIn("title", blueprint)
            self.assertIn("explanation", blueprint)
            self.assertIn("flowchart", blueprint)
            self.assertIn("diagram", blueprint)
            self.assertIn("teaching_card", blueprint)
            self.assertIn("example", blueprint)
            self.assertIn("quiz", blueprint)
            self.assertIn("summary", blueprint)
            self.assertIn("mind_map", blueprint)
            self.assertIn("architecture", blueprint)

    def test_05_multi_agent_hive_delegation(self):
        hive = MultiAgentHive.get_instance()
        agents = hive.get_agents()
        self.assertIn("ATHENA", agents)
        self.assertIn("NOVA", agents)
        self.assertIn("AURA", agents)
        self.assertIn("FRIDAY", agents)

        # Delegate research task to NOVA
        nova_del = hive.delegate("Research quantum encryption protocols in Knowledge Vault")
        self.assertEqual(nova_del["assigned_agent"], "NOVA")
        self.assertTrue(nova_del["result"].get("ok"))

        # Delegate builder task to AURA
        aura_del = hive.delegate("Build a project architecture for real-time visual teacher")
        self.assertEqual(aura_del["assigned_agent"], "AURA")
        self.assertTrue(aura_del["result"].get("ok"))

        # Delegate controller task to FRIDAY
        friday_del = hive.delegate("Check hardware CPU status and mouse coordinates")
        self.assertEqual(friday_del["assigned_agent"], "FRIDAY")
        self.assertTrue(friday_del["result"].get("ok"))

        # Athena default orchestration
        athena_del = hive.delegate("Coordinate executive summary for Anand_Honestic")
        self.assertEqual(athena_del["assigned_agent"], "ATHENA")
        self.assertTrue(athena_del["result"].get("ok"))

    def test_06_ultra_security_mode_and_pin(self):
        sec = UltraSecurityManager.get_instance()

        # Set PIN
        ok_pin = sec.set_pin("7788")
        self.assertTrue(ok_pin)

        # Verify correct PIN
        verify_ok, msg = sec.verify_pin("7788")
        self.assertTrue(verify_ok)
        self.assertEqual(sec.get_clearance_tier(), "FOUNDER_CLEARANCE")

        # Wrong PIN
        verify_fail, fail_msg = sec.verify_pin("0000")
        self.assertFalse(verify_fail)

        # Vault Lock
        sec.lock_vault("Security Drill")
        self.assertTrue(sec.is_vault_locked())
        self.assertEqual(sec.get_clearance_tier(), "VAULT_LOCKED")

        # Unlock with PIN
        unlocked, _ = sec.unlock_vault("7788")
        self.assertTrue(unlocked)
        self.assertFalse(sec.is_vault_locked())

    def test_07_knowledge_graph_and_second_brain(self):
        brain = SecondBrain.get_instance()
        graph = brain.get_knowledge_graph()
        self.assertIn("nodes", graph)
        self.assertIn("edges", graph)
        self.assertGreaterEqual(len(graph["nodes"]), 3)
        self.assertGreaterEqual(len(graph["edges"]), 1)

    def test_08_performance_mode_latencies(self):
        fce = FastCommandEngine.get_instance()
        commands = [
            "ping",
            "battery",
            "volume 60",
            "offline mode",
            "auto mode",
            "security status"
        ]
        for cmd in commands:
            t0 = time.perf_counter()
            res = fce.execute(cmd, mode="ultra_fast")
            elapsed_ms = (time.perf_counter() - t0) * 1000
            self.assertTrue(res.handled, f"Command '{cmd}' should be handled")
            self.assertLess(elapsed_ms, 350, f"Command '{cmd}' took {elapsed_ms:.2f}ms (>350ms target)")

    def test_09_memory_reviews_and_screen_memory(self):
        # Conversation replay
        replay_today = ConversationReplay.get_instance().replay("today")
        self.assertIn("summary", replay_today)

        replay_yesterday = ConversationReplay.get_instance().replay("yesterday")
        self.assertIn("summary", replay_yesterday)

        replay_week = ConversationReplay.get_instance().replay("week")
        self.assertIn("summary", replay_week)

        # Smart screen memory
        sm = ScreenMemoryManager.get_instance()
        rec = sm.record_screen_context(
            project="Mark-LVI-Evolution",
            notes="Honestic OS Ultra HUD upgrade verified",
            ocr_text="HONESTIC OS FOUNDER CLEARANCE ATHENA"
        )
        self.assertIn("id", rec)
        search_res = sm.search_screen_memory("Founder Clearance")
        self.assertGreaterEqual(len(search_res), 1)

    def test_10_project_manager_v2_and_self_healing(self):
        pm = ProjectManager.get_instance()
        tid = pm.add_task("Verify Apple Vision Pro Glassmorphism styling", "high")
        self.assertTrue(pm.complete_task(tid))
        metrics = pm.get_metrics()
        self.assertGreaterEqual(metrics["completed"], 1)

        # Self-healing engine
        diag = DiagnosticsCenter.get_instance().run_full_diagnostics()
        self.assertGreaterEqual(diag["health_score"], 90)

if __name__ == "__main__":
    unittest.main()
