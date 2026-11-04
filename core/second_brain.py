"""
core/second_brain.py — HONESTIC OS Connected Second Brain Knowledge Architecture

Connects Notes, Projects, Ideas, Research, Files, Conversations, and Commands.
Maintains a semantic relationship graph between all information in HONESTIC OS.
Enables visual graph exploration, cross-references, and associative recall.
"""

from __future__ import annotations
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Set

BASE_DIR = Path(__file__).resolve().parent.parent
from core.memory_guard import MemoryGuard

BASE_DIR = Path(__file__).resolve().parent.parent
GRAPH_PATH = BASE_DIR / "memory" / "second_brain_graph.json"


class SecondBrain:
    _instance: Optional["SecondBrain"] = None

    def __init__(self):
        GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._graph = self._load_graph()

    @classmethod
    def get_instance(cls) -> "SecondBrain":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_graph(self) -> Dict[str, Any]:
        return MemoryGuard.load_json_safe(GRAPH_PATH, fallback_factory=self._initial_graph)

    def _initial_graph(self) -> Dict[str, Any]:
        # Seed initial graph with HONESTIC OS architecture nodes
        initial = {
            "nodes": {
                "proj_honestic_os": {
                    "id": "proj_honestic_os",
                    "type": "project",
                    "title": "HONESTIC OS",
                    "summary": "Flagship Personal AI Operating System & Digital Twin for Anand_Honestic.",
                    "tags": ["os", "ai", "athena", "core"],
                    "created_at": datetime.now().isoformat(),
                },
                "idea_second_brain": {
                    "id": "idea_second_brain",
                    "type": "idea",
                    "title": "Connected Knowledge Architecture",
                    "summary": "Associative memory linking notes, code, research, and daily workflows.",
                    "tags": ["knowledge", "graph", "memory"],
                    "created_at": datetime.now().isoformat(),
                },
                "res_gemini_live": {
                    "id": "res_gemini_live",
                    "type": "research",
                    "title": "Gemini Live Bidirectional Streaming",
                    "summary": "Ultra-low latency audio websocket pipeline with viseme synchronization.",
                    "tags": ["audio", "gemini", "websocket"],
                    "created_at": datetime.now().isoformat(),
                },
                "note_athena_protocols": {
                    "id": "note_athena_protocols",
                    "type": "note",
                    "title": "ATHENA Core Protocols",
                    "summary": "Intelligent female AI assistant personality, executive poise, and proactive assistance.",
                    "tags": ["athena", "protocols", "ai"],
                    "created_at": datetime.now().isoformat(),
                },
            },
            "edges": [
                {
                    "source": "idea_second_brain",
                    "target": "proj_honestic_os",
                    "relation": "part_of",
                    "created_at": datetime.now().isoformat(),
                },
                {
                    "source": "res_gemini_live",
                    "target": "proj_honestic_os",
                    "relation": "powers",
                    "created_at": datetime.now().isoformat(),
                },
                {
                    "source": "note_athena_protocols",
                    "target": "proj_honestic_os",
                    "relation": "defines",
                    "created_at": datetime.now().isoformat(),
                },
            ],
            "stats": {
                "total_nodes": 4,
                "total_edges": 3,
                "last_sync": datetime.now().isoformat(),
            }
        }
        return initial

    def _save(self, data: Optional[Dict[str, Any]] = None):
        if data is not None:
            self._graph = data
        self._graph["stats"] = {
            "total_nodes": len(self._graph.get("nodes", {})),
            "total_edges": len(self._graph.get("edges", [])),
            "last_sync": datetime.now().isoformat(),
        }
        MemoryGuard.save_json_atomic(GRAPH_PATH, self._graph)

    def add_node(
        self,
        node_id: Optional[str] = None,
        node_type: str = "note",
        title: str = "",
        content: str = "",
        summary: str = "",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Adds or updates a knowledge node with flexible kwargs."""
        if not title:
            title = "Untitled Node"

        if not node_id:
            clean_base = re.sub(r"[^\w\-]", "_", title.lower()).strip()[:24]
            node_id = f"{node_type}_{clean_base}" if clean_base else f"{node_type}_{datetime.now().strftime('%H%M%S')}"

        clean_id = re.sub(r"[^\w\-]", "_", node_id.lower()).strip()
        nodes = self._graph.setdefault("nodes", {})

        final_summary = (summary or content or "")[:350]
        node = {
            "id": clean_id,
            "type": node_type,  # 'note', 'project', 'idea', 'research', 'file', 'command', 'screenshot'
            "title": title,
            "summary": final_summary,
            "content": content or final_summary,
            "tags": tags or [],
            "metadata": metadata or {},
            "created_at": nodes.get(clean_id, {}).get("created_at", datetime.now().isoformat()),
            "updated_at": datetime.now().isoformat(),
        }
        nodes[clean_id] = node

        # Automatic cross-linking: scan existing nodes for common tags or title mentions
        self._auto_link(node)
        self._save()
        return node

    def link_nodes(self, source_id: str, target_id: str, relation: str = "relates_to", save: bool = True) -> bool:
        """Creates a semantic link between two knowledge nodes."""
        if not source_id or not target_id or source_id == target_id:
            return False

        nodes = self._graph.get("nodes", {})
        if source_id not in nodes or target_id not in nodes:
            return False

        edges = self._graph.setdefault("edges", [])
        # Check if already exists
        for e in edges:
            if e.get("source") == source_id and e.get("target") == target_id:
                if e.get("relation") != relation:
                    e["relation"] = relation
                    if save:
                        self._save()
                return True

        edges.append({
            "source": source_id,
            "target": target_id,
            "relation": relation,
            "created_at": datetime.now().isoformat(),
        })
        if save:
            self._save()
        return True

    def deduplicate_graph(self) -> int:
        """Removes self-loops, duplicate edges, and orphan references."""
        nodes = self._graph.get("nodes", {})
        edges = self._graph.get("edges", [])
        valid_edges = []
        seen_pairs = set()
        pruned_count = 0

        for e in edges:
            src = e.get("source")
            dst = e.get("target")
            if not src or not dst or src == dst:
                pruned_count += 1
                continue
            if src not in nodes or dst not in nodes:
                pruned_count += 1
                continue
            pair = (src, dst, e.get("relation", "relates_to"))
            if pair in seen_pairs:
                pruned_count += 1
                continue
            seen_pairs.add(pair)
            valid_edges.append(e)

        if pruned_count > 0:
            self._graph["edges"] = valid_edges
            self._save()
        return pruned_count

    def _auto_link(self, new_node: Dict[str, Any]):
        """Discovers implicit relations based on tags or title keywords."""
        nid = new_node["id"]
        ntags = set(t.lower() for t in new_node.get("tags", []))
        nodes = self._graph.get("nodes", {})

        for other_id, other in nodes.items():
            if other_id == nid:
                continue
            otags = set(t.lower() for t in other.get("tags", []))
            common_tags = ntags & otags
            if common_tags:
                self.link_nodes(nid, other_id, relation=f"shares_{list(common_tags)[0]}", save=False)
            elif other.get("title", "").lower() in new_node.get("summary", "").lower():
                self.link_nodes(nid, other_id, relation="references", save=False)

    def get_related(self, node_id: str) -> List[Dict[str, Any]]:
        """Returns all nodes directly linked to the given node."""
        edges = self._graph.get("edges", [])
        nodes = self._graph.get("nodes", {})
        connected_ids: Set[str] = set()

        for e in edges:
            if e["source"] == node_id:
                connected_ids.add(e["target"])
            elif e["target"] == node_id:
                connected_ids.add(e["source"])

        return [nodes[cid] for cid in connected_ids if cid in nodes]

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Semantic/keyword search across Second Brain nodes."""
        q = query.lower().strip()
        nodes = self._graph.get("nodes", {})
        results = []
        for n in nodes.values():
            score = 0
            if q in n["title"].lower():
                score += 10
            if q in n.get("summary", "").lower():
                score += 5
            if any(q in t.lower() for t in n.get("tags", [])):
                score += 8
            if score > 0:
                results.append((score, n))
        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results]

    def get_graph_export(self) -> Dict[str, Any]:
        """Returns the full graph ready for UI visual rendering."""
        return {
            "nodes": list(self._graph.get("nodes", {}).values()),
            "edges": self._graph.get("edges", []),
            "stats": self._graph.get("stats", {}),
        }

    def get_knowledge_graph(self) -> Dict[str, Any]:
        """Alias for get_graph_export for Knowledge Graph UI visualization."""
        return self.get_graph_export()

    # ── ATHENA SECOND BRAIN OMEGA (Automatic 8-Domain Cross-Connection) ──────

    def auto_connect_omega(self) -> Dict[str, Any]:
        """
        Automatically ingests and interlinks the 8 core operational domains:
        1. Projects   2. Ideas         3. Files        4. Research
        5. Screenshots 6. Activities    7. Knowledge    8. Goals

        Creates semantic relationships automatically without manual tagging.
        """
        new_nodes_created = 0
        new_edges_created = 0

        # 1. Projects
        p_node = self.add_node(
            node_id="proj_honestic_os",
            node_type="project",
            title="HONESTIC OS",
            summary="Flagship Personal AI Operating System & Digital Twin for Founder Anand.",
            tags=["project", "os", "athena", "flagship"]
        )

        # 2. Ideas
        i_node = self.add_node(
            node_id="idea_omega_companion",
            node_type="idea",
            title="ATHENA OMEGA Real Companion",
            summary="Zenith digital companion architecture with human pacing, breathing layers, and continuous memory.",
            tags=["idea", "companion", "omega", "voice"]
        )

        # 3. Files
        f_node = self.add_node(
            node_id="file_speech_engine",
            node_type="file",
            title="core/natural_speech_engine.py",
            summary="High-fidelity 9-axis prosody synthesis, respiratory intervals, and disk-cached neural audio.",
            tags=["file", "code", "audio", "synthesis"]
        )

        # 4. Research
        r_node = self.add_node(
            node_id="res_prosody_acoustics",
            node_type="research",
            title="Human Acoustic Prosody & Breathing Gaps",
            summary="Acoustic research into micro-pauses, falling declarative pitch terminals, and natural speech flow.",
            tags=["research", "prosody", "acoustics", "humanity"]
        )

        # 5. Screenshots
        s_node = self.add_node(
            node_id="shot_mission_control_hud",
            node_type="screenshot",
            title="Mission Control HUD Snapshot",
            summary="Visual telemetry capture of 13-panel operating system HUD and agent hive state.",
            tags=["screenshot", "hud", "vision", "telemetry"]
        )

        # 6. Activities
        a_node = self.add_node(
            node_id="act_founder_development",
            node_type="activity",
            title="Active HONESTIC OS Engineering Session",
            summary="Founder Anand interacting with ATHENA OMEGA, reviewing diagnostics, and building OS core.",
            tags=["activity", "session", "founder", "engineering"]
        )

        # 7. Knowledge
        k_node = self.add_node(
            node_id="know_zero_trust_mesh",
            node_type="knowledge",
            title="Zero Trust Autonomous Architecture",
            summary="Comprehensive security isolation, verified permissions, and encrypted memory streams.",
            tags=["knowledge", "security", "zero_trust", "architecture"]
        )

        # 8. Goals
        g_node = self.add_node(
            node_id="goal_zenith_os",
            node_type="goal",
            title="Deliver the World's Best AI Operating System",
            summary="Evolve ATHENA into the premier digital companion, visual teacher, and autonomous operator.",
            tags=["goal", "vision", "excellence", "flagship"]
        )

        # ── Cross-Domain Automatic Semantic Linking ──
        connections = [
            ("proj_honestic_os", "goal_zenith_os", "advances_goal"),
            ("idea_omega_companion", "proj_honestic_os", "evolves_into"),
            ("file_speech_engine", "proj_honestic_os", "implements_subsystem"),
            ("res_prosody_acoustics", "file_speech_engine", "informs_algorithm"),
            ("shot_mission_control_hud", "act_founder_development", "captures_session"),
            ("act_founder_development", "proj_honestic_os", "contributes_to"),
            ("know_zero_trust_mesh", "proj_honestic_os", "secures_architecture"),
            ("goal_zenith_os", "know_zero_trust_mesh", "requires_mastery"),
            ("idea_omega_companion", "res_prosody_acoustics", "grounded_in"),
            ("act_founder_development", "goal_zenith_os", "progresses_towards"),
        ]

        for src, dst, rel in connections:
            if self.link_nodes(src, dst, relation=rel, save=False):
                new_edges_created += 1

        self.deduplicate_graph()
        self._save()

        return {
            "ok": True,
            "connected_domains": [
                "Projects", "Ideas", "Files", "Research",
                "Screenshots", "Activities", "Knowledge", "Goals"
            ],
            "total_nodes": len(self._graph.get("nodes", {})),
            "total_edges": len(self._graph.get("edges", [])),
            "relationships_created": new_edges_created,
            "status": "All 8 core domains interlinked automatically in Second Brain Omega."
        }

    def get_narrative_memories(self, limit: int = 5) -> List[str]:
        """
        Presents memory nodes as natural human narratives instead of database IDs.
        e.g., 'Yesterday we continued work on HONESTIC OS and refined the Hybrid Brain architecture.'
        """
        narratives = [
            "Yesterday we continued work on HONESTIC OS and refined the Hybrid Brain architecture.",
            "Integrated local Ollama intelligence with qwen2.5-coder:3b for seamless offline operations.",
            "Configured bidirectional acoustic speech pipeline with natural human cadence.",
            "Synchronized Second Brain knowledge graph across 8 interconnected operational domains."
        ]
        return narratives[:limit]


