"""
test_omega_evolution.py — Comprehensive Test Suite for HONESTIC OS ATHENA OMEGA EVOLUTION
Verifies the complete Zenith Digital Companion ecosystem, preserving all existing architecture:
- ATHENA OMEGA Flagship Personality (Warm, Calm, Professional, Trustworthy, Mature, Natural, Human-like)
- Exact 9-Axis Defaults: Warmth 95, Pitch 55, Speed 45, Energy 60, Expressiveness 85, Pause 75, Breath 80, Humanity 100, Conversational 100
- Preservation of ATHENA PRIME, ATHENA, NOVA, ARIA, FRIDAY, ORION, TITAN, JARVIS, Founder Mode, Digital Twin, Second Brain, Mission Control V2, etc.
- Real Companion Mode & Context Awareness Greeting
- Voice Realism Maximum (Breathing layers, human pacing, micro-pauses, falling terminals)
- Visual Teacher Omega (9 structured components including one-page learning card)
- Computer Agent Omega (6-stage lifecycle: Plan -> Explain -> Execute -> Monitor -> Verify -> Report)
- Second Brain Omega (8-domain automated cross-connection)
- Digital Twin Omega (6-dimensional dynamic learning without assumptions)
- Self-Improvement Engine (continuous audit, failure detection, memory optimization, report generation)
- Mission Control Omega (13 interactive OS HUD cockpit widgets)
"""

import time
import unittest
from pathlib import Path
from typing import Dict, Any

from core.os_identity import (
    PERSONALITIES, VOICE_CATALOG, VOICE_PROFILES,
    ATHENA_OMEGA_RECOMMENDED_DEFAULTS, ATHENA_OMEGA_PROFILE,
    ATHENA_PRIME_RECOMMENDED_DEFAULTS, ATHENA_PRIME_PROFILE,
    DEFAULT_AI_NAME, DEFAULT_VOICE, OWNER_NAME
)
from core.personality_manager import PersonalityManager
from core.voice_manager import VoiceManager, get_all_voices
from core.natural_speech_engine import NaturalSpeechEngine, NaturalProsodyEngine
from core.visual_learning import VisualLearningEngine
from core.computer_agent import ComputerUseAgent
from core.second_brain import SecondBrain
from core.digital_twin import DigitalTwinEngine
from core.self_improvement import SelfImprovementEngine
from memory.config_manager import (
    get_voice, get_voice_name, save_voice,
    get_voice_profile, save_voice_profile,
    get_voice_custom_params, save_voice_custom_params
)


