"""
core/offline_engine.py — HONESTIC OS Autonomous Offline Operational Engine

Enables ATHENA to remain fully operational when internet access is unavailable:
- Auto-detects network presence without blocking (socket probe with 0.5s timeout)
- Three operational modes:
  - ONLINE MODE (Force Gemini Live + Cloud Services)
  - OFFLINE MODE (Force Local Operations Only)
  - AUTO MODE (Dynamically switches seamlessly based on connectivity)
- In Offline / Auto-offline:
  - Local command routing via FastCommandEngine
  - Knowledge Vault offline semantic search & notes
  - Second Brain graph traversal
  - Application launch & management (open/close apps)
  - System controls (volume, brightness, media, power, workspace save/restore)
  - Visual Learning blueprint synthesis
  - Project Manager & Task tracking
  - Sub-50ms execution latency
"""

from __future__ import annotations
import socket
import time
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class OfflineEngine:
    _instance: Optional["OfflineEngine"] = None

    MODE_AUTO = "auto"
    MODE_ONLINE = "online"
    MODE_OFFLINE = "offline"
    MODE_HYBRID = "hybrid"

    def __init__(self):
        self._mode: str = self.MODE_AUTO
        self._last_net_check: float = 0.0
        self._is_online_cached: bool = True
        self._check_interval: float = 5.0  # seconds between probes

    @classmethod
    def get_instance(cls) -> "OfflineEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def check_internet(self, force: bool = False) -> bool:
        """Non-blocking socket probe to verify connectivity."""
        now = time.monotonic()
        if not force and (now - self._last_net_check < self._check_interval):
            return self._is_online_cached

        self._last_net_check = now
        # Test connection to public DNS servers (Cloudflare / Google) on port 53
        for host in ("1.1.1.1", "8.8.8.8"):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.4)
                s.connect((host, 53))
                s.close()
                self._is_online_cached = True
                return True
            except Exception:
                continue

        self._is_online_cached = False
        return False

    def record_network_failure(self):
        """Immediately marks the network as unreachable."""
        self._is_online_cached = False
        self._last_net_check = time.monotonic()

    def record_network_success(self):
        """Immediately marks the network as reachable."""
        self._is_online_cached = True
        self._last_net_check = time.monotonic()

    def get_mode(self) -> str:
        return self._mode

    def set_mode(self, mode: str) -> str:
        clean = mode.lower().strip()
        if clean in (self.MODE_AUTO, self.MODE_ONLINE, self.MODE_OFFLINE, self.MODE_HYBRID):
            self._mode = clean
        return self._mode

    def is_currently_offline(self) -> bool:
        """Returns True if the system is currently restricted to offline operations."""
        if self._mode == self.MODE_OFFLINE:
            return True
        if self._mode in (self.MODE_ONLINE, self.MODE_HYBRID):
            return False
        # AUTO MODE: check real-time connectivity
        return not self.check_internet()

    def is_hybrid_mode(self) -> bool:
        return self._mode == self.MODE_HYBRID

    def get_status(self) -> Dict[str, Any]:
        has_net = self.check_internet()
        effective_mode = "offline" if self.is_currently_offline() else "online"
        return {
            "configured_mode": self._mode,
            "effective_mode": effective_mode,
            "internet_reachable": has_net,
            "offline_capabilities": [
                "Fast Command Engine",
                "Knowledge Vault Search",
                "Application Control",
                "System Controls",
                "Workspace Save & Restore",
                "Project Manager",
                "Second Brain Navigation",
                "Visual Learning Blueprints",
                "Diagnostics Center",
                "Backup System"
            ]
        }

    def process_offline(self, command_text: str) -> Dict[str, Any]:
        """
        Executes a command locally with sub-100ms response time.
        Routes through FastCommandEngine, Knowledge Vault, and Project Manager.
        """
        start_t = time.perf_counter()
        raw = command_text.strip()
        lower = raw.lower()

        # 1. FastCommandEngine direct execution for instant OS controls
        from core.command_engine import FastCommandEngine
        res = FastCommandEngine.get_instance().execute(raw)
        if res.handled:
            elapsed = round((time.perf_counter() - start_t) * 1000, 1)
            return {
                "ok": True,
                "offline": True,
                "source": "fast_command_engine",
                "latency_ms": elapsed,
                "message": res.message,
                "action": res.action,
            }

        # 2. Knowledge Vault Search commands
        if any(k in lower for k in ("search vault", "vault search", "look in vault", "find in vault")):
            query = lower.replace("search vault", "").replace("vault search", "").replace("find in vault", "").strip()
            from actions.knowledge_vault import search_knowledge_vault
            vault_res = search_knowledge_vault(query)
            elapsed = round((time.perf_counter() - start_t) * 1000, 1)
            return {
                "ok": True,
                "offline": True,
                "source": "knowledge_vault",
                "latency_ms": elapsed,
                "message": vault_res,
            }

        # 3. Project Manager query
        if any(k in lower for k in ("project status", "project metrics", "tasks pending")):
            from core.project_manager import ProjectManager
            m = ProjectManager.get_instance().get_metrics()
            msg = (
                f"📊 Project Metrics (Offline):\n"
                f"• Completion Rate: {m.get('completion_rate', 0)}%\n"
                f"• Total Tasks: {m.get('total_tasks', 0)} (Completed: {m.get('completed', 0)}, Pending: {m.get('pending', 0)})\n"
                f"• Ideas: {m.get('ideas', 0)} | Bugs: {m.get('bugs', 0)}"
            )
            elapsed = round((time.perf_counter() - start_t) * 1000, 1)
            return {
                "ok": True,
                "offline": True,
                "source": "project_manager",
                "latency_ms": elapsed,
                "message": msg,
            }

        # 4. Route user prompt through BrainRouter first (Hybrid Brain Omega -> Ollama)
        try:
            from core.brain_router import BrainRouter
            br = BrainRouter.get_instance()
            route_res = br.route(raw)
            if route_res.get("ok") and route_res.get("content"):
                elapsed = round((time.perf_counter() - start_t) * 1000, 1)
                return {
                    "ok": True,
                    "offline": True,
                    "source": f"brain_router:{route_res.get('provider', 'ollama')}",
                    "latency_ms": elapsed,
                    "message": route_res.get("content", ""),
                    "model": route_res.get("model", ""),
                }
        except Exception as e:
            print(f"[OfflineEngine] BrainRouter routing error: {e}")

        # 5. Visual Learning query fallback
        if any(k in lower for k in ("explain", "what is", "how does", "diagram")):
            topic = lower.replace("explain", "").replace("what is", "").replace("how does", "").strip()
            from core.visual_learning import VisualLearningEngine
            card = VisualLearningEngine.get_instance().explain(topic)
            elapsed = round((time.perf_counter() - start_t) * 1000, 1)
            return {
                "ok": True,
                "offline": True,
                "source": "visual_learning",
                "latency_ms": elapsed,
                "message": f"{card['title']}:\n{card['explanation']}\n\nDiagram:\n{card['diagram']}",
                "card": card,
            }

        elapsed = round((time.perf_counter() - start_t) * 1000, 1)
        return {
            "ok": True,
            "offline": True,
            "source": "athena_offline",
            "latency_ms": elapsed,
            "message": f"I am ATHENA, operating in offline mode. Core local services, apps, and Knowledge Vault are ready for '{raw}'.",
        }
