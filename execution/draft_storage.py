"""
Draft storage system - PostgreSQL-backed storage for LinkedIn post drafts, hooks, ideas, and insights.
"""
from datetime import datetime
from typing import Optional
import uuid

from database import SessionLocal, Draft, Hook, Idea, Insight, SocialProof


# =============================================================================
# HELPERS
# =============================================================================

def _draft_to_dict(row: Draft) -> dict:
    """Convert a Draft ORM object to dict matching the original JSON structure."""
    return {
        "id": row.id,
        "content": row.content or "",
        "hooks": row.hooks or [],
        "selected_hook": row.selected_hook,
        "template_used": row.template_used,
        "topic": row.topic,
        "status": row.status or "draft",
        "scheduled_time": row.scheduled_time,
        "posted_at": row.posted_at,
        "images": row.images or [],
        "metrics": row.metrics or {"impressions": None, "likes": None, "comments": None},
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _hook_to_dict(row: Hook) -> dict:
    return {
        "id": row.id,
        "hook": row.hook,
        "topic": row.topic,
        "created_at": row.created_at,
        "used_count": row.used_count or 0,
    }


def _idea_to_dict(row: Idea) -> dict:
    return {
        "id": row.id,
        "idea": row.idea,
        "topic": row.topic,
        "angle": row.angle,
        "created_at": row.created_at,
        "used_count": row.used_count or 0,
    }


def _insight_to_dict(row: Insight) -> dict:
    return {
        "id": row.id,
        "title": row.title,
        "content": row.content,
        "category": row.category,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


# =============================================================================
# DRAFT FUNCTIONS
# =============================================================================

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
    now = datetime.now().isoformat()
    draft = Draft(
        id=str(uuid.uuid4())[:8],
        content=content,
        hooks=hooks or [],
        selected_hook=selected_hook,
        template_used=template_used,
        topic=topic,
        status="draft",
        scheduled_time=None,
        posted_at=None,
        images=[],
        metrics={"impressions": None, "likes": None, "comments": None},
        created_at=now,
        updated_at=now,
    )

    with SessionLocal() as db:
        db.add(draft)
        db.commit()
        db.refresh(draft)
        return _draft_to_dict(draft)


def get_draft(draft_id: str) -> Optional[dict]:
    """Get a specific draft by ID."""
    with SessionLocal() as db:
        row = db.query(Draft).filter(Draft.id == draft_id).first()
        return _draft_to_dict(row) if row else None


def list_drafts(status: str = None, limit: int = None) -> list[dict]:
    """
    List all drafts, optionally filtered by status.

    Args:
        status: Filter by status (draft, scheduled, posted)
        limit: Maximum number of drafts to return

    Returns:
        List of draft dicts
    """
    with SessionLocal() as db:
        query = db.query(Draft).order_by(Draft.created_at.desc())
        if status:
            query = query.filter(Draft.status == status)
        if limit:
            query = query.limit(limit)
        return [_draft_to_dict(r) for r in query.all()]


def list_drafts_by_date(year: int, month: int) -> list[dict]:
    """
    List all drafts that are scheduled or posted in a given month.

    Args:
        year: Year (e.g., 2024)
        month: Month (1-12)

    Returns:
        List of draft dicts with their scheduled/posted dates
    """
    prefix = f"{year}-{month:02d}"
    with SessionLocal() as db:
        rows = db.query(Draft).filter(
            (Draft.scheduled_time.ilike(f"{prefix}%")) |
            (Draft.posted_at.ilike(f"{prefix}%"))
        ).all()
        return [_draft_to_dict(r) for r in rows]


def get_drafts_for_date(date_str: str) -> list[dict]:
    """
    Get all drafts scheduled or posted on a specific date.

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        List of draft dicts
    """
    with SessionLocal() as db:
        rows = db.query(Draft).filter(
            (Draft.scheduled_time.ilike(f"{date_str}%")) |
            (Draft.posted_at.ilike(f"{date_str}%"))
        ).all()
        return [_draft_to_dict(r) for r in rows]


def update_draft(draft_id: str, **updates) -> Optional[dict]:
    """
    Update a draft.

    Args:
        draft_id: The draft ID
        **updates: Fields to update (content, hooks, selected_hook, status, scheduled_time, posted_at, images)

    Returns:
        Updated draft dict or None if not found
    """
    with SessionLocal() as db:
        row = db.query(Draft).filter(Draft.id == draft_id).first()
        if not row:
            return None

        allowed_fields = {
            "content", "hooks", "selected_hook", "template_used", "topic",
            "status", "scheduled_time", "posted_at", "images", "metrics"
        }
        for key, value in updates.items():
            if key in allowed_fields:
                setattr(row, key, value)
        row.updated_at = datetime.now().isoformat()
        db.commit()
        db.refresh(row)
        return _draft_to_dict(row)


def delete_draft(draft_id: str) -> bool:
    """Delete a draft by ID."""
    with SessionLocal() as db:
        row = db.query(Draft).filter(Draft.id == draft_id).first()
        if not row:
            return False
        db.delete(row)
        db.commit()
        return True


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
    entry = Hook(
        id=str(uuid.uuid4())[:8],
        hook=hook,
        topic=topic,
        created_at=datetime.now().isoformat(),
        used_count=0,
    )

    with SessionLocal() as db:
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return _hook_to_dict(entry)


def get_hooks_bank(topic: str = None) -> list[dict]:
    """
    Get all saved hooks, optionally filtered by topic.

    Args:
        topic: Filter by topic (partial match)

    Returns:
        List of hook entries
    """
    with SessionLocal() as db:
        query = db.query(Hook).order_by(Hook.created_at.desc())
        if topic:
            query = query.filter(Hook.topic.ilike(f"%{topic}%"))
        return [_hook_to_dict(r) for r in query.all()]


def delete_hook_from_bank(hook_id: str) -> bool:
    """Delete a hook from the bank."""
    with SessionLocal() as db:
        row = db.query(Hook).filter(Hook.id == hook_id).first()
        if not row:
            return False
        db.delete(row)
        db.commit()
        return True


def increment_hook_usage(hook_id: str) -> None:
    """Increment the usage count for a hook."""
    with SessionLocal() as db:
        row = db.query(Hook).filter(Hook.id == hook_id).first()
        if row:
            row.used_count = (row.used_count or 0) + 1
            db.commit()


# =============================================================================
# IDEAS BANK FUNCTIONS
# =============================================================================

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
    entry = Idea(
        id=str(uuid.uuid4())[:8],
        idea=idea,
        topic=topic,
        angle=angle,
        created_at=datetime.now().isoformat(),
        used_count=0,
    )

    with SessionLocal() as db:
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return _idea_to_dict(entry)


def get_ideas_bank(topic: str = None) -> list[dict]:
    """
    Get all saved ideas, optionally filtered by topic.

    Args:
        topic: Filter by topic (partial match)

    Returns:
        List of idea entries
    """
    with SessionLocal() as db:
        query = db.query(Idea).order_by(Idea.created_at.desc())
        if topic:
            query = query.filter(Idea.topic.ilike(f"%{topic}%"))
        return [_idea_to_dict(r) for r in query.all()]


def delete_idea_from_bank(idea_id: str) -> bool:
    """Delete an idea from the bank."""
    with SessionLocal() as db:
        row = db.query(Idea).filter(Idea.id == idea_id).first()
        if not row:
            return False
        db.delete(row)
        db.commit()
        return True


# =============================================================================
# INSIGHTS BANK FUNCTIONS
# =============================================================================

def save_insight_to_bank(title: str, content: str, category: str = None) -> dict:
    """Save an insight to the bank."""
    now = datetime.now().isoformat()
    entry = Insight(
        id=str(uuid.uuid4())[:8],
        title=title,
        content=content,
        category=category,
        created_at=now,
        updated_at=now,
    )

    with SessionLocal() as db:
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return _insight_to_dict(entry)


def get_insights_bank(category: str = None) -> list[dict]:
    """Get all saved insights, optionally filtered by category."""
    with SessionLocal() as db:
        query = db.query(Insight).order_by(Insight.created_at.desc())
        if category:
            query = query.filter(Insight.category.ilike(f"%{category}%"))
        return [_insight_to_dict(r) for r in query.all()]


def get_insight(insight_id: str) -> Optional[dict]:
    """Get a single insight by ID."""
    with SessionLocal() as db:
        row = db.query(Insight).filter(Insight.id == insight_id).first()
        return _insight_to_dict(row) if row else None


def update_insight(insight_id: str, **updates) -> Optional[dict]:
    """Update an insight by ID."""
    with SessionLocal() as db:
        row = db.query(Insight).filter(Insight.id == insight_id).first()
        if not row:
            return None

        allowed_fields = {"title", "content", "category"}
        for key, value in updates.items():
            if key in allowed_fields:
                setattr(row, key, value)
        row.updated_at = datetime.now().isoformat()
        db.commit()
        db.refresh(row)
        return _insight_to_dict(row)


def delete_insight_from_bank(insight_id: str) -> bool:
    """Delete an insight from the bank."""
    with SessionLocal() as db:
        row = db.query(Insight).filter(Insight.id == insight_id).first()
        if not row:
            return False
        db.delete(row)
        db.commit()
        return True


def seed_insights_if_empty() -> int:
    """Seed insights bank with initial data if empty. Returns count of seeded items."""
    with SessionLocal() as db:
        if db.query(Insight).count() > 0:
            return 0

    seeds = [
        {
            "title": "Outreach Philosophy",
            "category": "Outreach",
            "content": """Here's what we do differently:

1. Actually look at who we're messaging
2. Find something specific and relevant to them
3. Look to learn their situation - to know how best to help
4. Follow up like a human, not a robot

We've scaled offers to $25k+ targeting CEOs/founders using this approach

Not because we had magic scripts.

Because we maintained a frame most people forget:

You're there to understand and help them where they're at.

If our client's service is the best fit? Great, let's explore.

If not? We STILL look to provide value/intros relevant to them"""
        },
        {
            "title": "Rebuilding Broken Outreach",
            "category": "Outreach",
            "content": """The problem?
- Copy-paste templates everyone could smell
- No systematic follow-ups
- Zero social proof on her profile

Everyone's numb to the same pitches they've seen 47 times this week.

So we rebuilt the entire approach:

We made it conversational. Actually looked at each prospect's situation. Asked questions. Listened.

We maintained one frame: we're here to genuinely help.

Whether that meant our client's services, free resources, or connecting them with someone valuable in our network."""
        },
        {
            "title": "Content System (AI + Taste)",
            "category": "Content",
            "content": """Not if you do it right.

Here's my system:

Step 1: Extract the client's real voice from 90+ min filmed interviews

Step 2: Generate 30 hooks per topic modelled on winning YouTube titles

Step 3: Kill anything that doesn't pass the gut check (taste)

Step 4: Build bodies using proven LinkedIn post formats

Step 5: Edit ruthlessly for voice against the original interviews

The key insight:

AI magnifies what's already winning.
But it can't build taste.

Taste is knowing which 3 out of 30 hooks would actually stop YOUR audience mid-scroll.

That's built over time. Through reps. Through studying what resonates and what falls flat.

Volume without taste = generic noise
Taste without volume = slow and exhausting"""
        },
        {
            "title": "Founder Leverage & Delegation",
            "category": "Founder",
            "content": """Then my body gave out. Eczema. Gut issues. Fatigue.

And you know what? The work still wasn't getting done properly.

Here's what I learned:
Automated tasks are the ultimate leverage
Failing that if you can pay someone 4x less than your hourly rate to do something, you should.

Not because you're lazy.

Because your job as a founder is strategy, not execution.

Every hour you spend writing posts is an hour not closing deals.

Every hour you spend managing DMs is an hour not improving your offer.

Dan Martell calls it "buying back your time."

The founders winning at content aren't creating it all themselves.

They have systems. Teams. AI where it makes sense.

They approve everything. They create nothing."""
        },
        {
            "title": "Find a Starving Crowd",
            "category": "Outreach",
            "content": """You make outreach a lot easier on yourself by finding a starving crowd.

No one's going to say "stop spamming me" when you are offering the answer to their deepest need.

Look for signals of that need."""
        },
        {
            "title": "Systems Over Hustle",
            "category": "Founder",
            "content": """We were doing everything manually.
Every DM. Every piece of content. Every follow-up.

The moment I brought on a third client, the first one dropped off.

I couldn't keep up. My health tanked. Eczema. Fatigue. The works.

So I pulled the plug. Rebuilt from scratch.

This time with systems. With AI where it made sense. With humans in the loop where it matters.

Now?

20 minutes of content input per week.
Follow-ups scheduled.
Admin automated.

Once someone responds?
A real human takes over.

The extra headspace lets me test messaging angles side by side and make decisions on real data."""
        },
    ]

    for seed in seeds:
        save_insight_to_bank(seed["title"], seed["content"], seed["category"])

    return len(seeds)


# =============================================================================
# SOCIAL PROOF FUNCTIONS
# =============================================================================

def _social_proof_to_dict(row: SocialProof) -> dict:
    return {
        "id": row.id,
        "metric": row.metric,
        "value": row.value,
        "context": row.context,
        "source": row.source,
        "category": row.category,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def save_social_proof(metric: str, value: str, context: str = None, source: str = None, category: str = None) -> dict:
    """Save a social proof entry."""
    now = datetime.now().isoformat()
    entry = SocialProof(
        id=str(uuid.uuid4())[:8],
        metric=metric,
        value=value,
        context=context,
        source=source,
        category=category,
        created_at=now,
        updated_at=now,
    )
    with SessionLocal() as db:
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return _social_proof_to_dict(entry)


def get_social_proof_bank(category: str = None) -> list[dict]:
    """Get all social proof entries, optionally filtered by category."""
    with SessionLocal() as db:
        query = db.query(SocialProof).order_by(SocialProof.created_at.desc())
        if category:
            query = query.filter(SocialProof.category.ilike(f"%{category}%"))
        return [_social_proof_to_dict(r) for r in query.all()]


def get_social_proof(proof_id: str) -> Optional[dict]:
    """Get a single social proof entry by ID."""
    with SessionLocal() as db:
        row = db.query(SocialProof).filter(SocialProof.id == proof_id).first()
        return _social_proof_to_dict(row) if row else None


def update_social_proof(proof_id: str, **updates) -> Optional[dict]:
    """Update a social proof entry."""
    with SessionLocal() as db:
        row = db.query(SocialProof).filter(SocialProof.id == proof_id).first()
        if not row:
            return None
        allowed_fields = {"metric", "value", "context", "source", "category"}
        for key, value in updates.items():
            if key in allowed_fields:
                setattr(row, key, value)
        row.updated_at = datetime.now().isoformat()
        db.commit()
        db.refresh(row)
        return _social_proof_to_dict(row)


def delete_social_proof(proof_id: str) -> bool:
    """Delete a social proof entry."""
    with SessionLocal() as db:
        row = db.query(SocialProof).filter(SocialProof.id == proof_id).first()
        if not row:
            return False
        db.delete(row)
        db.commit()
        return True


def seed_social_proof_if_empty() -> int:
    """Seed social proof bank with results from knowledge base if empty."""
    with SessionLocal() as db:
        if db.query(SocialProof).count() > 0:
            return 0

    seeds = [
        # Client Revenue Results
        {
            "metric": "Client Revenue",
            "value": "$25k/month",
            "context": "Scaled client targeting CEOs/founders on LinkedIn using conversational outreach approach",
            "source": "Client 1",
            "category": "Revenue",
        },
        {
            "metric": "Client Revenue",
            "value": "$35k+/month",
            "context": "Scaled Cam Beaudoin (serving speakers) including $15k one-off sales and retainers leading to higher LTV",
            "source": "Client 2 (Cam Beaudoin)",
            "category": "Revenue",
        },
        {
            "metric": "Client Revenue",
            "value": "$60k/month within 60 days",
            "context": "Scaled client to $60k within 60 days using our outreach system",
            "source": "Client 3",
            "category": "Revenue",
        },
        {
            "metric": "Clients Scaled to $25k+",
            "value": "Several clients",
            "context": "Scaled several clients to $25k+ through LinkedIn outreach",
            "source": "Portfolio",
            "category": "Revenue",
        },
        # Outreach Metrics
        {
            "metric": "Sales Calls Booked",
            "value": "5+ calls/week per client",
            "context": "Scaled clients to 5+ calls/week using conversational LinkedIn outreach",
            "source": "Client Results",
            "category": "Outreach",
        },
        # Personal Achievements
        {
            "metric": "AI Hackathon",
            "value": "2nd Place",
            "context": "Placed second in an AI hackathon without formal AI training",
            "source": "Personal",
            "category": "Credibility",
        },
    ]

    for seed in seeds:
        save_social_proof(**seed)

    return len(seeds)


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
