"""Tests for trending topics feature: storage CRUD, trend scout pipeline, and web routes."""
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
    TREND_STATUSES, TREND_PLATFORMS,
    save_trending_topic, get_trending_topics, get_trending_topic,
    update_trending_topic, delete_trending_topic, get_trending_stats,
    convert_trend_to_idea, get_ideas_bank, delete_idea_from_bank,
)


class TestTrendingConstants:
    def test_statuses(self):
        assert "new" in TREND_STATUSES
        assert "reviewed" in TREND_STATUSES
        assert "used" in TREND_STATUSES
        assert "dismissed" in TREND_STATUSES

    def test_platforms(self):
        assert "reddit" in TREND_PLATFORMS
        assert "twitter" in TREND_PLATFORMS
        assert "linkedin" in TREND_PLATFORMS
        assert "web" in TREND_PLATFORMS


class TestTrendingTopicCRUD:
    """Test create, read, update, delete for trending topics."""

    def test_save_and_get(self):
        topic = save_trending_topic(
            topic="AI replacing cold outreach",
            summary="Founders debating whether AI will make cold DMs obsolete.",
            source_urls=["https://reddit.com/r/sales/123"],
            relevance_score=8,
            content_angles=["Share contrarian take", "Case study from client"],
            search_query="B2B founders AI outreach",
            batch_id="test-batch",
            source_platform="reddit",
        )
        assert topic["id"]
        assert topic["topic"] == "AI replacing cold outreach"
        assert topic["relevance_score"] == 8
        assert topic["status"] == "new"
        assert topic["source_platform"] == "reddit"
        assert len(topic["content_angles"]) == 2
        assert topic["batch_id"] == "test-batch"

        # Verify get by ID
        fetched = get_trending_topic(topic["id"])
        assert fetched is not None
        assert fetched["topic"] == "AI replacing cold outreach"

        # Cleanup
        delete_trending_topic(topic["id"])

    def test_update(self):
        topic = save_trending_topic(
            topic="Original topic",
            relevance_score=6,
            source_platform="web",
        )
        updated = update_trending_topic(
            topic["id"],
            status="reviewed",
            notes="Interesting angle for next week",
            relevance_score=9,
        )
        assert updated["status"] == "reviewed"
        assert updated["notes"] == "Interesting angle for next week"
        assert updated["relevance_score"] == 9

        # Cleanup
        delete_trending_topic(topic["id"])

    def test_delete(self):
        topic = save_trending_topic(topic="Topic to delete", source_platform="twitter")
        assert delete_trending_topic(topic["id"]) is True
        assert delete_trending_topic(topic["id"]) is False  # Already deleted

    def test_get_nonexistent_returns_none(self):
        assert get_trending_topic("nonexistent-id") is None

    def test_update_nonexistent_returns_none(self):
        assert update_trending_topic("nonexistent-id", status="reviewed") is None

    def test_filter_by_status(self):
        t1 = save_trending_topic(topic="New topic", source_platform="reddit")
        t2 = save_trending_topic(topic="Dismissed topic", source_platform="reddit")
        update_trending_topic(t2["id"], status="dismissed")

        new_topics = get_trending_topics(status="new")
        new_ids = [t["id"] for t in new_topics]
        assert t1["id"] in new_ids
        assert t2["id"] not in new_ids

        # Cleanup
        delete_trending_topic(t1["id"])
        delete_trending_topic(t2["id"])

    def test_filter_by_platform(self):
        t1 = save_trending_topic(topic="Reddit topic", source_platform="reddit")
        t2 = save_trending_topic(topic="LinkedIn topic", source_platform="linkedin")

        reddit = get_trending_topics(source_platform="reddit")
        reddit_ids = [t["id"] for t in reddit]
        assert t1["id"] in reddit_ids
        assert t2["id"] not in reddit_ids

        # Cleanup
        delete_trending_topic(t1["id"])
        delete_trending_topic(t2["id"])

    def test_filter_by_min_relevance(self):
        t1 = save_trending_topic(topic="High relevance", relevance_score=9, source_platform="web")
        t2 = save_trending_topic(topic="Low relevance", relevance_score=3, source_platform="web")

        high = get_trending_topics(min_relevance=8)
        high_ids = [t["id"] for t in high]
        assert t1["id"] in high_ids
        assert t2["id"] not in high_ids

        # Cleanup
        delete_trending_topic(t1["id"])
        delete_trending_topic(t2["id"])

    def test_filter_by_batch(self):
        t1 = save_trending_topic(topic="Batch A", batch_id="batch-a", source_platform="web")
        t2 = save_trending_topic(topic="Batch B", batch_id="batch-b", source_platform="web")

        batch_a = get_trending_topics(batch_id="batch-a")
        batch_a_ids = [t["id"] for t in batch_a]
        assert t1["id"] in batch_a_ids
        assert t2["id"] not in batch_a_ids

        # Cleanup
        delete_trending_topic(t1["id"])
        delete_trending_topic(t2["id"])

    def test_stats(self):
        t1 = save_trending_topic(topic="Topic 1", relevance_score=8, source_platform="reddit")
        t2 = save_trending_topic(topic="Topic 2", relevance_score=6, source_platform="reddit")
        t3 = save_trending_topic(topic="Topic 3", relevance_score=9, source_platform="linkedin")

        stats = get_trending_stats()
        assert stats["total"] >= 3
        assert stats["new_count"] >= 3
        assert stats["avg_relevance"] > 0
        assert stats["top_platform"] is not None

        # Cleanup
        delete_trending_topic(t1["id"])
        delete_trending_topic(t2["id"])
        delete_trending_topic(t3["id"])


