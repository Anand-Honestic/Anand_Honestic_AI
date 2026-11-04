"""
core/project_manager.py — HONESTIC OS Project & Task Management Engine

Automatically tracks:
- Projects & Workspaces
- Completed Tasks
- Pending Tasks
- Ideas Backlog
- Bug Tracking
- Overall Progress Metrics (%)

Persisted with MemoryGuard in memory/projects.json and linked to Second Brain.
"""

from __future__ import annotations
import secrets
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from core.memory_guard import MemoryGuard
from core.second_brain import SecondBrain

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECTS_FILE = BASE_DIR / "memory" / "projects.json"


class ProjectManager:
    _instance: Optional["ProjectManager"] = None

    def __init__(self):
        PROJECTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._data: Dict[str, Any] = self._load()

    @classmethod
    def get_instance(cls) -> "ProjectManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _default_projects(self) -> Dict[str, Any]:
        return {
            "version": "1.0.0",
            "last_updated": datetime.now().isoformat(),
            "projects": [
                {
                    "id": "proj_honestic_os",
                    "name": "HONESTIC OS",
                    "description": "Personal AI Operating System, Digital Twin, and Second Brain for Founder Anand_Honestic.",
                    "status": "active",
                    "created_at": datetime.now().isoformat(),
                    "tasks": [
                        {"id": "t1", "title": "Implement Gemini Live bidirectional streaming audio", "category": "completed", "completed_at": datetime.now().isoformat(), "priority": "high"},
                        {"id": "t2", "title": "Build Digital Twin self-learning engine", "category": "completed", "completed_at": datetime.now().isoformat(), "priority": "high"},
                        {"id": "t3", "title": "Deploy Second Brain bidirectional knowledge graph", "category": "completed", "completed_at": datetime.now().isoformat(), "priority": "high"},
                        {"id": "t4", "title": "Build 7-part Visual Teacher engine", "category": "completed", "completed_at": datetime.now().isoformat(), "priority": "medium"},
                        {"id": "t5", "title": "Implement Fast Command Engine (<500ms)", "category": "completed", "completed_at": datetime.now().isoformat(), "priority": "high"},
                        {"id": "t6", "title": "Rebrand application completely to HONESTIC OS & ATHENA", "category": "completed", "completed_at": datetime.now().isoformat(), "priority": "high"},
                        {"id": "t7", "title": "Memory protection & atomic persistence with auto-backup", "category": "completed", "completed_at": datetime.now().isoformat(), "priority": "high"},
                        {"id": "t8", "title": "Implement Safe Mode & crash recovery", "category": "completed", "completed_at": datetime.now().isoformat(), "priority": "high"},
                        {"id": "t9", "title": "Full 9-subsystem Diagnostics Center", "category": "completed", "completed_at": datetime.now().isoformat(), "priority": "high"},
                        {"id": "t10", "title": "Acoustic Voice Training & Founder Enrollment", "category": "completed", "completed_at": datetime.now().isoformat(), "priority": "medium"},
                        {"id": "t11", "title": "Mobile App Architecture & Remote Push Notifications", "category": "pending", "priority": "medium"},
                        {"id": "t12", "title": "Cloud Sync & Multi-device Replication", "category": "pending", "priority": "low"},
                        {"id": "i1", "title": "Wearable smart glasses visual link", "category": "idea", "priority": "low"},
                        {"id": "i2", "title": "Voice biometric continuous authentication", "category": "idea", "priority": "medium"},
                    ]
                }
            ]
        }

    def _load(self) -> Dict[str, Any]:
        return MemoryGuard.load_json_safe(PROJECTS_FILE, fallback_factory=self._default_projects)

    def _save(self):
        self._data["last_updated"] = datetime.now().isoformat()
        MemoryGuard.save_json_atomic(PROJECTS_FILE, self._data)

    def get_projects(self) -> List[Dict[str, Any]]:
        return self._data.get("projects", [])

    def create_project(self, name: str, description: str = "") -> Dict[str, Any]:
        pid = f"proj_{secrets.token_hex(4)}"
        p = {
            "id": pid,
            "name": name.strip(),
            "description": description.strip(),
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "tasks": []
        }
        self._data.setdefault("projects", []).append(p)
        self._save()
        # Register in Second Brain
        try:
            SecondBrain.get_instance().add_node(
                node_type="project",
                title=f"Project: {name}",
                content=description or f"Project {name} managed in HONESTIC OS.",
                tags=["project", name.lower().replace(" ", "_")]
            )
        except Exception:
            pass
        return p

    def add_task(
        self,
        project_name: str,
        title: str,
        category: str = "pending",
        priority: str = "medium"
    ) -> Dict[str, Any]:
        """
        category: 'pending' | 'completed' | 'idea' | 'bug'
        priority: 'high' | 'medium' | 'low'
        """
        target = None
        for p in self._data.get("projects", []):
            if p["name"].lower() == project_name.lower():
                target = p
                break
        if not target:
            target = self.create_project(project_name)

        tid = f"task_{secrets.token_hex(3)}"
        task = {
            "id": tid,
            "title": title.strip(),
            "category": category.lower(),
            "priority": priority.lower(),
            "created_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat() if category == "completed" else None,
        }
        target.setdefault("tasks", []).append(task)
        self._save()
        return task

    def complete_task(self, task_id_or_dict: Any) -> bool:
        if isinstance(task_id_or_dict, dict):
            task_id = str(task_id_or_dict.get("id", ""))
        else:
            task_id = str(task_id_or_dict)

        for p in self._data.get("projects", []):
            for t in p.get("tasks", []):
                if t.get("id") == task_id or t.get("title", "").lower() == task_id.lower():
                    t["category"] = "completed"
                    t["completed_at"] = datetime.now().isoformat()
                    self._save()
                    return True
        return False

    def get_metrics(self) -> Dict[str, Any]:
        total_projects = len(self._data.get("projects", []))
        completed = 0
        pending = 0
        ideas = 0
        bugs = 0

        for p in self._data.get("projects", []):
            for t in p.get("tasks", []):
                cat = t.get("category", "pending")
                if cat == "completed":
                    completed += 1
                elif cat == "pending":
                    pending += 1
                elif cat == "idea":
                    ideas += 1
                elif cat == "bug":
                    bugs += 1

        total_work = completed + pending + bugs
        progress_pct = int(round((completed / max(1, total_work)) * 100)) if total_work > 0 else 100

        return {
            "total_projects": total_projects,
            "total_tasks": completed + pending + ideas + bugs,
            "completed_tasks": completed,
            "completed": completed,
            "pending_tasks": pending,
            "pending": pending,
            "ideas": ideas,
            "bugs": bugs,
            "overall_progress_pct": progress_pct,
            "completion_rate": progress_pct,
            "projects_summary": [
                {
                    "name": p["name"],
                    "status": p.get("status", "active"),
                    "task_count": len(p.get("tasks", [])),
                }
                for p in self._data.get("projects", [])
            ]
        }
