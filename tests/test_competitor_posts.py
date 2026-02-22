"""Tests for competitor posts feature: storage CRUD, AI analysis, and web routes."""
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add execution dir to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent / "execution"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")


# =============================================================================
# STORAGE CRUD TESTS
# =============================================================================

from draft_storage import (
    COMPETITORS, POST_TYPES, save_competitor_post, get_competitor_posts,
    update_competitor_post, delete_competitor_post, get_competitor_names,
    get_competitor_stats,
)


class TestCompetitorConstants:
    def test_competitors_list_has_five(self):
        assert len(COMPETITORS) == 5

    def test_competitor_names(self):
        names = get_competitor_names()
        assert "Aidan Collins" in names
        assert "Cameron Trew" in names
        assert "Naim Ahmed" in names
        assert "Lara Acosta" in names
        assert "Chase Dimond" in names

    def test_post_types_not_empty(self):
        assert len(POST_TYPES) > 0
        assert "Story" in POST_TYPES
        assert "How-to" in POST_TYPES


class TestCompetitorPostCRUD:
    """Test create, read, update, delete for competitor posts."""

    def test_save_and_get(self):
        post = save_competitor_post(
            competitor_name="Aidan Collins",
            post_content="Test post content about growth hacking.",
            hook="Growth hacking is dead.",
            post_type="Contrarian",
            likes=150,
            performance="high",
        )
        assert post["id"]
        assert post["competitor_name"] == "Aidan Collins"
        assert post["post_content"] == "Test post content about growth hacking."
        assert post["hook"] == "Growth hacking is dead."
        assert post["post_type"] == "Contrarian"
        assert post["likes"] == 150
        assert post["performance"] == "high"
        assert post["competitor_linkedin_url"] is not None

        # Verify it appears in get
        posts = get_competitor_posts(competitor_name="Aidan Collins")
        ids = [p["id"] for p in posts]
        assert post["id"] in ids

        # Cleanup
        delete_competitor_post(post["id"])

    def test_update(self):
        post = save_competitor_post(
            competitor_name="Cameron Trew",
            post_content="Original content.",
        )
        updated = update_competitor_post(post["id"], hook="New hook line", post_type="Story", likes=200)
        assert updated["hook"] == "New hook line"
        assert updated["post_type"] == "Story"
        assert updated["likes"] == 200

        # Cleanup
        delete_competitor_post(post["id"])

    def test_delete(self):
        post = save_competitor_post(
            competitor_name="Naim Ahmed",
            post_content="Post to delete.",
        )
        assert delete_competitor_post(post["id"]) is True
        assert delete_competitor_post(post["id"]) is False  # Already deleted

    def test_filter_by_post_type(self):
        p1 = save_competitor_post(competitor_name="Lara Acosta", post_content="Story post", post_type="Story")
        p2 = save_competitor_post(competitor_name="Chase Dimond", post_content="List post", post_type="List")

        stories = get_competitor_posts(post_type="Story")
        story_ids = [p["id"] for p in stories]
        assert p1["id"] in story_ids
        assert p2["id"] not in story_ids

        # Cleanup
        delete_competitor_post(p1["id"])
        delete_competitor_post(p2["id"])

    def test_filter_by_performance(self):
        p1 = save_competitor_post(competitor_name="Aidan Collins", post_content="High post", performance="high")
        p2 = save_competitor_post(competitor_name="Aidan Collins", post_content="Low post", performance="low")

        high = get_competitor_posts(performance="high")
        high_ids = [p["id"] for p in high]
        assert p1["id"] in high_ids
        assert p2["id"] not in high_ids

        # Cleanup
        delete_competitor_post(p1["id"])
        delete_competitor_post(p2["id"])

    def test_stats(self):
        p1 = save_competitor_post(competitor_name="Aidan Collins", post_content="Post 1", post_type="Story")
        p2 = save_competitor_post(competitor_name="Aidan Collins", post_content="Post 2", post_type="Story")
        p3 = save_competitor_post(competitor_name="Cameron Trew", post_content="Post 3", post_type="List")

        stats = get_competitor_stats()
        assert stats["total"] >= 3
        # Aidan has 2 posts, should be top performer (or at least included)
        assert stats["top_performer"] is not None
        assert stats["most_common_type"] is not None

        # Cleanup
        delete_competitor_post(p1["id"])
        delete_competitor_post(p2["id"])
        delete_competitor_post(p3["id"])

    def test_update_nonexistent_returns_none(self):
        result = update_competitor_post("nonexistent-id", hook="test")
        assert result is None


