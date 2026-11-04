"""
core/founder_mode.py — HONESTIC OS Founder Mode Architecture
Dedicated operating mode for 👑 Anand_Honestic (Founder & Creator).
Synthesizes the complete Founder context packet in < 5ms:
- Projects & Roadmaps
- Core Memories & Preferences
- Notes & Ideas from Second Brain
- Knowledge Vault Documents
- Digital Twin 3.0 Behavioral Model
- Active Goals & Milestones
- Recent Activities & Screen Memory
"""

from __future__ import annotations
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from core.os_identity import OWNER_NAME
from core.memory_guard import MemoryGuard

BASE_DIR = Path(__file__).resolve().parent.parent
FOUNDER_STATE_FILE = BASE_DIR / "config" / "founder_state.json"


class FounderModeEngine:
    _instance: Optional["FounderModeEngine"] = None

    def __init__(self):
        self._is_active: bool = True
        self._activated_at: str = datetime.now().isoformat()
        self._auth_source: str = "system_boot"
        self._cache_context: Optional[Dict[str, Any]] = None
        self._cache_time: float = 0.0

    @classmethod
    def get_instance(cls) -> "FounderModeEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def activate_founder_mode(self, source: str = "voice") -> Dict[str, Any]:
        """
        Activates Founder Mode for Anand_Honestic.
        Loads clearance, activates Founder security tier, and synthesizes instant context.
        """
        self._is_active = True
        self._activated_at = datetime.now().isoformat()
        self._auth_source = source

        # Elevate Ultra Security to FOUNDER_CLEARANCE
        try:
            from core.ultra_security import UltraSecurityManager
            UltraSecurityManager.get_instance().unlock_founder(verified_by=source)
        except Exception:
            pass

        ctx = self.get_founder_context(force_refresh=True)

        # Record event in timeline
        try:
            from core.memory_timeline import MemoryTimeline
            MemoryTimeline.get_instance().record_event(
                # pyrefly: ignore[unexpected-keyword]
                category="founder",
                title="Founder Mode Activated",
                details=f"Anand_Honestic authenticated via {source}. Full context loaded in {ctx.get('load_time_ms', 0)}ms."
            )
        except Exception:
            pass

        return {
            "ok": True,
            "status": "FOUNDER_ACTIVE",
            "founder": OWNER_NAME,
            "title": "Founder & Creator",
            "greeting": f"Welcome back {OWNER_NAME}. Founder Mode active — all subsystems aligned.",
            "auth_source": source,
            "context": ctx,
        }

    def get_founder_context(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Synthesizes the complete Founder context packet in < 5ms.
        ATHENA consumes this immediately to know everything Anand_Honestic is working on.
        """
        now = time.monotonic()
        if not force_refresh and self._cache_context and (now - self._cache_time < 3.0):
            return self._cache_context

        t0 = time.perf_counter()

        # 1. Projects
        projects = []
        try:
            from core.project_manager import ProjectManager
            projects = ProjectManager.get_instance().get_all_projects()
        except Exception:
            pass

        # 2. Digital Twin 3.0 Model
        twin_data = {}
        try:
            from core.digital_twin import DigitalTwinEngine
            twin_data = DigitalTwinEngine.get_instance().get_twin_summary()
        except Exception:
            pass

        # 3. Second Brain Knowledge Graph summary
        second_brain = {}
        try:
            from core.second_brain import SecondBrain
            g = SecondBrain.get_instance().get_knowledge_graph()
            second_brain = {
                "total_nodes": len(g.get("nodes", [])),
                "total_edges": len(g.get("edges", [])),
                "recent_nodes": [n.get("title") for n in g.get("nodes", [])[:6]]
            }
        except Exception:
            pass

        # 4. Knowledge Vault Status
        vault_summary = {}
        try:
            from actions.knowledge_vault import _load_index
            idx = _load_index()
            vault_summary = {
                "total_items": len(idx.get("items", [])),
                "categories": ["notes", "research", "projects", "code", "architecture"]
            }
        except Exception:
            pass

        # 5. Recent Screen Context
        screen_ctx = {}
        try:
            from memory.screen_memory import ScreenMemoryManager
            recent_shots = ScreenMemoryManager.get_instance().get_recent(limit=3)
            if recent_shots:
                screen_ctx = recent_shots[0]
        except Exception:
            pass

        # 6. Multi-Agent Hive Status
        hive_status = {}
        try:
            from core.multi_agent import MultiAgentHive
            hive_status = MultiAgentHive.get_instance().get_agents()
        except Exception:
            pass

        # 7. Goals & Priorities
        goals = twin_data.get("active_goals", [
            "Evolve HONESTIC OS into world-class AI Operating System",
            "Automate computer tasks with Computer Use Agent Pro",
            "Maintain sub-200ms local execution latency"
        ])

        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

        packet = {
            "founder_name": OWNER_NAME,
            "title": "Founder & Creator",
            "clearance": "ALPHA-1 FOUNDER CLEARANCE",
            "mode": "FOUNDER_MODE",
            "load_time_ms": elapsed_ms,
            "timestamp": datetime.now().isoformat(),
            "active_projects": projects,
            "goals": goals,
            "learned_preferences": twin_data.get("learned_preferences", {}),
            "work_habits": twin_data.get("work_habits", {}),
            "second_brain": second_brain,
            "knowledge_vault": vault_summary,
            "screen_context": screen_ctx,
            "agent_hive": hive_status,
        }

        self._cache_context = packet
        self._cache_time = now
        return packet

    def is_founder_mode_active(self) -> bool:
        return self._is_active
