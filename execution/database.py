import json
import os
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, Column, String, Text, Integer, DateTime, JSON
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# =============================================================================
# MODELS
# =============================================================================

class Draft(Base):
    __tablename__ = "drafts"

    id = Column(String, primary_key=True)
    content = Column(Text, nullable=False, default="")
    hooks = Column(JSON, default=list)
    selected_hook = Column(Integer, nullable=True)
    template_used = Column(String, nullable=True)
    topic = Column(String, nullable=True)
    status = Column(String, nullable=False, default="draft")
    scheduled_time = Column(String, nullable=True)
    posted_at = Column(String, nullable=True)
    images = Column(JSON, default=list)
    metrics = Column(JSON, default=dict)
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)


class Hook(Base):
    __tablename__ = "hooks"

    id = Column(String, primary_key=True)
    hook = Column(Text, nullable=False)
    topic = Column(String, nullable=True)
    created_at = Column(String, nullable=False)
    used_count = Column(Integer, default=0)


class Idea(Base):
    __tablename__ = "ideas"

    id = Column(String, primary_key=True)
    idea = Column(Text, nullable=False)
    topic = Column(String, nullable=True)
    angle = Column(String, nullable=True)
    created_at = Column(String, nullable=False)
    used_count = Column(Integer, default=0)


class Insight(Base):
    __tablename__ = "insights"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String, nullable=True)
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)


class Image(Base):
    __tablename__ = "images"

    id = Column(String, primary_key=True)
    original_name = Column(String, nullable=False)
    s3_key = Column(String, nullable=False)
    url = Column(String, nullable=False)
    uploaded_at = Column(String, nullable=False)


class SocialProof(Base):
    __tablename__ = "social_proof"

    id = Column(String, primary_key=True)
    metric = Column(String, nullable=False)
    value = Column(String, nullable=False)
    context = Column(Text, nullable=True)
    source = Column(String, nullable=True)
    category = Column(String, nullable=True)
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)


class CompetitorPost(Base):
    __tablename__ = "competitor_posts"

    id = Column(String, primary_key=True)
    competitor_name = Column(String, nullable=False)
    competitor_linkedin_url = Column(String, nullable=True)
    post_content = Column(Text, nullable=False)
    hook = Column(Text, nullable=True)
    post_type = Column(String, nullable=True)
    post_url = Column(String, nullable=True)
    likes = Column(Integer, nullable=True)
    comments = Column(Integer, nullable=True)
    reposts = Column(Integer, nullable=True)
    performance = Column(String, nullable=True)  # high / medium / low
    date_posted = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)


class TrendingTopic(Base):
    __tablename__ = "trending_topics"

    id = Column(String, primary_key=True)
    topic = Column(Text, nullable=False)
    summary = Column(Text)
    source_urls = Column(JSON, default=list)
    relevance_score = Column(Integer)         # 1-10 ICP relevance
    content_angles = Column(JSON, default=list)
    search_query = Column(String)
    batch_id = Column(String)                 # Groups results from same run
    status = Column(String, default="new")    # new/reviewed/used/dismissed
    source_platform = Column(String)          # reddit/twitter/linkedin/web
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)
    notes = Column(Text)


# =============================================================================
# HELPERS
# =============================================================================

def get_db():
    """Dependency for FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)


def migrate_json_to_db():
    """One-time migration: import existing JSON data into DB tables (skips if table has data)."""
    base_dir = Path(__file__).parent.parent

    drafts_file = base_dir / ".drafts.json"
    hooks_file = base_dir / ".hooks_bank.json"
    ideas_file = base_dir / ".ideas_bank.json"
    insights_file = base_dir / ".insights_bank.json"
    images_file = base_dir / ".image_library.json"

    with SessionLocal() as db:
        # Drafts
        if drafts_file.exists() and db.query(Draft).count() == 0:
            with open(drafts_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for d in data.get("drafts", []):
                db.add(Draft(
                    id=d["id"],
                    content=d.get("content", ""),
                    hooks=d.get("hooks", []),
                    selected_hook=d.get("selected_hook"),
                    template_used=d.get("template_used"),
                    topic=d.get("topic"),
                    status=d.get("status", "draft"),
                    scheduled_time=d.get("scheduled_time"),
                    posted_at=d.get("posted_at"),
                    images=d.get("images", []),
                    metrics=d.get("metrics", {"impressions": None, "likes": None, "comments": None}),
                    created_at=d.get("created_at", datetime.now().isoformat()),
                    updated_at=d.get("updated_at", datetime.now().isoformat()),
                ))
            db.commit()

        # Hooks
        if hooks_file.exists() and db.query(Hook).count() == 0:
            with open(hooks_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for h in data.get("hooks", []):
                db.add(Hook(
                    id=h["id"],
                    hook=h["hook"],
                    topic=h.get("topic"),
                    created_at=h.get("created_at", datetime.now().isoformat()),
                    used_count=h.get("used_count", 0),
                ))
            db.commit()

        # Ideas
        if ideas_file.exists() and db.query(Idea).count() == 0:
            with open(ideas_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for i in data.get("ideas", []):
                db.add(Idea(
                    id=i["id"],
                    idea=i["idea"],
                    topic=i.get("topic"),
                    angle=i.get("angle"),
                    created_at=i.get("created_at", datetime.now().isoformat()),
                    used_count=i.get("used_count", 0),
                ))
            db.commit()

        # Insights
        if insights_file.exists() and db.query(Insight).count() == 0:
            with open(insights_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for i in data.get("insights", []):
                db.add(Insight(
                    id=i["id"],
                    title=i["title"],
                    content=i["content"],
                    category=i.get("category"),
                    created_at=i.get("created_at", datetime.now().isoformat()),
                    updated_at=i.get("updated_at", datetime.now().isoformat()),
                ))
            db.commit()

        # Images
        if images_file.exists() and db.query(Image).count() == 0:
            with open(images_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for img in data.get("images", []):
                db.add(Image(
                    id=img["id"],
                    original_name=img["original_name"],
                    s3_key=img["s3_key"],
                    url=img["url"],
                    uploaded_at=img.get("uploaded_at", datetime.now().isoformat()),
                ))
            db.commit()
