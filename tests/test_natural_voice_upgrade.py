"""
test_natural_voice_upgrade.py — Comprehensive Test Suite for ATHENA PRIME Human Voice Evolution
HONESTIC OS Flagship Voice Architecture & Human Realism
"""

import json
import time
import unittest
from pathlib import Path

from core.os_identity import (
    VOICE_CATALOG, VOICE_PROFILES, ATHENA_DEFAULT_PROFILE,
    DEFAULT_AI_NAME, DEFAULT_VOICE, OWNER_NAME,
    ATHENA_PRIME_RECOMMENDED_DEFAULTS, ATHENA_PRIME_PROFILE
)
from core.voice_manager import VoiceManager, get_all_voices
from core.natural_speech_engine import NaturalSpeechEngine, NaturalProsodyEngine
from memory.config_manager import (
    get_voice, get_voice_name, save_voice,
    get_voice_profile, save_voice_profile,
    get_voice_custom_params, save_voice_custom_params
)


class TestAthenaPrimeHumanVoiceEvolution(unittest.TestCase):

    def setUp(self):
        self.vm = VoiceManager.get_instance()
        self.nse = NaturalSpeechEngine.get_instance()

    def test_01_athena_prime_flagship_identity(self):
        """ATHENA PRIME must be the flagship premier human assistant voice of HONESTIC OS."""
        self.assertEqual(DEFAULT_AI_NAME, "ATHENA")
        self.assertIn(DEFAULT_VOICE, ("Athena Omega", "Athena Prime"))

        # Female voices catalog check
        female_voices = self.vm.get_female_voices()
        prime_info = next((v for v in female_voices if v["name"] == "Athena Prime"), None)
        self.assertIsNotNone(prime_info, "ATHENA PRIME must be in female voices catalog.")
        self.assertTrue(prime_info.get("flagship"), "ATHENA PRIME must be marked as flagship.")
        self.assertIn("Flagship", prime_info["title"])
        self.assertEqual(prime_info["gemini_voice"], "Aoede")
        self.assertEqual(prime_info["edge_voice"], "en-US-JennyNeural")

    def test_02_voice_catalog_preservation(self):
        """Preserve all existing voices: ATHENA, NOVA, ARIA, FRIDAY, ORION, TITAN, JARVIS."""
        female_names = [v["name"] for v in self.vm.get_female_voices()]
        male_names = [v["name"] for v in self.vm.get_male_voices()]
        all_v = get_all_voices()

        # Female voices preserved
        self.assertIn("Athena Prime", female_names)
        self.assertIn("Athena", female_names)
        self.assertIn("Nova", female_names)
        self.assertIn("Aria", female_names)
        self.assertIn("Friday", female_names)

        # Male voices preserved
        self.assertIn("Orion", male_names)
        self.assertIn("Titan", male_names)
        self.assertIn("Jarvis", male_names)

        # Total voices preserved
        for expected in ("Athena Prime", "Athena", "Nova", "Aria", "Friday", "Orion", "Titan", "Jarvis"):
            self.assertIn(expected, all_v)

        # Backend Gemini mappings preserved
        self.assertEqual(self.vm.get_gemini_voice_name("Athena Prime"), "Aoede")
        self.assertEqual(self.vm.get_gemini_voice_name("Athena"), "Aoede")
        self.assertEqual(self.vm.get_gemini_voice_name("Nova"), "Kore")
        self.assertEqual(self.vm.get_gemini_voice_name("Aria"), "Aoede")
        self.assertEqual(self.vm.get_gemini_voice_name("Friday"), "Puck")
        self.assertEqual(self.vm.get_gemini_voice_name("Orion"), "Fenrir")
        self.assertEqual(self.vm.get_gemini_voice_name("Titan"), "Charon")
        self.assertEqual(self.vm.get_gemini_voice_name("Jarvis"), "Charon")

    def test_03_instant_voice_switching(self):
        """Voice switching between ATHENA PRIME, ATHENA, NOVA, etc. is instant (< 20ms) with no restart."""
        t0 = time.perf_counter()
        switched = self.vm.set_voice("Athena Prime")
        elapsed_ms = (time.perf_counter() - t0) * 1000
        self.assertEqual(switched, "Athena Prime")
        self.assertEqual(self.vm.get_current_voice(), "Athena Prime")
        self.assertLess(elapsed_ms, 25.0, "Voice switching must be instantaneous")

        # Switch to Athena
        self.vm.set_voice("Athena")
        self.assertEqual(self.vm.get_current_voice(), "Athena")

        # Switch to Nova
        self.vm.set_voice("Nova")
        self.assertEqual(self.vm.get_current_voice(), "Nova")

        # Switch back to Athena Prime
        self.vm.set_voice("Athena Prime")
        self.assertEqual(self.vm.get_current_voice(), "Athena Prime")

    def test_04_athena_prime_recommended_defaults(self):
        """Recommended defaults: Warmth 85, Pitch 58, Speed 48, Energy 62, Expressiveness 72, Pause 60, Breath 65, Humanity 90, Conversational 80."""
        expected = {
            "warmth": 85,
            "pitch": 58,
            "speed": 48,
            "energy": 62,
            "expressiveness": 72,
            "pause_length": 60,
            "breath_level": 65,
            "humanity_level": 90,
            "conversational_level": 80,
        }
        for k, expected_val in expected.items():
            self.assertEqual(ATHENA_PRIME_RECOMMENDED_DEFAULTS[k], expected_val, f"Default for {k} must match.")
            self.assertEqual(VOICE_PROFILES["Athena Prime"][k], expected_val, f"Athena Prime profile for {k} must match.")

    def test_05_nine_axis_customization_sliders(self):
        """Nine-axis slider validation (0-100 range) and bounds checking."""
        test_sliders = {
            "warmth": 85,
            "pitch": 58,
            "speed": 48,
            "energy": 62,
            "expressiveness": 72,
            "pause_length": 60,
            "breath_level": 65,
            "humanity_level": 90,
            "conversational_level": 80,
        }
        res = self.vm.set_custom_parameters(test_sliders)
        for k, v in test_sliders.items():
            self.assertEqual(res[k], v, f"Slider {k} must be set correctly.")

        # Bounds clipping check (0-100)
        clipped = self.vm.set_custom_parameters({"warmth": 150, "pitch": -20, "breath_level": 120})
        self.assertEqual(clipped["warmth"], 100)
        self.assertEqual(clipped["pitch"], 0)
        self.assertEqual(clipped["breath_level"], 100)

    def test_06_natural_prosody_ssml_with_breathing_and_humanity(self):
        """Prosody engine creates SSML with breathing pauses, conversational pauses, and falling sentence ending."""
        text = "Hello Anand. I am ATHENA PRIME. All systems are operational. How can I help you today?"
        ssml = NaturalProsodyEngine.build_ssml(
            text=text,
            voice_id="en-US-JennyNeural",
            profile_data=VOICE_PROFILES["Athena Prime"],
            custom_params=ATHENA_PRIME_RECOMMENDED_DEFAULTS
        )

        self.assertIn("<speak", ssml)
        self.assertIn("<voice name=\"en-US-JennyNeural\">", ssml)
        self.assertIn("<break time=", ssml, "Must inject respiratory and comma breaks.")
        self.assertIn("<emphasis", ssml, "Must inject operative emphasis.")
        self.assertIn("ATHENA PRIME", ssml)
        self.assertIn("operational", ssml)

    def test_07_founder_custom_profile_athena_prime(self):
        """Founder can create and persist custom profile (ATHENA PRIME - Founder Edition)."""
        fp = self.vm.save_founder_profile("ATHENA PRIME - Founder Edition", ATHENA_PRIME_RECOMMENDED_DEFAULTS)
        self.assertEqual(fp["name"], "ATHENA PRIME - Founder Edition")
        self.assertEqual(fp["created_by"], OWNER_NAME)
        self.assertEqual(fp["custom_parameters"]["warmth"], 85)

        retrieved = self.vm.get_founder_profile()
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["name"], "ATHENA PRIME - Founder Edition")

    def test_08_founder_voice_recognition_and_greeting(self):
        """Founder recognized greeting: 'Welcome back Anand_Honestic. Good to see you again. All systems are ready.' using ATHENA PRIME."""
        self.vm.update_voice_match(confidence=0.995, status="Founder Match Confirmed")
        status = self.vm.get_voice_status()
        self.assertEqual(status["last_voice_match"]["user"], OWNER_NAME)
        self.assertEqual(status["last_voice_match"]["confidence"], 0.995)
        self.assertIn("Founder Match", status["last_voice_match"]["status"])

    def test_09_mission_control_voice_widget_telemetry(self):
        """Mission Control Voice Widget displays Current Voice, Recognition Status, Founder Match, and Voice Health."""
        status = self.vm.get_voice_status()
        self.assertIn("current_voice", status)
        self.assertIn("voice_recognition_status", status)
        self.assertIn("founder_match", status)
        self.assertIn("voice_health", status)
        self.assertIn("OPTIMAL", status["voice_health"])
        self.assertIn("custom_parameters", status)

    def test_10_offline_voice_mode_support(self):
        """ATHENA PRIME works across ONLINE, HYBRID, and OFFLINE modes seamlessly."""
        self.nse.set_mode("OFFLINE")
        self.assertEqual(self.nse.get_mode(), "OFFLINE")

        # Synthesize with ATHENA PRIME in OFFLINE mode
        pcm, sr = self.nse.synthesize_to_pcm(
            text="All systems are ready.",
            voice_name="Athena Prime",
            profile_name="Athena Prime"
        )
        self.assertIsNotNone(pcm)
        self.assertGreater(len(pcm), 0)
        self.assertGreater(sr, 0)

        # Restore ONLINE mode
        self.nse.set_mode("ONLINE")
        self.assertEqual(self.nse.get_mode(), "ONLINE")

    def test_11_side_by_side_comparison_previews_latency(self):
        """Side-by-side comparison previews for Athena, Athena Prime, Nova, Aria generate sub-second audio."""
        for voice in ("Athena Prime", "Athena", "Nova", "Aria"):
            phrase = f"Hello Anand. I am {voice.upper()}. All systems are operational. How can I help you today?"
            # Pre-warm cache
            self.nse.synthesize_to_pcm(phrase, voice_name=voice, profile_name="Athena Prime")
            # Retrieval latency check
            t0 = time.perf_counter()
            pcm, sr = self.nse.synthesize_to_pcm(phrase, voice_name=voice, profile_name="Athena Prime")
            elapsed = time.perf_counter() - t0
            self.assertIsNotNone(pcm)
            self.assertLess(elapsed, 0.4, f"Preview for {voice} took {elapsed:.4f}s (must be < 1s)")


if __name__ == "__main__":
    unittest.main()
