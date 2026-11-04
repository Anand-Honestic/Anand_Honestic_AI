"""
test_hybrid_brain_offline.py — Verification Test Suite for Hybrid Brain Omega Integration
Tests:
1. Every prompt goes through BrainRouter first
2. BrainRouter chooses Gemini (online) or Ollama (offline / hybrid)
3. Offline mode routes all queries to local Ollama (qwen2.5-coder:3b)
4. Context augmentation for memory and project queries
5. Natural speech synthesis offline fallback
6. OfflineBrainSession conforming to Engine protocol for JarvisLive
7. Verification of all 4 required test queries:
   - Hello ATHENA
   - What projects am I working on?
   - Tell me a joke.
   - Write a Python function.
"""

import unittest
import asyncio
from core.brain_router import BrainRouter, OfflineBrainSession
from core.offline_engine import OfflineEngine
from core.natural_speech_engine import NaturalSpeechEngine


class TestHybridBrainOffline(unittest.TestCase):

    def setUp(self):
        self.router = BrainRouter.get_instance()
        self.off_engine = OfflineEngine.get_instance()

    def test_01_brain_router_presence_and_active_model(self):
        """BrainRouter exists, is singleton, and has active model qwen2.5-coder:3b."""
        self.assertIsNotNone(self.router)
        self.assertEqual(self.router, BrainRouter.get_instance())
        active_m = self.router._models.get_active()
        self.assertIn("qwen", active_m.lower())

    def test_02_offline_mode_forces_ollama(self):
        """When offline mode is active or internet is unavailable, provider must be Ollama."""
        self.off_engine.set_mode("offline")
        task_type = self.router._reasoning.classify("Hello ATHENA")
        provider, model = self.router._reasoning.choose_provider(
            task_type,
            gemini_up=False,
            ollama_up=True,
            models=self.router._models.get_models(),
            mode="offline"
        )
        self.assertEqual(provider, "ollama")
        self.assertIn("qwen", model.lower())

    def test_03_query_hello_athena_offline(self):
        """Query: Hello ATHENA -> generated via Ollama with ATHENA persona."""
        self.off_engine.set_mode("offline")
        res = self.router.route("Hello ATHENA")
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("provider"), "ollama")
        self.assertTrue(len(res.get("content", "")) > 0)

    def test_04_query_projects_offline_context(self):
        """Query: What projects am I working on? -> generated via Ollama with local context."""
        self.off_engine.set_mode("offline")
        res = self.router.route("What projects am I working on?")
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("provider"), "ollama")
        content = res.get("content", "")
        self.assertTrue(len(content) > 0)
        # Should mention HONESTIC OS or projects from project manager
        self.assertTrue(any(term in content.lower() for term in ("honestic", "project", "os", "task", "workspace")))

    def test_05_query_joke_offline(self):
        """Query: Tell me a joke. -> generated via Ollama with natural personality."""
        self.off_engine.set_mode("offline")
        res = self.router.route("Tell me a joke.")
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("provider"), "ollama")
        self.assertTrue(len(res.get("content", "")) > 0)

    def test_06_query_python_function_offline(self):
        """Query: Write a Python function. -> generated via Ollama code model."""
        self.off_engine.set_mode("offline")
        res = self.router.route("Write a Python function to compute factorial.")
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("provider"), "ollama")
        content = res.get("content", "")
        self.assertIn("def ", content)

    def test_07_offline_engine_process_offline_routes_through_brain_router(self):
        """OfflineEngine.process_offline routes through BrainRouter to Ollama."""
        self.off_engine.set_mode("offline")
        res = self.off_engine.process_offline("Hello ATHENA")
        self.assertTrue(res.get("ok"))
        self.assertTrue(res.get("offline"))
        self.assertIn("brain_router:ollama", res.get("source"))

    def test_08_voice_synthesis_offline(self):
        """NaturalSpeechEngine synthesizes PCM audio offline."""
        engine = NaturalSpeechEngine.get_instance()
        engine.set_mode("OFFLINE")
        pcm, sr = engine.synthesize_to_pcm("Hello Anand, ATHENA is fully operational offline.")
        self.assertIsNotNone(pcm)
        self.assertTrue(len(pcm) > 0)
        self.assertTrue(sr > 0)

    def test_09_offline_brain_session_engine_contract(self):
        """OfflineBrainSession implements the Engine protocol for JarvisLive."""
        async def _run():
            session = OfflineBrainSession()
            self.assertTrue(hasattr(session, "send_realtime_input"))
            self.assertTrue(hasattr(session, "send_client_content"))
            self.assertTrue(hasattr(session, "send_tool_response"))
            self.assertTrue(hasattr(session, "receive"))
            self.assertTrue(hasattr(session, "close"))

            await session.send_client_content(turns={"role": "user", "parts": [{"text": "Hello ATHENA"}]})
            received_said = False
            received_audio = False
            turn_completed = False

            async for msg in session.receive():
                if msg.server_content and msg.server_content.output_transcription:
                    received_said = True
                if msg.data:
                    received_audio = True
                if msg.server_content and msg.server_content.turn_complete:
                    turn_completed = True
                    break

            await session.close()
            return received_said, received_audio, turn_completed

        said, audio, done = asyncio.run(_run())
        self.assertTrue(said, "OfflineBrainSession must emit said text.")
        self.assertTrue(audio, "OfflineBrainSession must emit audio bytes.")
        self.assertTrue(done, "OfflineBrainSession must emit turn completion.")


if __name__ == "__main__":
    unittest.main()

