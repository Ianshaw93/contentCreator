"""
Generate hook options for a LinkedIn post using Claude API.
"""
import os
from anthropic import Anthropic
from prompts import HOOK_GENERATOR_SYSTEM, HOOK_GENERATOR_USER


def generate_hooks(post_body: str, num_hooks: int = 5) -> list[str]:
    """
    Generate hook options for a post body.

    Args:
        post_body: The main content of the LinkedIn post
        num_hooks: Number of hooks to generate (default 5)

    Returns:
        List of hook strings
    """
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=HOOK_GENERATOR_SYSTEM,
        messages=[
            {"role": "user", "content": HOOK_GENERATOR_USER.format(post_body=post_body)}
        ]
    )

    # Parse response into list of hooks
    content = response.content[0].text
    hooks = []
    for line in content.strip().split("\n"):
        line = line.strip()
        if line and line[0] in "ABCDE" and ":" in line:
            hook = line.split(":", 1)[1].strip()
            hooks.append(hook)

    return hooks[:num_hooks]


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv()

    if len(sys.argv) < 2:
        print("Usage: python generate_hooks.py 'post body text'")
        sys.exit(1)

    post_body = sys.argv[1]
    hooks = generate_hooks(post_body)

    print("Generated hooks:")
    for i, hook in enumerate(hooks):
        print(f"{chr(65+i)}: {hook}")
