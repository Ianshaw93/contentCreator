"""
Post directly to LinkedIn using the LinkedIn REST API (Posts API).
Supports text posts and image attachments.
"""
import os
import json
from pathlib import Path
from typing import Optional
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


def _get_headers(access_token: str, content_type: str = "application/json") -> dict:
    """Get standard headers for LinkedIn API calls."""
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": content_type,
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": LINKEDIN_API_VERSION,
    }


def register_image_upload(access_token: str, person_id: str) -> dict:
    """
    Register an image upload with LinkedIn.

    Returns:
        Dict with 'upload_url' and 'image_urn'
    """
    headers = _get_headers(access_token)

    payload = {
        "initializeUploadRequest": {
            "owner": f"urn:li:person:{person_id}"
        }
    }

    response = requests.post(
        "https://api.linkedin.com/rest/images?action=initializeUpload",
        headers=headers,
        json=payload
    )

    if response.status_code != 200:
        raise Exception(f"Failed to register image upload: {response.text}")

    data = response.json()
    return {
        "upload_url": data["value"]["uploadUrl"],
        "image_urn": data["value"]["image"]
    }


def upload_image_binary(upload_url: str, image_data: bytes, content_type: str, access_token: str) -> bool:
    """
    Upload image binary to LinkedIn's upload URL.

    Args:
        upload_url: The URL returned from register_image_upload
        image_data: Raw image bytes
        content_type: MIME type of the image
        access_token: LinkedIn access token

    Returns:
        True if successful
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": content_type,
    }

    response = requests.put(upload_url, headers=headers, data=image_data)

    if response.status_code not in [200, 201]:
        raise Exception(f"Failed to upload image: {response.status_code} - {response.text}")

    return True


def _download_image_from_url(url: str) -> tuple[bytes, str]:
    """
    Download an image from a URL and return (bytes, content_type).
    """
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    content_type = resp.headers.get("Content-Type", "image/jpeg")
    return resp.content, content_type


def _guess_content_type(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }.get(ext, "image/jpeg")


def upload_image_to_linkedin(image_source) -> str:
    """
    Complete image upload flow to LinkedIn.

    Args:
        image_source: Either a Path to a local file, or a URL string (http/https)

    Returns:
        The image URN to use in post
    """
    tokens = load_tokens()
    access_token = tokens["access_token"]
    person_id = tokens["person_id"]

    # Step 1: Register upload
    upload_info = register_image_upload(access_token, person_id)

    # Step 2: Get image bytes
    if isinstance(image_source, str) and image_source.startswith("http"):
        image_data, content_type = _download_image_from_url(image_source)
    else:
        image_path = Path(image_source)
        with open(image_path, "rb") as f:
            image_data = f.read()
        content_type = _guess_content_type(image_path)

    # Step 3: Upload binary
    upload_image_binary(upload_info["upload_url"], image_data, content_type, access_token)

    return upload_info["image_urn"]


def post_to_linkedin(content: str, image_sources: list = None) -> dict:
    """
    Post content directly to LinkedIn using the Posts API.

    Args:
        content: The post content to publish
        image_sources: Optional list of image file paths (Path) or S3 URLs (str)

    Returns:
        API response dict
    """
    tokens = load_tokens()
    access_token = tokens["access_token"]
    person_id = tokens["person_id"]

    headers = _get_headers(access_token)

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

    # Handle image attachments (accepts Paths or URL strings)
    if image_sources:
        try:
            image_urns = []
            for image_source in image_sources:
                # Support both local paths and S3 URLs
                if isinstance(image_source, str) and image_source.startswith("http"):
                    urn = upload_image_to_linkedin(image_source)
                    image_urns.append(urn)
                elif hasattr(image_source, "exists") and image_source.exists():
                    urn = upload_image_to_linkedin(image_source)
                    image_urns.append(urn)

            if image_urns:
                # Add image content to payload
                if len(image_urns) == 1:
                    # Single image
                    payload["content"] = {
                        "media": {
                            "id": image_urns[0]
                        }
                    }
                else:
                    # Multiple images (carousel)
                    payload["content"] = {
                        "multiImage": {
                            "images": [{"id": urn} for urn in image_urns]
                        }
                    }
        except Exception as e:
            return {
                "success": False,
                "error": f"Image upload failed: {str(e)}"
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