# =============================================================================
# AI ANALYSIS TESTS (mocked)
# =============================================================================

class TestAnalyzeCompetitorPost:
    @patch("analyze_competitor_post.Anthropic")
    def test_analyze_post_returns_structured(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(
            text='{"hook": "Growth hacking is dead.", "post_type": "Contrarian", "notes": "Uses a bold opening statement to challenge conventional wisdom."}'
        )]
        mock_client.messages.create.return_value = mock_response

        from analyze_competitor_post import analyze_post
        result = analyze_post("Growth hacking is dead.\n\nHere's why everyone gets it wrong...")

        assert result["hook"] == "Growth hacking is dead."
        assert result["post_type"] == "Contrarian"
        assert "bold" in result["notes"].lower() or len(result["notes"]) > 0

    @patch("analyze_competitor_post.Anthropic")
    def test_analyze_post_handles_markdown_fences(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(
            text='```json\n{"hook": "Test hook", "post_type": "Story", "notes": "Good story."}\n```'
        )]
        mock_client.messages.create.return_value = mock_response

        from analyze_competitor_post import analyze_post
        result = analyze_post("Some post content")

        assert result["hook"] == "Test hook"
        assert result["post_type"] == "Story"

    @patch("analyze_competitor_post.Anthropic")
    def test_analyze_post_handles_invalid_json(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='not valid json')]
        mock_client.messages.create.return_value = mock_response

        from analyze_competitor_post import analyze_post
        result = analyze_post("Some post")

        assert "hook" in result
        assert "post_type" in result
        assert "notes" in result


# =============================================================================
# ROUTE TESTS
# =============================================================================

from fastapi.testclient import TestClient
from web_ui import app

client = TestClient(app)


class TestCompetitorRoutes:
    def test_competitors_page_loads(self):
        resp = client.get("/competitors")
        assert resp.status_code == 200
        assert "Competitor Posts" in resp.text

    def test_add_and_delete_competitor_post(self):
        # Add
        resp = client.post("/competitors/add", data={
            "competitor_name": "Aidan Collins",
            "post_content": "Route test post content.",
            "hook": "Test hook",
            "post_type": "Story",
            "post_url": "",
            "date_posted": "",
            "likes": "50",
            "comments": "",
            "reposts": "",
            "performance": "high",
            "notes": "Test notes",
        }, follow_redirects=False)
        assert resp.status_code == 303

        # Verify it shows up
        resp = client.get("/competitors")
        assert "Route test post content." in resp.text

        # Find the post ID from the page to delete it
        import re
        match = re.search(r'/competitors/delete/([a-f0-9-]+)', resp.text)
        assert match, "Could not find delete link"
        post_id = match.group(1)

        # Delete
        resp = client.post(f"/competitors/delete/{post_id}", follow_redirects=False)
        assert resp.status_code == 303

    def test_update_competitor_post_route(self):
        # Create a post first
        post = save_competitor_post(
            competitor_name="Lara Acosta",
            post_content="Update route test.",
        )

        resp = client.post(f"/competitors/update/{post['id']}", data={
            "competitor_name": "Lara Acosta",
            "post_content": "Updated via route.",
            "hook": "Updated hook",
            "post_type": "Framework",
            "post_url": "",
            "date_posted": "",
            "likes": "",
            "comments": "",
            "reposts": "",
            "performance": "",
            "notes": "",
        }, follow_redirects=False)
        assert resp.status_code == 303

        # Cleanup
        delete_competitor_post(post["id"])

    def test_filters_applied(self):
        resp = client.get("/competitors?competitor=Aidan+Collins&type=Story&performance=high")
        assert resp.status_code == 200

    @patch("web_ui.analyze_post")
    def test_analyze_endpoint(self, mock_analyze):
        mock_analyze.return_value = {
            "hook": "AI hook",
            "post_type": "How-to",
            "notes": "Great structure.",
        }
        resp = client.post("/competitors/analyze", json={"post_content": "Some test post"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["hook"] == "AI hook"
        assert data["post_type"] == "How-to"

    def test_analyze_endpoint_empty_content(self):
        resp = client.post("/competitors/analyze", json={"post_content": ""})
        assert resp.status_code == 400