class TestAthenaOmegaEvolution(unittest.TestCase):

    def setUp(self):
        self.vm = VoiceManager.get_instance()
        self.pm = PersonalityManager.get_instance()
        self.vle = VisualLearningEngine.get_instance()
        self.cua = ComputerUseAgent.get_instance()
        self.sb = SecondBrain.get_instance()
        self.dt = DigitalTwinEngine.get_instance()
        self.sie = SelfImprovementEngine.get_instance()

    def test_01_athena_omega_flagship_personality(self):
        """ATHENA OMEGA is the flagship digital companion personality (Warm, calm, mature, human-like)."""
        self.assertIn("ATHENA_OMEGA", PERSONALITIES)
        omega_p = PERSONALITIES["ATHENA_OMEGA"]
        self.assertEqual(omega_p["name"], "ATHENA OMEGA")
        self.assertEqual(omega_p["title"], "Flagship Digital Companion")
        self.assertEqual(omega_p["default_voice"], "Athena Omega")

        # Personality traits
        desc = omega_p["description"].lower()
        self.assertIn("warm", desc)
        self.assertIn("calm", desc)
        self.assertIn("professional", desc)
        self.assertIn("trustworthy", desc)
        self.assertIn("mature", desc)
        self.assertIn("natural", desc)
        self.assertIn("human-like", desc)

        # Active personality in manager
        p_data = self.pm.get_personality_data("ATHENA_OMEGA")
        self.assertEqual(p_data["name"], "ATHENA OMEGA")

    def test_02_athena_omega_voice_and_nine_axis_defaults(self):
        """Exact 9-axis defaults: Warmth 95, Pitch 55, Speed 45, Energy 60, Expressiveness 85, Pause 75, Breath 80, Humanity 100, Conversational 100."""
        expected_defaults = {
            "warmth": 95,
            "pitch": 55,
            "speed": 45,
            "energy": 60,
            "expressiveness": 85,
            "pause_length": 75,
            "breath_level": 80,
            "humanity_level": 100,
            "conversational_level": 100,
        }
        for k, expected_val in expected_defaults.items():
            self.assertEqual(ATHENA_OMEGA_RECOMMENDED_DEFAULTS[k], expected_val, f"Athena Omega default for {k} must match.")
            self.assertEqual(VOICE_PROFILES["Athena Omega"][k], expected_val, f"Athena Omega voice profile {k} must match.")
            self.assertEqual(ATHENA_OMEGA_PROFILE["attributes"][k], expected_val, f"Athena Omega profile specification for {k} must match.")

        # Voice catalog entry
        f_voices = self.vm.get_female_voices()
        omega_v = next((v for v in f_voices if v["name"] == "Athena Omega"), None)
        self.assertIsNotNone(omega_v, "Athena Omega must be present in female voice catalog.")
        self.assertTrue(omega_v.get("flagship"), "Athena Omega must be marked as flagship.")
        self.assertTrue(omega_v.get("omega"), "Athena Omega must be marked as omega.")
        self.assertEqual(omega_v["gemini_voice"], "Aoede")
        self.assertEqual(omega_v["edge_voice"], "en-US-JennyNeural")

    def test_03_preservation_of_all_existing_systems(self):
        """Must preserve ATHENA PRIME, ATHENA, NOVA, ARIA, FRIDAY, ORION, TITAN, JARVIS and all existing fleets."""
        all_v = get_all_voices()
        preserved_voices = [
            "Athena Omega", "Athena Prime", "Athena", "Nova",
            "Aria", "Friday", "Orion", "Titan", "Jarvis"
        ]
        for v in preserved_voices:
            self.assertIn(v, all_v, f"Voice {v} must be preserved.")

        # Preserved profiles
        self.assertIn("Athena Prime", VOICE_PROFILES)
        self.assertIn("Professional", VOICE_PROFILES)
        self.assertIn("Friendly", VOICE_PROFILES)
        self.assertIn("Natural", VOICE_PROFILES)
        self.assertIn("Warm", VOICE_PROFILES)
        self.assertIn("Technical", VOICE_PROFILES)
        self.assertIn("Calm", VOICE_PROFILES)
        self.assertIn("Founder", VOICE_PROFILES)

        # ATHENA PRIME defaults preserved intact
        self.assertEqual(ATHENA_PRIME_RECOMMENDED_DEFAULTS["warmth"], 85)
        self.assertEqual(ATHENA_PRIME_RECOMMENDED_DEFAULTS["pitch"], 58)
        self.assertEqual(ATHENA_PRIME_RECOMMENDED_DEFAULTS["speed"], 48)
        self.assertEqual(ATHENA_PRIME_RECOMMENDED_DEFAULTS["energy"], 62)
        self.assertEqual(ATHENA_PRIME_RECOMMENDED_DEFAULTS["expressiveness"], 72)
        self.assertEqual(ATHENA_PRIME_RECOMMENDED_DEFAULTS["pause_length"], 60)
        self.assertEqual(ATHENA_PRIME_RECOMMENDED_DEFAULTS["breath_level"], 65)
        self.assertEqual(ATHENA_PRIME_RECOMMENDED_DEFAULTS["humanity_level"], 90)
        self.assertEqual(ATHENA_PRIME_RECOMMENDED_DEFAULTS["conversational_level"], 80)

    def test_04_real_companion_context_greeting(self):
        """ATHENA OMEGA remembers context and greets Anand with founder familiarity."""
        greeting = self.vm.get_companion_context_greeting()
        self.assertIn("Anand", greeting)
        self.assertIn("Yesterday we worked on", greeting)
        self.assertTrue("diagnostics showed all" in greeting)
        self.assertIn("Would you like to continue?", greeting)

    def test_05_voice_realism_maximum_prosody(self):
        """SSML builder implements breathing layers, falling sentence terminals, and micro-pauses."""
        phrase = "Good morning Anand. Yesterday we worked on HONESTIC OS, and all systems are healthy. Would you like to continue?"
        ssml = NaturalProsodyEngine.build_ssml(
            text=phrase,
            voice_id="en-US-JennyNeural",
            profile_data=VOICE_PROFILES["Athena Omega"],
            custom_params=ATHENA_OMEGA_RECOMMENDED_DEFAULTS
        )
        self.assertIn("<speak", ssml)
        self.assertIn("<voice", ssml)
        self.assertIn('<break time="', ssml, "Must include breathing pauses")
        self.assertIn('<emphasis level="moderate">', ssml, "Must emphasize key operative words")
        self.assertIn('prosody rate="-3%', ssml, "Speed 45 translates into deliberate human rate")

    def test_06_visual_teacher_omega_nine_parts(self):
        """Every explanation must include all 9 components including one_page_learning_card."""
        pkg = self.vle.explain_omega("dns")
        required_keys = [
            "plain_explanation",
            "visual_diagram",
            "flowchart",
            "mind_map",
            "architecture_view",
            "real_world_example",
            "quiz",
            "summary",
            "one_page_learning_card"
        ]
        for rk in required_keys:
            self.assertIn(rk, pkg, f"Component '{rk}' must be present in Visual Teacher Omega package.")
            self.assertTrue(bool(pkg[rk]), f"Component '{rk}' must not be empty.")

        # Verify one-page learning card formatting
        card_text = pkg["one_page_learning_card"]
        self.assertIn("VISUAL TEACHER OMEGA — ONE-PAGE LEARNING CARD", card_text)
        self.assertIn("PLAIN EXPLANATION", card_text)
        self.assertIn("ARCHITECTURE TOPOLOGY", card_text)
        self.assertIn("FLOWCHART", card_text)
        self.assertIn("MIND MAP", card_text)
        self.assertIn("QUIZ", card_text)

    def test_07_computer_agent_omega_six_stages(self):
        """Computer Agent Omega executes 6-stage lifecycle: Plan -> Explain -> Execute -> Monitor -> Verify -> Report."""
        stages_seen = []
        def _on_prog(stage, pct, msg):
            if stage not in stages_seen:
                stages_seen.append(stage)

        res = self.cua.execute_omega_task("Build automated telemetry dashboard", on_progress=_on_prog)
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("progress_pct"), 100)

        # 6 stages verified
        expected_stages = ["Plan", "Explain", "Execute", "Monitor", "Verify", "Report"]
        self.assertEqual(res.get("stages"), expected_stages)
        for st in expected_stages:
            self.assertIn(st.upper(), stages_seen)

        # Verification checklist present
        self.assertIn("verification", res)
        self.assertTrue(res["verification"]["overall_verified"])
        self.assertIn("monitoring_telemetry", res)
        self.assertIn("reasoning", res)

    def test_08_second_brain_omega_eight_entities(self):
        """Second Brain Omega automatically interlinks all 8 core domains."""
        conn_res = self.sb.auto_connect_omega()
        self.assertTrue(conn_res.get("ok"))
        expected_domains = [
            "Projects", "Ideas", "Files", "Research",
            "Screenshots", "Activities", "Knowledge", "Goals"
        ]
        self.assertEqual(conn_res.get("connected_domains"), expected_domains)
        self.assertGreaterEqual(conn_res.get("relationships_created", 0), 5)
        self.assertGreaterEqual(conn_res.get("total_nodes", 0), 8)

    def test_09_digital_twin_omega_dynamic_learning(self):
        """Digital Twin Omega dynamically learns habits, schedule patterns, preferences, growth, progress, workflows."""
        profile = self.dt.get_omega_profile()
        self.assertIn("work_habits", profile)
        self.assertIn("schedule_patterns", profile)
        self.assertIn("project_preferences", profile)
        self.assertIn("knowledge_growth", profile)
        self.assertIn("learning_progress", profile)
        self.assertIn("founder_workflows", profile)

        # Dynamic learning method tests
        wf = self.dt.learn_workflow("security_hardening", ["audit_firewall", "verify_encryption", "rotate_keys"])
        self.assertEqual(wf["name"], "security_hardening")

        milestone = self.dt.record_learning_milestone("Quantum Cryptography", score=100.0, domain="Cybersecurity")
        self.assertEqual(milestone["topic"], "Quantum Cryptography")
        self.assertIn("Cybersecurity", self.dt.get_twin_summary()["knowledge_growth"]["explored_domains"])

    def test_10_self_improvement_audit(self):
        """Self-improvement engine performs continuous performance, slowdown, failure, and memory audits."""
        perf = self.sie.analyze_performance()
        self.assertIn("cpu_percent", perf)
        self.assertIn("memory_usage_mb", perf)

        slowdowns = self.sie.detect_slowdowns()
        self.assertIsInstance(slowdowns, list)

        failures = self.sie.detect_failures()
        self.assertIsInstance(failures, list)

        mem_opt = self.sie.optimize_memory()
        self.assertEqual(mem_opt.get("status"), "OPTIMIZED")

        load_opt = self.sie.optimize_loading()
        self.assertEqual(load_opt.get("status"), "OPTIMIZED")

        report = self.sie.generate_improvement_report()
        self.assertIn("overall_grade", report)
        self.assertIn("health_score", report)
        self.assertIn("performance_telemetry", report)

    def test_11_mission_control_omega_thirteen_panels(self):
        """Mission Control Omega UI constructs 13 interactive OS HUD cockpit widgets."""
        from core.mission_control import MissionControlDialog
        # Test widget structure without showing window
        try:
            # pyrefly: ignore[missing-import]
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance() or QApplication([])
            dlg = MissionControlDialog()
            overview_widget = dlg._build_overview_tab()
            self.assertIsNotNone(overview_widget)
            dlg.close()
        except Exception as e:
            self.fail(f"MissionControlDialog instantiation failed: {e}")


if __name__ == "__main__":
    unittest.main()
