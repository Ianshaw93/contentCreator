"""
Post directly to LinkedIn using the LinkedIn REST API (Posts API).
"""
import os
import json
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN_FILE = Path(__file__).parent.parent / ".linkedin_tokens.json"
LINKEDIN_API_VERSION = "202501"


def load_tokens() -> dict:
    """Load LinkedIn tokens from file."""
    if not TOKEN_FILE.exists():
        raise FileNotFoundError(
            "LinkedIn tokens not found. Run 'python execution/linkedin_oauth.py' first."
        )
    with open(TOKEN_FILE, "r") as f:
        return json.load(f)


def post_to_linkedin(content: str) -> dict:
    """
    Post content directly to LinkedIn using the Posts API.

    Args:
        content: The post content to publish

    Returns:
        API response dict
    """
    tokens = load_tokens()
    access_token = tokens["access_token"]
    person_id = tokens["person_id"]

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": LINKEDIN_API_VERSION,
    }

    # LinkedIn Posts API payload (newer API)
    payload = {
        "author": f"urn:li:person:{person_id}",
        "commentary": content,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": []
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False
    }

    response = requests.post(
        "https://api.linkedin.com/rest/posts",
        headers=headers,
        json=payload
    )

    if response.status_code == 201:
        return {
            "success": True,
            "post_id": response.headers.get("x-restli-id", "unknown"),
            "message": "Post published successfully!"
        }
    else:
        return {
            "success": False,
            "status_code": response.status_code,
            "error": response.text
        }


def check_token_validity() -> dict:
    """Check if the LinkedIn access token is still valid."""
    try:
        tokens = load_tokens()
        access_token = tokens["access_token"]

        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(
            "https://api.linkedin.com/v2/userinfo",
            headers=headers
        )

        if response.status_code == 200:
            user_info = response.json()
            return {
                "valid": True,
                "name": user_info.get("name", "Unknown"),
                "email": user_info.get("email", "Unknown")
            }
        else:
            return {
                "valid": False,
                "error": "Token expired or invalid. Run linkedin_oauth.py again."
            }
    except FileNotFoundError as e:
        return {"valid": False, "error": str(e)}


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        # Check token validity
        print("Checking LinkedIn token validity...")
        result = check_token_validity()
        if result["valid"]:
            print(f"Token is valid! Logged in as: {result['name']}")
        else:
            print(f"Token issue: {result['error']}")
        sys.exit(0)

    content = sys.argv[1]

    print("Posting to LinkedIn...")
    print(f"Content preview: {content[:100]}...")

    result = post_to_linkedin(content)

    if result["success"]:
        print(f"\nSuccess! Post ID: {result['post_id']}")
    else:
        print(f"\nFailed! Error: {result['error']}")
