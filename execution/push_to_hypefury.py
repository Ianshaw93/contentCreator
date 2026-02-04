"""
Push a post to Hypefury.

Note: Hypefury's external API only supports X/Twitter posts and scheduling.
It does NOT support:
- Creating drafts (posts are scheduled immediately)
- LinkedIn posts
- Reading back posts or analytics
"""
import os
import requests


HYPEFURY_API_BASE = "https://app.hypefury.com"
HYPEFURY_PARTNER_KEY = "NjhiNGQ1NWItOWFjNi00MDlkLWI2MjktNjhkNTk5OTNkZWQz"


def schedule_post(content: str) -> dict:
    """
    Schedule a post via Hypefury (X/Twitter only).

    Note: This schedules the post to the next available slot.
    Hypefury's API does not support creating drafts or LinkedIn posts.

    Args:
        content: The post content

    Returns:
        API response dict with postId
    """
    api_key = os.getenv("HYPEFURY_API_KEY")
    if not api_key:
        raise ValueError("HYPEFURY_API_KEY not set in environment")

    headers = {
        "Authorization": f"Bearer {HYPEFURY_PARTNER_KEY}:{api_key}",
        "Content-Type": "application/json"
    }

    payload = {"text": content}

    response = requests.post(
        f"{HYPEFURY_API_BASE}/api/externalApps/posts/save",
        headers=headers,
        json=payload
    )
    response.raise_for_status()

    return response.json()


def create_draft(content: str) -> dict:
    """
    Alias for schedule_post for backwards compatibility.

    Note: Despite the name, this actually SCHEDULES the post
    because Hypefury's API doesn't support true drafts.
    """
    return schedule_post(content)


def format_post_with_hooks(hooks: list[str], body: str) -> str:
    """
    Format the post with hook options at the top.

    Args:
        hooks: List of hook options
        body: Main post body

    Returns:
        Formatted post string
    """
    hook_section = "[HOOK OPTIONS - delete the ones you don't want]\n"
    for i, hook in enumerate(hooks):
        hook_section += f"{chr(65+i)}: {hook}\n"

    return f"{hook_section}---\n\n{body}"


def check_auth() -> dict:
    """Check if Hypefury authentication is valid."""
    api_key = os.getenv("HYPEFURY_API_KEY")
    if not api_key:
        return {"valid": False, "error": "HYPEFURY_API_KEY not set"}

    headers = {
        "Authorization": f"Bearer {HYPEFURY_PARTNER_KEY}:{api_key}",
        "Content-Type": "application/json"
    }

    response = requests.get(
        f"{HYPEFURY_API_BASE}/api/externalApps/auth",
        headers=headers
    )

    if response.status_code == 200:
        data = response.json()
        return {"valid": True, "twitter_user_id": data.get("twitterUserId")}
    else:
        return {"valid": False, "error": f"Auth failed: {response.status_code}"}


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv()

    if len(sys.argv) < 2:
        print("Checking Hypefury auth...")
        result = check_auth()
        if result["valid"]:
            print(f"Auth OK! Twitter User ID: {result['twitter_user_id']}")
        else:
            print(f"Auth failed: {result['error']}")
        print("\nNote: Hypefury API only supports X/Twitter, not LinkedIn.")
        sys.exit(0)

    content = sys.argv[1]
    print("Scheduling post to Hypefury (X/Twitter)...")
    result = schedule_post(content)
    print(f"Post scheduled: {result}")
