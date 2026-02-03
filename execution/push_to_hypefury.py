"""
Push a draft post to Hypefury.
"""
import os
import requests


HYPEFURY_API_BASE = "https://api.hypefury.com/api/v1"


def create_draft(content: str) -> dict:
    """
    Create a draft post in Hypefury.

    Args:
        content: The full post content (hooks + body formatted)

    Returns:
        API response dict
    """
    api_key = os.getenv("HYPEFURY_API_KEY")
    if not api_key:
        raise ValueError("HYPEFURY_API_KEY not set in environment")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "content": content,
        "status": "draft"
    }

    response = requests.post(
        f"{HYPEFURY_API_BASE}/posts",
        headers=headers,
        json=payload
    )
    response.raise_for_status()

    return response.json()


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


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv()

    if len(sys.argv) < 2:
        print("Usage: python push_to_hypefury.py 'formatted post content'")
        sys.exit(1)

    content = sys.argv[1]
    result = create_draft(content)
    print(f"Draft created: {result}")
