"""
Trend Scout: Discover trending topics relevant to ICP (B2B founders/coaches/consultants).

Two-phase pipeline:
1. Parallel Perplexity Sonar searches across Reddit, LinkedIn, Twitter, web
2. Claude ICP scoring, deduplication, and content angle extraction

Results saved to TrendingTopic model in DB.
"""
import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import requests
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
PERPLEXITY_BASE_URL = "https://api.perplexity.ai"

# Pre-built ICP-relevant search queries
SEARCH_QUERIES = [
    {
        "query": "What are B2B founders, coaches, and consultants discussing on Reddit this week? Pain points, wins, and hot debates",
        "platform": "reddit",
    },
    {
        "query": "Trending LinkedIn discussions among founders, coaches, and consultants about scaling, personal branding, and client acquisition",
        "platform": "linkedin",
    },
    {
        "query": "Hot takes on AI for business, AI automation for coaches and consultants on social media this week",
        "platform": "twitter",
    },
    {
        "query": "Top pain points and challenges entrepreneurs and consultants are sharing on Reddit right now",
        "platform": "reddit",
    },
    {
        "query": "Content marketing and personal branding trends for B2B service providers and coaches in 2025-2026",
        "platform": "web",
    },
]


def _search_perplexity(query: str, platform: str) -> dict:
    """Run a single Perplexity Sonar search."""
    if not PERPLEXITY_API_KEY:
        raise ValueError("PERPLEXITY_API_KEY not set in .env")

    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "sonar",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a trend research assistant. Find trending topics, "
                    "discussions, and pain points relevant to B2B founders, coaches, "
                    "and consultants. Focus on actionable, specific trends — not generic advice."
                ),
            },
            {"role": "user", "content": query},
        ],
    }

    resp = requests.post(
        f"{PERPLEXITY_BASE_URL}/chat/completions",
        headers=headers,
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    content = data["choices"][0]["message"]["content"]
    citations = data.get("citations", [])

    return {
        "content": content,
        "citations": citations,
        "query": query,
        "platform": platform,
    }


def run_all_searches(custom_queries: list[dict] = None) -> list[dict]:
    """Run all search queries in parallel using ThreadPoolExecutor.

    Args:
        custom_queries: Optional list of {"query": str, "platform": str} dicts.
                       Falls back to SEARCH_QUERIES if not provided.

    Returns:
        List of search result dicts.
    """
    queries = custom_queries or SEARCH_QUERIES
    results = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(_search_perplexity, q["query"], q["platform"]): q
            for q in queries
        }
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                q = futures[future]
                print(f"Search failed for '{q['query'][:50]}...': {e}")
                results.append({
                    "content": "",
                    "citations": [],
                    "query": q["query"],
                    "platform": q["platform"],
                    "error": str(e),
                })

    return results


def score_and_extract_topics(search_results: list[dict]) -> list[dict]:
    """Use Claude to deduplicate, score for ICP relevance, and extract content angles.

    Args:
        search_results: Output from run_all_searches().

    Returns:
        List of scored topic dicts ready for DB insertion.
    """
    combined_text = ""
    for r in search_results:
        if r.get("error"):
            continue
        combined_text += f"\n\n--- Source: {r['platform']} (Query: {r['query']}) ---\n"
        combined_text += r["content"]
        if r.get("citations"):
            combined_text += "\nURLs: " + ", ".join(r["citations"])

    if not combined_text.strip():
        return []

    client = Anthropic()

    prompt = f"""Analyze these search results and extract distinct trending topics relevant to our ICP: B2B founders, coaches, and consultants who sell high-ticket services ($5k-$50k+).

SEARCH RESULTS:
{combined_text}

For each unique topic, provide:
1. topic: A concise topic title (max 10 words)
2. summary: 2-3 sentence summary of why this is trending
3. source_urls: Any relevant URLs from the citations
4. relevance_score: 1-10 score for ICP relevance (10 = perfectly relevant to B2B founders/coaches/consultants)
5. content_angles: 2-3 specific content angles Ian could use (e.g., "Share your contrarian take on X", "Story about how you solved Y for a client")
6. source_platform: Primary platform where this was found (reddit/twitter/linkedin/web)

Rules:
- Deduplicate similar topics
- Filter OUT anything below 5/10 relevance
- Focus on topics that would make good LinkedIn content
- Prefer specific, timely topics over generic evergreen advice

Return as JSON array:
[{{"topic": "...", "summary": "...", "source_urls": [...], "relevance_score": N, "content_angles": [...], "source_platform": "..."}}]

Return ONLY the JSON array, no other text."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()

    # Handle markdown fences
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        topics = json.loads(text)
    except json.JSONDecodeError:
        print(f"Failed to parse Claude response as JSON: {text[:200]}...")
        return []

    if not isinstance(topics, list):
        return []

    return topics


def run_trend_scout(custom_queries: list[dict] = None) -> dict:
    """Main entry point: run searches, score topics, save to DB.

    Args:
        custom_queries: Optional custom search queries.

    Returns:
        Summary dict with batch_id, topic count, and saved topics.
    """
    from draft_storage import save_trending_topic

    batch_id = str(uuid.uuid4())[:8]

    # Phase 1: Parallel Perplexity searches
    print("Phase 1: Running Perplexity searches...")
    search_results = run_all_searches(custom_queries)

    successful = [r for r in search_results if not r.get("error")]
    print(f"  {len(successful)}/{len(search_results)} searches succeeded")

    if not successful:
        return {"batch_id": batch_id, "topics_found": 0, "topics_saved": 0, "topics": []}

    # Phase 2: Claude ICP scoring
    print("Phase 2: Scoring and extracting topics with Claude...")
    scored_topics = score_and_extract_topics(search_results)
    print(f"  {len(scored_topics)} topics extracted (above relevance threshold)")

    # Phase 3: Save to DB
    saved = []
    for t in scored_topics:
        # Find which query produced this result
        search_query = None
        for r in search_results:
            if r["platform"] == t.get("source_platform"):
                search_query = r["query"]
                break

        topic = save_trending_topic(
            topic=t["topic"],
            summary=t.get("summary"),
            source_urls=t.get("source_urls", []),
            relevance_score=t.get("relevance_score"),
            content_angles=t.get("content_angles", []),
            search_query=search_query,
            batch_id=batch_id,
            source_platform=t.get("source_platform"),
        )
        saved.append(topic)

    print(f"  {len(saved)} topics saved to DB (batch: {batch_id})")

    return {
        "batch_id": batch_id,
        "topics_found": len(scored_topics),
        "topics_saved": len(saved),
        "topics": saved,
    }


if __name__ == "__main__":
    result = run_trend_scout()
    print(f"\nTrend Scout complete!")
    print(f"Batch ID: {result['batch_id']}")
    print(f"Topics saved: {result['topics_saved']}")
    for t in result["topics"]:
        print(f"  [{t['relevance_score']}/10] {t['topic']} ({t['source_platform']})")
