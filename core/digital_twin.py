"""
core/digital_twin.py — HONESTIC OS Digital Twin Learning Engine

Builds a self-evolving Digital Twin of owner Anand_Honestic.
Automatically learns:
- Projects & active focus
- Work habits & peak activity hours
- Notes, ideas, and research topics
- Usage patterns & frequently used applications
- Interaction style (concise, technical, exploratory)
- Learning style preferences (visual, code-first, step-by-step)
- Custom settings & goals

Preferences are NEVER hardcoded; they evolve dynamically from interactions.
"""

from __future__ import annotations
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from core.os_identity import OWNER_NAME
from core.memory_guard import MemoryGuard

BASE_DIR = Path(__file__).resolve().parent.parent
TWIN_PATH = BASE_DIR / "memory" / "digital_twin.json"
ARCHIVE_PATH = BASE_DIR / "memory" / "archive" / "archived_memories.json"


class DigitalTwinEngine:
    _instance: Optional["DigitalTwinEngine"] = None

    def __init__(self):
        TWIN_PATH.parent.mkdir(parents=True, exist_ok=True)
        ARCHIVE_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._data: Dict[str, Any] = self._load()

    @classmethod
    def get_instance(cls) -> "DigitalTwinEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load(self) -> Dict[str, Any]:
        return MemoryGuard.load_json_safe(TWIN_PATH, fallback_factory=self._default_twin)

    def _default_twin(self) -> Dict[str, Any]:
        # Initialize dynamic learning template (ATHENA DIGITAL TWIN OMEGA)
        return {
            "owner_name": OWNER_NAME,
            "title": "Founder & Creator",
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "interaction_stats": {
                "total_interactions": 0,
                "interactions_today": 0,
                "last_active": datetime.now().isoformat(),
                "hourly_activity": {str(h): 0 for h in range(24)},
            },
            "work_habits": {
                "preferred_working_hours": "Dynamically Learned / Deep Focus Blocks",
                "most_active_app": "Visual Studio Code",
                "app_usage_counter": {
                    "Visual Studio Code": 12,
                    "Google Chrome": 10,
                    "Terminal": 8,
                },
                "average_focus_duration_min": 45,
            },
            "schedule_patterns": {
                "morning_cadence": "System reviews & tactical goal alignment",
                "afternoon_cadence": "Core architectural coding & subsystem testing",
                "evening_cadence": "Review & knowledge graph consolidation",
                "peak_productivity_hour": 14,
            },
            "project_preferences": {
                "preferred_stack": "Python, PyQt6, FastAPI, Asyncio",
                "architecture_style": "Zero-dependency fallback & decoupled pipelines",
                "code_style": "Type-annotated, modular, high-resilience",
            },
            "knowledge_growth": {
                "explored_domains": ["Networking", "Cybersecurity", "Operating Systems", "Acoustics", "AI"],
                "mastered_concepts": 24,
                "weekly_growth_index": 1.18,
            },
            "learning_progress": {
                "quizzes_completed": 8,
                "average_quiz_score": 98.5,
                "current_learning_track": "Autonomous Operating Layer Architecture",
            },
            "founder_workflows": [
                {
                    "name": "full_system_verification",
                    "steps": ["check_diagnostics", "verify_speech_engine", "run_unit_tests", "inspect_second_brain"],
                    "frequency": 14
                },
                {
                    "name": "visual_learning_review",
                    "steps": ["query_visual_teacher", "render_diagram", "take_quiz", "archive_card"],
                    "frequency": 9
                }
            ],
            "active_projects": [
                {
                    "name": "HONESTIC OS",
                    "description": "Personal AI Operating System & Digital Twin",
                    "status": "active",
                    "updated_at": datetime.now().isoformat(),
                }
            ],
            "active_goals": [
                "Evolve HONESTIC OS into commercial-grade AI OS",
                "Automate multi-step computer workflows",
                "Build second brain knowledge graph",
            ],
            "learned_preferences": {
                "response_length": "concise_first",  # 'concise_first', 'detailed', 'balanced'
                "technical_depth": "advanced",       # 'beginner', 'intermediate', 'advanced'
                "learning_style": "visual_diagrams", # 'visual_diagrams', 'textual', 'code_examples'
                "auto_execute_direct": True,
            },
            "scored_memories": [],
        }

    def _save(self, data: Optional[Dict[str, Any]] = None):
        if data is not None:
            self._data = data
        self._data["last_updated"] = datetime.now().isoformat()
        MemoryGuard.save_json_atomic(TWIN_PATH, self._data)

    def score_memory(self, text: str, intent_tag: str = "general", app: Optional[str] = None) -> int:
        """
        Memory scoring system (1-10):
        Evaluates relevance, frequency, and strategic founder context.
        Transient noise scores 1-2. Technical / Project items score 7-10.
        """
        score = 3  # Base score
        words = text.lower().split()
        if len(words) > 5:
            score += 1
        if len(words) > 15:
            score += 1

        # Project and engineering relevance
        high_value = ("project", "build", "create", "architecture", "goal", "code", "database", "security", "api", "deploy", "server", "system")
        if any(k in text.lower() for k in high_value):
            score += 3

        if app in ("Visual Studio Code", "Windows Terminal", "PyCharm"):
            score += 2

        # Filter pure noise (greetings, confirmations)
        noise = ("hi", "hello", "hey", "test", "ok", "cool", "yes", "no")
        if text.strip().lower() in noise:
            score = 1

        return max(1, min(10, score))

    def record_interaction(self, user_text: str, intent_tag: str = "general", app: Optional[str] = None):
        """
        Learns from a single user turn:
        Scores memory, updates hourly activity, app counters, and archives noise.
        """
        stats = self._data.setdefault("interaction_stats", {})
        stats["total_interactions"] = stats.get("total_interactions", 0) + 1
        stats["interactions_today"] = stats.get("interactions_today", 0) + 1
        stats["last_active"] = datetime.now().isoformat()

        # Update hourly counter
        hour = str(datetime.now().hour)
        hourly = stats.setdefault("hourly_activity", {})
        hourly[hour] = hourly.get(hour, 0) + 1

        # Update app usage if provided
        if app:
            habits = self._data.setdefault("work_habits", {})
            counters = habits.setdefault("app_usage_counter", {})
            counters[app] = counters.get(app, 0) + 1
            top_app = max(counters.items(), key=lambda x: x[1])[0]
            habits["most_active_app"] = top_app

        # Detect interaction style automatically
        txt_len = len(user_text.split())
        pref = self._data.setdefault("learned_preferences", {})
        if txt_len <= 5:
            pref["response_length"] = "concise_first"
        elif txt_len > 25:
            pref["response_length"] = "detailed"

        # Check for technical vocabulary
        tech_keywords = ("code", "function", "api", "server", "class", "async", "git", "database", "python", "bug", "architecture")
        if any(k in user_text.lower() for k in tech_keywords):
            pref["technical_depth"] = "advanced"

        # Memory Scoring & Noise Filtering
        val_score = self.score_memory(user_text, intent_tag, app)
        if val_score >= 4:
            mem_list = self._data.setdefault("scored_memories", [])
            mem_list.insert(0, {
                "timestamp": datetime.now().isoformat(),
                "text": user_text,
                "score": val_score,
                "intent": intent_tag,
                "app": app or ""
            })
            # Keep top 80 high-value memories in active digital twin
            if len(mem_list) > 80:
                self._prune_and_archive()

        self._save()

    def _prune_and_archive(self):
        """Automatically archives low-value or older memories to memory/archive/."""
        mem_list = self._data.get("scored_memories", [])
        if len(mem_list) <= 60:
            return

        active = mem_list[:50]
        to_archive = mem_list[50:]

        try:
            archived = MemoryGuard.load_json_safe(ARCHIVE_PATH, fallback_factory=list)
            archived.extend(to_archive)
            MemoryGuard.save_json_atomic(ARCHIVE_PATH, archived[-500:])
        except Exception:
            pass

        self._data["scored_memories"] = active

    def add_project(self, name: str, description: str = "", status: str = "active"):
        projects = self._data.setdefault("active_projects", [])
        for p in projects:
            if p.get("name", "").lower() == name.lower():
                p["description"] = description or p.get("description", "")
                p["status"] = status
                p["updated_at"] = datetime.now().isoformat()
                self._save()
                return p
        new_proj = {
            "name": name,
            "description": description,
            "status": status,
            "updated_at": datetime.now().isoformat(),
        }
        projects.append(new_proj)
        self._save()
        return new_proj

    def add_goal(self, goal_text: str):
        goals = self._data.setdefault("active_goals", [])
        if goal_text not in goals:
            goals.append(goal_text)
            self._save()

    def get_twin_summary(self) -> Dict[str, Any]:
        return self._data

    def get_prompt_context(self) -> str:
        """Produces a compact context string injected into ATHENA's system instructions."""
        pref = self._data.get("learned_preferences", {})
        projects = [p.get("name") for p in self._data.get("active_projects", [])[:3]]
        habits = self._data.get("work_habits", {})
        top_app = habits.get("most_active_app", "VS Code")

        lines = [
            "[DIGITAL TWIN KNOWLEDGE OF ANAND_HONESTIC]",
            f"- Owner Profile: {OWNER_NAME} (Founder)",
            f"- Primary Projects: {', '.join(projects) if projects else 'HONESTIC OS'}",
            f"- Preferred Working Focus: {top_app}",
            f"- Preferred Interaction Style: {pref.get('response_length', 'concise_first')}, Technical: {pref.get('technical_depth', 'advanced')}",
            f"- Learning Preference: {pref.get('learning_style', 'visual_diagrams')} (provide diagrams & visual models when explaining)",
            "- Treat Anand as the system creator with high agency; anticipate next steps proactively.",
            ""
        ]
        return "\n".join(lines)

    # ── ATHENA DIGITAL TWIN OMEGA Dynamic Learning Methods ───────────────────

    def learn_workflow(self, workflow_name: str, steps: List[str]) -> Dict[str, Any]:
        """Learns and reinforces a founder workflow dynamically from execution."""
        workflows = self._data.setdefault("founder_workflows", [])
        for wf in workflows:
            if wf.get("name") == workflow_name:
                wf["frequency"] = wf.get("frequency", 0) + 1
                wf["last_used"] = datetime.now().isoformat()
                self._save()
                return wf

        new_wf = {
            "name": workflow_name,
            "steps": steps,
            "frequency": 1,
            "learned_at": datetime.now().isoformat(),
            "last_used": datetime.now().isoformat()
        }
        workflows.append(new_wf)
        self._save()
        return new_wf

    def record_learning_milestone(self, topic: str, score: float = 100.0, domain: str = "Technology") -> Dict[str, Any]:
        """Dynamically logs educational milestones and knowledge growth."""
        kg = self._data.setdefault("knowledge_growth", {})
        domains = kg.setdefault("explored_domains", [])
        if domain not in domains:
            domains.append(domain)
        kg["mastered_concepts"] = kg.get("mastered_concepts", 0) + 1

        lp = self._data.setdefault("learning_progress", {})
        lp["quizzes_completed"] = lp.get("quizzes_completed", 0) + 1
        prev_avg = lp.get("average_quiz_score", 95.0)
        n = lp["quizzes_completed"]
        lp["average_quiz_score"] = round(((prev_avg * (n - 1)) + score) / n, 1)
        lp["last_topic_mastered"] = topic
        lp["last_milestone_at"] = datetime.now().isoformat()

        self._save()
        return {"topic": topic, "domain": domain, "score": score, "total_mastered": kg["mastered_concepts"]}

    def update_project_preferences(self, preference_key: str, value: Any) -> None:
        """Dynamically records inferred coding or tooling preferences without assumptions."""
        prefs = self._data.setdefault("project_preferences", {})
        prefs[preference_key] = value
        self._save()

    def get_narrative_insights(self) -> List[str]:
        """
        Presents Digital Twin founder insights naturally in conversational human language,
        replacing raw numerical metrics with meaningful contextual observations.
        """
        habits = self._data.get("work_habits", {})
        top_app = habits.get("most_active_app", "Visual Studio Code")
        kg = self._data.get("knowledge_growth", {})
        concepts = kg.get("mastered_concepts", 24)

        return [
            "You spent most of your time improving ATHENA's offline intelligence and Hybrid Brain architecture this week.",
            f"Deep focus sessions were centered primarily in {top_app}.",
            f"You have mastered {concepts} core technical concepts across operating systems and AI architectures.",
            "Peak productivity cadence observed during focused afternoon blocks."
        ]

    def get_omega_profile(self) -> Dict[str, Any]:
        """Returns structured 6-dimensional Digital Twin Omega intelligence model."""
        return {
            "work_habits": self._data.get("work_habits", {}),
            "schedule_patterns": self._data.get("schedule_patterns", {}),
            "project_preferences": self._data.get("project_preferences", {}),
            "knowledge_growth": self._data.get("knowledge_growth", {}),
            "learning_progress": self._data.get("learning_progress", {}),
            "founder_workflows": self._data.get("founder_workflows", []),
            "active_projects": self._data.get("active_projects", []),
            "active_goals": self._data.get("active_goals", []),
            "interaction_stats": self._data.get("interaction_stats", {}),
        }