class TestConvertTrendToIdea:
    def test_converts_and_marks_used(self):
        topic = save_trending_topic(
            topic="AI coaching tools trending",
            relevance_score=9,
            content_angles=["Share your AI stack", "Contrarian take on AI hype"],
            source_platform="twitter",
        )

        idea = convert_trend_to_idea(topic["id"])
        assert idea is not None
        assert idea["idea"] == "AI coaching tools trending"
        assert idea["topic"] == "Trending: twitter"
        assert idea["angle"] == "Share your AI stack"

        # Verify trend is marked as used
        updated_trend = get_trending_topic(topic["id"])
        assert updated_trend["status"] == "used"

        # Cleanup
        delete_trending_topic(topic["id"])
        delete_idea_from_bank(idea["id"])

    def test_convert_nonexistent_returns_none(self):
        assert convert_trend_to_idea("nonexistent-id") is None

    def test_convert_with_no_angles(self):
        topic = save_trending_topic(
            topic="Topic with no angles",
            source_platform="web",
        )

        idea = convert_trend_to_idea(topic["id"])
        assert idea is not None
        assert idea["angle"] is None

        # Cleanup
        delete_trending_topic(topic["id"])
        delete_idea_from_bank(idea["id"])


# =============================================================================
# PERPLEXITY API TESTS (mocked)
# =============================================================================

class TestPerplexitySearch:
    @patch("trend_scout.requests.post")
    @patch("trend_scout.PERPLEXITY_API_KEY", "test-key")
    def test_search_perplexity_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "AI outreach is trending..."}}],
            "citations": ["https://example.com/article"],
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        from trend_scout import _search_perplexity
        result = _search_perplexity("test query", "reddit")

        assert result["content"] == "AI outreach is trending..."
        assert result["citations"] == ["https://example.com/article"]
        assert result["platform"] == "reddit"
        assert result["query"] == "test query"

    @patch("trend_scout.requests.post")
    def test_search_perplexity_error_handling(self, mock_post):
        mock_post.side_effect = Exception("API timeout")

        from trend_scout import run_all_searches
        results = run_all_searches([{"query": "test", "platform": "web"}])

        assert len(results) == 1
        assert "error" in results[0]

    @patch("trend_scout.PERPLEXITY_API_KEY", None)
    def test_search_without_api_key(self):
        from trend_scout import _search_perplexity
        with pytest.raises(ValueError, match="PERPLEXITY_API_KEY"):
            _search_perplexity("test", "web")


# =============================================================================
# ICP SCORING TESTS (mocked Claude)
# =============================================================================

