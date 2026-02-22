"""
Analyze a competitor's LinkedIn post using Claude API.
Extracts hook, classifies post type, and writes analysis notes.
"""
import json
import os

from anthropic import Anthropic
from draft_storage import POST_TYPES


def analyze_post(post_content: str) -> dict:
    """
    Analyze a competitor post and extract structured data.

    Returns:
        dict with keys: hook, post_type, notes
    """
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    type_list = ", ".join(POST_TYPES)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system="You are a LinkedIn content analyst. Respond ONLY with valid JSON, no markdown fences.",
        messages=[{
            "role": "user",
            "content": f"""Analyze this LinkedIn post and return JSON with exactly these keys:

- "hook": The verbatim opening line(s) that grab attention (copy exactly from the post)
- "post_type": Classify into ONE of: {type_list}
- "notes": 2-3 sentences on what makes this post effective (writing technique, structure, emotional triggers)

Post to analyze:
---
{post_content}
---

Return JSON only."""
        }]
    )

    text = response.content[0].text.strip()
    # Strip markdown fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        result = {"hook": "", "post_type": "", "notes": "AI analysis failed to parse."}

    return {
        "hook": result.get("hook", ""),
        "post_type": result.get("post_type", ""),
        "notes": result.get("notes", ""),
    }
