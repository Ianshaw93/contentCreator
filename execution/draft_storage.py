"""
Draft storage system - JSON-based storage for LinkedIn post drafts and hooks bank.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
import uuid


DRAFTS_FILE = Path(__file__).parent.parent / ".drafts.json"
HOOKS_BANK_FILE = Path(__file__).parent.parent / ".hooks_bank.json"
IDEAS_BANK_FILE = Path(__file__).parent.parent / ".ideas_bank.json"


def _load_drafts() -> dict:
    """Load drafts from JSON file."""
    if not DRAFTS_FILE.exists():
        return {"drafts": []}
    with open(DRAFTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_hooks_bank() -> dict:
    """Load hooks bank from JSON file."""
    if not HOOKS_BANK_FILE.exists():
        return {"hooks": []}
    with open(HOOKS_BANK_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_hooks_bank(data: dict) -> None:
    """Save hooks bank to JSON file."""
    with open(HOOKS_BANK_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def _save_drafts(data: dict) -> None:
    """Save drafts to JSON file."""
    with open(DRAFTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def _migrate_draft(draft: dict) -> dict:
    """Ensure draft has all required fields (migration for older drafts)."""
    if "posted_at" not in draft:
        draft["posted_at"] = None
    if "images" not in draft:
        draft["images"] = []
    return draft


def create_draft(
    content: str,
    hooks: list[str] = None,
    template_used: str = None,
    topic: str = None,
    selected_hook: int = None
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
        "selected_hook": selected_hook,
        "template_used": template_used,
        "topic": topic,
        "status": "draft",  # draft, scheduled, posted
        "scheduled_time": None,
        "posted_at": None,
        "images": [],
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
            return _migrate_draft(draft)
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
    drafts = [_migrate_draft(d) for d in data["drafts"]]

    if status:
        drafts = [d for d in drafts if d["status"] == status]

    if limit:
        drafts = drafts[:limit]

    return drafts


def list_drafts_by_date(year: int, month: int) -> list[dict]:
    """
    List all drafts that are scheduled or posted in a given month.

    Args:
        year: Year (e.g., 2024)
        month: Month (1-12)

    Returns:
        List of draft dicts with their scheduled/posted dates
    """
    data = _load_drafts()
    drafts = [_migrate_draft(d) for d in data["drafts"]]

    result = []
    for draft in drafts:
        # Check scheduled_time
        if draft.get("scheduled_time"):
            try:
                dt = datetime.fromisoformat(draft["scheduled_time"].replace("Z", "+00:00"))
                if dt.year == year and dt.month == month:
                    result.append(draft)
                    continue
            except (ValueError, AttributeError):
                pass

        # Check posted_at
        if draft.get("posted_at"):
            try:
                dt = datetime.fromisoformat(draft["posted_at"].replace("Z", "+00:00"))
                if dt.year == year and dt.month == month:
                    result.append(draft)
                    continue
            except (ValueError, AttributeError):
                pass

    return result


def get_drafts_for_date(date_str: str) -> list[dict]:
    """
    Get all drafts scheduled or posted on a specific date.

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        List of draft dicts
    """
    data = _load_drafts()
    drafts = [_migrate_draft(d) for d in data["drafts"]]

    result = []
    for draft in drafts:
        # Check scheduled_time
        if draft.get("scheduled_time"):
            try:
                dt = datetime.fromisoformat(draft["scheduled_time"].replace("Z", "+00:00"))
                if dt.strftime("%Y-%m-%d") == date_str:
                    result.append(draft)
                    continue
            except (ValueError, AttributeError):
                pass

        # Check posted_at
        if draft.get("posted_at"):
            try:
                dt = datetime.fromisoformat(draft["posted_at"].replace("Z", "+00:00"))
                if dt.strftime("%Y-%m-%d") == date_str:
                    result.append(draft)
                    continue
            except (ValueError, AttributeError):
                pass

    return result


def update_draft(draft_id: str, **updates) -> Optional[dict]:
    """
    Update a draft.

    Args:
        draft_id: The draft ID
        **updates: Fields to update (content, hooks, selected_hook, status, scheduled_time, posted_at, images)

    Returns:
        Updated draft dict or None if not found
    """
    data = _load_drafts()

    for i, draft in enumerate(data["drafts"]):
        if draft["id"] == draft_id:
            # Migrate first to ensure all fields exist
            draft = _migrate_draft(draft)
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


# =============================================================================
# HOOKS BANK FUNCTIONS
# =============================================================================

def save_hook_to_bank(hook: str, topic: str = None) -> dict:
    """
    Save a hook to the hooks bank for future use.

    Args:
        hook: The hook text
        topic: Optional topic/idea it relates to

    Returns:
        The saved hook entry
    """
    data = _load_hooks_bank()

    entry = {
        "id": str(uuid.uuid4())[:8],
        "hook": hook,
        "topic": topic,
        "created_at": datetime.now().isoformat(),
        "used_count": 0,
    }

    data["hooks"].insert(0, entry)
    _save_hooks_bank(data)

    return entry


def get_hooks_bank(topic: str = None) -> list[dict]:
    """
    Get all saved hooks, optionally filtered by topic.

    Args:
        topic: Filter by topic (partial match)

    Returns:
        List of hook entries
    """
    data = _load_hooks_bank()
    hooks = data["hooks"]

    if topic:
        hooks = [h for h in hooks if topic.lower() in (h.get("topic") or "").lower()]

    return hooks


def delete_hook_from_bank(hook_id: str) -> bool:
    """Delete a hook from the bank."""
    data = _load_hooks_bank()

    for i, hook in enumerate(data["hooks"]):
        if hook["id"] == hook_id:
            data["hooks"].pop(i)
            _save_hooks_bank(data)
            return True

    return False


def increment_hook_usage(hook_id: str) -> None:
    """Increment the usage count for a hook."""
    data = _load_hooks_bank()

    for hook in data["hooks"]:
        if hook["id"] == hook_id:
            hook["used_count"] = hook.get("used_count", 0) + 1
            _save_hooks_bank(data)
            return


# =============================================================================
# IDEAS BANK FUNCTIONS
# =============================================================================

def _load_ideas_bank() -> dict:
    """Load ideas bank from JSON file."""
    if not IDEAS_BANK_FILE.exists():
        return {"ideas": []}
    with open(IDEAS_BANK_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_ideas_bank(data: dict) -> None:
    """Save ideas bank to JSON file."""
    with open(IDEAS_BANK_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def save_idea_to_bank(idea: str, topic: str = None, angle: str = None) -> dict:
    """
    Save an idea to the ideas bank for future use.

    Args:
        idea: The idea/angle text
        topic: Original topic it relates to
        angle: The content pillar/angle (Personal, Expertise, Social Proof, etc.)

    Returns:
        The saved idea entry
    """
    data = _load_ideas_bank()

    entry = {
        "id": str(uuid.uuid4())[:8],
        "idea": idea,
        "topic": topic,
        "angle": angle,
        "created_at": datetime.now().isoformat(),
        "used_count": 0,
    }

    data["ideas"].insert(0, entry)
    _save_ideas_bank(data)

    return entry


def get_ideas_bank(topic: str = None) -> list[dict]:
    """
    Get all saved ideas, optionally filtered by topic.

    Args:
        topic: Filter by topic (partial match)

    Returns:
        List of idea entries
    """
    data = _load_ideas_bank()
    ideas = data["ideas"]

    if topic:
        ideas = [i for i in ideas if topic.lower() in (i.get("topic") or "").lower()]

    return ideas


def delete_idea_from_bank(idea_id: str) -> bool:
    """Delete an idea from the bank."""
    data = _load_ideas_bank()

    for i, idea in enumerate(data["ideas"]):
        if idea["id"] == idea_id:
            data["ideas"].pop(i)
            _save_ideas_bank(data)
            return True

    return False


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
