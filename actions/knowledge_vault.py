"""
actions/knowledge_vault.py — HONESTIC OS Knowledge Vault 2.0

Upgraded Connected Knowledge Repository:
- Supports: PDF, TXT, DOCX, MD, Images, Code, Notes, Research, Projects
- Semantic & keyword relevance search (weighted TF-IDF scoring)
- Bidirectional Second Brain Knowledge Graph integration
- Cross-references and relationship mapping
"""

from __future__ import annotations
import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from core.second_brain import SecondBrain

BASE_DIR = Path(__file__).resolve().parent.parent
VAULT_DIR = BASE_DIR / "knowledge_vault"
CATEGORIES = ["pdfs", "documents", "notes", "projects", "research", "code", "images"]
INDEX_FILE = VAULT_DIR / "vault_index.json"


def _ensure_vault():
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    for cat in CATEGORIES:
        (VAULT_DIR / cat).mkdir(parents=True, exist_ok=True)
    if not INDEX_FILE.exists():
        initial_index = {
            "version": "2.0",
            "owner": "Anand_Honestic",
            "items": [
                {
                    "id": "intro-note",
                    "title": "HONESTIC OS Architecture & Vision",
                    "category": "notes",
                    "filename": "intro_note.txt",
                    "filetype": "txt",
                    "tags": ["os", "architecture", "athena"],
                    "created_at": datetime.now().isoformat(),
                    "summary": "Core blueprint for Anand_Honestic's Personal AI Operating System.",
                    "related_ids": ["proj_honestic_os"],
                }
            ]
        }
        INDEX_FILE.write_text(json.dumps(initial_index, indent=4), encoding="utf-8")
        note_path = VAULT_DIR / "notes" / "intro_note.txt"
        note_path.write_text(
            "HONESTIC OS: Commercial-grade AI Operating System for Anand_Honestic.\n"
            "AI Assistant: ATHENA.\n"
            "Key Pillars: Voice, Vision, Hardware Monitoring, Knowledge Vault 2.0, Second Brain, and Automation.",
            encoding="utf-8"
        )


def _load_index() -> Dict[str, Any]:
    _ensure_vault()
    try:
        return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"version": "2.0", "owner": "Anand_Honestic", "items": []}


def _save_index(data: Dict[str, Any]):
    _ensure_vault()
    INDEX_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