class TestICPScoring:
    @patch("trend_scout.Anthropic")
    def test_score_and_extract_topics(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(
            text='[{"topic": "AI outreach debate", "summary": "Founders debating AI in sales", "source_urls": ["https://example.com"], "relevance_score": 9, "content_angles": ["Share your take", "Client story"], "source_platform": "reddit"}]'
        )]
        mock_client.messages.create.return_value = mock_response

        from trend_scout import score_and_extract_topics
        search_results = [{
            "content": "Some search content about AI outreach",
            "citations": ["https://example.com"],
            "query": "test query",
            "platform": "reddit",
        }]

        topics = score_and_extract_topics(search_results)
        assert len(topics) == 1
        assert topics[0]["topic"] == "AI outreach debate"
        assert topics[0]["relevance_score"] == 9

    @patch("trend_scout.Anthropic")
    def test_score_handles_markdown_fences(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(
            text='```json\n[{"topic": "Test", "summary": "Test", "source_urls": [], "relevance_score": 7, "content_angles": ["Angle 1"], "source_platform": "web"}]\n```'
        )]
        mock_client.messages.create.return_value = mock_response

        from trend_scout import score_and_extract_topics
        topics = score_and_extract_topics([{
            "content": "Test content",
            "citations": [],
            "query": "test",
            "platform": "web",
        }])

        assert len(topics) == 1
        assert topics[0]["topic"] == "Test"

    @patch("trend_scout.Anthropic")
    def test_score_handles_invalid_json(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="not valid json at all")]
        mock_client.messages.create.return_value = mock_response

        from trend_scout import score_and_extract_topics
        topics = score_and_extract_topics([{
            "content": "Test",
            "citations": [],
            "query": "test",
            "platform": "web",
        }])

        assert topics == []

    def test_score_empty_results(self):
        from trend_scout import score_and_extract_topics
        # All results have errors — should return empty
        topics = score_and_extract_topics([{
            "content": "",
            "citations": [],
            "query": "test",
            "platform": "web",
            "error": "failed",
        }])
        assert topics == []


# =============================================================================
# ROUTE TESTS
# =============================================================================

from fastapi.testclient import TestClient
from web_ui import app

client = TestClient(app)


class TestTrendingRoutes:
    def test_trending_page_loads(self):
        resp = client.get("/trending")
        assert resp.status_code == 200
        assert "Trending Topics" in resp.text

    def test_trending_page_with_filters(self):
        resp = client.get("/trending?status=new&platform=reddit&min_relevance=8")
        assert resp.status_code == 200

    def test_convert_to_idea_route(self):
        topic = save_trending_topic(
            topic="Route test topic",
            relevance_score=8,
            content_angles=["Test angle"],
            source_platform="web",
        )

        resp = client.post(f"/trending/convert/{topic['id']}", follow_redirects=False)
        assert resp.status_code == 303

        # Verify trend is marked used
        updated = get_trending_topic(topic["id"])
        assert updated["status"] == "used"

        # Cleanup
        delete_trending_topic(topic["id"])
        # Also clean up the created idea
        ideas = get_ideas_bank(topic="Trending")
        for idea in ideas:
            if idea["idea"] == "Route test topic":
                delete_idea_from_bank(idea["id"])

    def test_convert_nonexistent_topic(self):
        resp = client.post("/trending/convert/nonexistent-id", follow_redirects=False)
        assert resp.status_code == 303
        assert "error" in resp.headers.get("location", "")

    def test_dismiss_route(self):
        topic = save_trending_topic(topic="Dismiss test", source_platform="reddit")

        resp = client.post(f"/trending/dismiss/{topic['id']}", follow_redirects=False)
        assert resp.status_code == 303

        updated = get_trending_topic(topic["id"])
        assert updated["status"] == "dismissed"

        # Cleanup
        delete_trending_topic(topic["id"])

    def test_update_notes_route(self):
        topic = save_trending_topic(topic="Notes test", source_platform="web")

        resp = client.post(
            f"/trending/update/{topic['id']}",
            data={"notes": "Important for next week"},
            follow_redirects=False,
        )
        assert resp.status_code == 303

        updated = get_trending_topic(topic["id"])
        assert updated["notes"] == "Important for next week"

        # Cleanup
        delete_trending_topic(topic["id"])

    def test_delete_route(self):
        topic = save_trending_topic(topic="Delete route test", source_platform="linkedin")

        resp = client.post(f"/trending/delete/{topic['id']}", follow_redirects=False)
        assert resp.status_code == 303

        assert get_trending_topic(topic["id"]) is None

    @patch("trend_scout.run_trend_scout")
    def test_scan_route(self, mock_scout):
        mock_scout.return_value = {
            "batch_id": "test-batch",
            "topics_found": 3,
            "topics_saved": 3,
            "topics": [],
        }

        resp = client.post("/trending/scan")
        assert resp.status_code == 200
        data = resp.json()
        assert data["batch_id"] == "test-batch"
        assert data["topics_saved"] == 3

    @patch("trend_scout.run_trend_scout", side_effect=Exception("API key missing"))
    def test_scan_route_error(self, mock_scout):
        resp = client.post("/trending/scan")
        assert resp.status_code == 500
        assert "error" in resp.json()

    def test_trending_nav_link_present(self):
        resp = client.get("/trending")
        assert 'href="/trending"' in resp.text
