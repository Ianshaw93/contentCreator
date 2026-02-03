"""
Draft storage system - JSON-based storage for LinkedIn post drafts.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
import uuid


DRAFTS_FILE = Path(__file__).parent.parent / ".drafts.json"


def _load_drafts() -> dict:
    """Load drafts from JSON file."""
    if not DRAFTS_FILE.exists():
        return {"drafts": []}
    with open(DRAFTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_drafts(data: dict) -> None:
    """Save drafts to JSON file."""
    with open(DRAFTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def create_draft(
    content: str,
    hooks: list[str] = None,
    template_used: str = None,
    topic: str = None
) -> dict:
    """
    Create a new draft post.

    Args:
        content: The main post content
        hooks: List of hook options (optional)
        template_used: Which template was used to generate (optional)
        topic: Topic/theme of the post (optional)

    Returns:
        The created draft dict with id
    """
    data = _load_drafts()

    draft = {
        "id": str(uuid.uuid4())[:8],
        "content": content,
        "hooks": hooks or [],
        "selected_hook": None,
        "template_used": template_used,
        "topic": topic,
        "status": "draft",  # draft, scheduled, posted
        "scheduled_time": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

    data["drafts"].insert(0, draft)  # Newest first
    _save_drafts(data)

    return draft


def get_draft(draft_id: str) -> Optional[dict]:
    """Get a specific draft by ID."""
    data = _load_drafts()
    for draft in data["drafts"]:
        if draft["id"] == draft_id:
            return draft
    return None


def list_drafts(status: str = None, limit: int = None) -> list[dict]:
    """
    List all drafts, optionally filtered by status.

    Args:
        status: Filter by status (draft, scheduled, posted)
        limit: Maximum number of drafts to return

    Returns:
        List of draft dicts
    """
    data = _load_drafts()
    drafts = data["drafts"]

    if status:
        drafts = [d for d in drafts if d["status"] == status]

    if limit:
        drafts = drafts[:limit]

    return drafts


def update_draft(draft_id: str, **updates) -> Optional[dict]:
    """
    Update a draft.

    Args:
        draft_id: The draft ID
        **updates: Fields to update (content, hooks, selected_hook, status, scheduled_time)

    Returns:
        Updated draft dict or None if not found
    """
    data = _load_drafts()

    for i, draft in enumerate(data["drafts"]):
        if draft["id"] == draft_id:
            for key, value in updates.items():
                if key in draft:
                    draft[key] = value
            draft["updated_at"] = datetime.now().isoformat()
            data["drafts"][i] = draft
            _save_drafts(data)
            return draft

    return None


def delete_draft(draft_id: str) -> bool:
    """Delete a draft by ID."""
    data = _load_drafts()

    for i, draft in enumerate(data["drafts"]):
        if draft["id"] == draft_id:
            data["drafts"].pop(i)
            _save_drafts(data)
            return True

    return False


def get_final_post(draft_id: str) -> Optional[str]:
    """
    Get the final post content with selected hook.

    Returns the content with the selected hook prepended,
    or just the content if no hook is selected.
    """
    draft = get_draft(draft_id)
    if not draft:
        return None

    content = draft["content"]

    if draft["selected_hook"] is not None and draft["hooks"]:
        hook_idx = draft["selected_hook"]
        if 0 <= hook_idx < len(draft["hooks"]):
            hook = draft["hooks"][hook_idx]
            content = f"{hook}\n\n{content}"

    return content


if __name__ == "__main__":
    # Test the storage
    print("Testing draft storage...")

    # Create a test draft
    draft = create_draft(
        content="This is a test post about AI coaching.",
        hooks=["Hook A: Did you know...", "Hook B: Most people fail at..."],
        topic="AI Coaching"
    )
    print(f"Created draft: {draft['id']}")

    # List drafts
    drafts = list_drafts()
    print(f"Total drafts: {len(drafts)}")

    # Update draft
    updated = update_draft(draft["id"], selected_hook=0, status="scheduled")
    print(f"Updated draft status: {updated['status']}")

    # Get final post
    final = get_final_post(draft["id"])
    print(f"Final post preview:\n{final[:100]}...")