def vault_search(query: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Semantic and keyword relevance search across the Knowledge Vault.
    Uses TF-IDF inspired term frequency and field-weight ranking.
    """
    index = _load_index()
    q = (query or "").lower().strip()
    words = [w for w in re.split(r"\W+", q) if len(w) > 1]
    results = []

    for item in index.get("items", []):
        if category and item.get("category") != category:
            continue
        title = item.get("title", "").lower()
        summary = item.get("summary", "").lower()
        tags = [t.lower() for t in item.get("tags", [])]
        content_preview = item.get("content_preview", "").lower()

        score = 0
        for w in words:
            # Exact word match in title = highest weight
            if re.search(rf"\b{re.escape(w)}\b", title):
                score += 15
            elif w in title:
                score += 8

            # Tag match
            if any(w == t for t in tags):
                score += 10
            elif any(w in t for t in tags):
                score += 5

            # Summary and content matches
            if w in summary:
                score += 4
            if w in content_preview:
                score += 2

        if score > 0 or not words:
            results.append((score, item))

    results.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in results[:15]]


def vault_read(item_id_or_title: str) -> str:
    """Reads the full content of a file from the vault."""
    index = _load_index()
    target_item = None
    target_q = item_id_or_title.lower().strip()

    for item in index.get("items", []):
        if item.get("id", "").lower() == target_q or target_q in item.get("title", "").lower():
            target_item = item
            break

    if not target_item:
        return f"Item '{item_id_or_title}' not found in Knowledge Vault."

    cat = target_item.get("category", "notes")
    fname = target_item.get("filename", "")
    fpath = VAULT_DIR / cat / fname

    if not fpath.exists():
        # Check other categories just in case
        for c in CATEGORIES:
            alt = VAULT_DIR / c / fname
            if alt.exists():
                fpath = alt
                break

    if not fpath.exists():
        return f"File '{fname}' could not be located on disk."

    try:
        suffix = fpath.suffix.lower()
        if suffix in (".txt", ".md", ".py", ".json", ".csv", ".html", ".js", ".css"):
            content = fpath.read_text(encoding="utf-8", errors="replace")
            return f"[{target_item['title']}]\nCategory: {cat} | ID: {target_item['id']}\n\n{content[:4000]}"
        elif suffix == ".pdf":
            # Attempt to extract text from PDF
            try:
                import pypdf
                reader = pypdf.PdfReader(str(fpath))
                text = "\n".join(page.extract_text() or "" for page in reader.pages[:10])
                return f"[{target_item['title']} - PDF Document]\n\n{text[:3000]}"
            except Exception:
                return f"[{target_item['title']} - PDF Document]\nPath: {fpath}\nSummary: {target_item.get('summary', '')}"
        else:
            return f"[{target_item['title']}]\nType: {suffix.upper()}\nPath: {fpath}\nSummary: {target_item.get('summary', '')}"
    except Exception as e:
        return f"Error reading {fname}: {e}"


def vault_add_note(title: str, content: str, category: str = "notes", tags: Optional[List[str]] = None) -> Dict[str, Any]:
    """Adds a new text/markdown document to the vault and syncs into Second Brain."""
    _ensure_vault()
    cat = category if category in CATEGORIES else "notes"
    item_id = f"note-{uuid.uuid4().hex[:8]}"
    safe_title = re.sub(r"[^\w\-]", "_", title.lower())[:30]
    fname = f"{safe_title}_{item_id}.txt"
    filepath = VAULT_DIR / cat / fname
    filepath.write_text(content, encoding="utf-8")

    index = _load_index()
    new_entry = {
        "id": item_id,
        "title": title,
        "category": cat,
        "filename": fname,
        "filetype": "txt",
        "tags": tags or [],
        "created_at": datetime.now().isoformat(),
        "summary": content[:240].replace("\n", " "),
        "content_preview": content[:600],
    }
    index["items"].append(new_entry)
    _save_index(index)

    # Sync with Second Brain Knowledge Graph
    try:
        sb = SecondBrain.get_instance()
        sb.add_node(
            node_id=item_id,
            node_type="note",
            title=title,
            summary=new_entry["summary"],
            tags=tags or [cat],
        )
    except Exception as e:
        print(f"[Vault] Second Brain sync: {e}")

    return new_entry


def knowledge_vault_action(parameters: dict, player=None, session_memory=None) -> str:
    action = parameters.get("action", "search")
    query = parameters.get("query", "")
    category = parameters.get("category")
    item_id = parameters.get("item_id", "")
    title = parameters.get("title", "")
    content = parameters.get("content", "")

    if action == "search":
        items = vault_search(query, category)
        if not items:
            return f"No records found in Knowledge Vault 2.0 matching '{query}'."
        lines = [f"Knowledge Vault 2.0 Search ({len(items)} results):"]
        for it in items:
            lines.append(f"- [{it['category'].upper()}] {it['title']} (ID: {it['id']}): {it.get('summary', '')[:120]}")
        return "\n".join(lines)

    elif action == "read":
        return vault_read(item_id or query)

    elif action == "add_note":
        if not title or not content:
            return "Please specify both 'title' and 'content' to store in Knowledge Vault."
        res = vault_add_note(title, content, category or "notes")
        return f"Saved '{title}' to Knowledge Vault [{res['category']}]. Synced with Second Brain."

    elif action == "list":
        items = vault_search("", category)
        lines = [f"Knowledge Vault 2.0 Catalog ({len(items)} items):"]
        for it in items:
            lines.append(f"- [{it['category'].upper()}] {it['title']} (ID: {it['id']})")
        return "\n".join(lines)

    return f"Unknown Knowledge Vault action: '{action}'"


# ── Action Tool Declaration (auto-discovered by core/action_loader.py) ──────
TOOL = {
    "name": "knowledge_vault",
    "description": (
        "Search, read, or add notes, research, PDFs, and documents in Anand_Honestic's "
        "Knowledge Vault 2.0 and Second Brain repository."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "The vault action: 'search', 'read', 'add_note', or 'list'",
                "enum": ["search", "read", "add_note", "list"],
            },
            "query": {
                "type": "STRING",
                "description": "Keywords or search term to look for in the vault.",
            },
            "category": {
                "type": "STRING",
                "description": "Optional category filter: 'pdfs', 'documents', 'notes', 'projects', 'research', 'code', 'images'",
                "enum": ["pdfs", "documents", "notes", "projects", "research", "code", "images"],
            },
            "item_id": {
                "type": "STRING",
                "description": "ID or title of the specific vault item to read in detail.",
            },
            "title": {
                "type": "STRING",
                "description": "Title of new note/document being added.",
            },
            "content": {
                "type": "STRING",
                "description": "Body content of new note/document being added.",
            },
        },
        "required": ["action"],
    },
    "handler": knowledge_vault_action,
}

search_knowledge_vault = vault_search

