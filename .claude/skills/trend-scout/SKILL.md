---
name: trend-scout
description: Discover trending topics relevant to B2B founders/coaches/consultants. Searches Reddit, Twitter/X, LinkedIn, and web via Perplexity Sonar API, then scores results through the ICP lens with Claude.
---

# /trend-scout - Weekly Trending Topic Discovery

Discover what's trending in the B2B founder/coach/consultant world and turn hot topics into content ideas.

## Workflow

### Step 1: Confirm Scope

Ask the user:
1. Any specific focus area? (e.g., "AI automation", "client acquisition", "personal branding") — or run the default broad scan
2. Time window preference? (default: this week's trends)
3. Platform priority? (Reddit, LinkedIn, Twitter/X, or all)

If the user provides focus areas via $ARGUMENTS, use those directly.

### Step 2: Run Trend Scout

```python
import sys
sys.path.insert(0, "execution")
from trend_scout import run_trend_scout

# For default scan:
result = run_trend_scout()

# For custom focus (build custom queries if user specified a focus):
# custom_queries = [
#     {"query": "Your custom query here", "platform": "reddit"},
#     {"query": "Another custom query", "platform": "web"},
# ]
# result = run_trend_scout(custom_queries=custom_queries)
```

### Step 3: Present Results

Show a table of discovered topics:

```
| # | Topic                          | Score | Platform | Summary                    |
|---|--------------------------------|-------|----------|----------------------------|
| 1 | AI replacing outbound sales    | 9/10  | reddit   | Founders debating whether.. |
| 2 | LinkedIn algorithm changes     | 8/10  | linkedin | New reach patterns...       |
```

For each topic, also show:
- Content angles (2-3 per topic)
- Source URLs if available

### Step 4: User Selection

Ask the user:
- Which topics to **keep** (mark as "reviewed")
- Which to **dismiss** (mark as "dismissed")
- Which to **convert to Ideas** immediately

```python
from draft_storage import update_trending_topic, convert_trend_to_idea

# Dismiss:
update_trending_topic(topic_id, status="dismissed")

# Convert to idea:
idea = convert_trend_to_idea(topic_id)
```

### Step 5: Optional — Chain into /idea

If user converted topics to ideas, offer to develop them further:
- "Want me to generate hooks for any of these ideas? I can run /idea on them."

## Important

- Requires `PERPLEXITY_API_KEY` in `.env` — get one from https://docs.perplexity.ai/
- Perplexity Sonar handles the web search; Claude handles scoring and angle extraction
- Results are saved to DB and visible at `/trending` in the web UI
- Default scan runs 5 queries in parallel (3 concurrent max to respect rate limits)
- Only topics scoring 5/10+ ICP relevance are kept
