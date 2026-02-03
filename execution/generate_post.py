"""
AI Post Generator - Creates LinkedIn posts using knowledge base content.
"""
import os
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

KNOWLEDGE_BASE_PATH = Path(__file__).parent.parent / "knowledge_bases"


def load_knowledge_base(client_name: str = "Smiths") -> dict:
    """
    Load knowledge base content for a client.

    Returns dict with:
        - origin_story: The client's origin story
        - best_posts: Examples of high-performing posts
        - templates: Post templates
    """
    kb_path = KNOWLEDGE_BASE_PATH / client_name / "Written Posts"

    content = {
        "origin_story": "",
        "best_posts": "",
        "templates": "",
    }

    # Load origin story
    origin_file = kb_path / "Ian Origin Story 2.0.md"
    if origin_file.exists():
        content["origin_story"] = origin_file.read_text(encoding="utf-8")

    # Load best posts
    best_posts_file = kb_path / "Smiths Ian Best Performing Posts.md"
    if best_posts_file.exists():
        content["best_posts"] = best_posts_file.read_text(encoding="utf-8")

    # Load templates
    templates_file = kb_path / "LI Content Templates.md"
    if templates_file.exists():
        content["templates"] = templates_file.read_text(encoding="utf-8")

    return content


SYSTEM_PROMPT = """You are an expert LinkedIn content strategist and ghostwriter for Ian Shaw.

Ian's background:
- Software developer turned entrepreneur and AI coach
- Spent 15 months traveling (Australia, NZ, South America) doing hard manual labor to fund it
- Placed second in an AI hackathon without formal AI training
- Focuses on helping coaches leverage AI and build personal brands
- Values: resilience, practical learning (just-in-time not just-in-case), overcoming comfort zones

His writing style:
- Uses short, punchy sentences and line breaks for readability
- Mixes personal stories with actionable advice
- Often uses "What people think vs What it actually is" format
- Includes bullet points with contrasts (before/after, wrong/right)
- Ends with motivational call-to-action
- No emojis (or very minimal)
- Authentic, direct tone - not salesy

When creating posts:
1. Draw from the knowledge base content provided
2. Match the style of his best-performing posts
3. Use proven templates when appropriate
4. Focus on one clear message per post
5. Include specific details and personal examples
6. Make it scroll-stopping from the first line"""


def generate_post(
    topic: str,
    knowledge_base: dict = None,
    template_name: str = None,
    additional_context: str = None
) -> str:
    """
    Generate a LinkedIn post on a topic using the knowledge base.

    Args:
        topic: The topic/theme for the post
        knowledge_base: Dict with origin_story, best_posts, templates
        template_name: Specific template to use (optional)
        additional_context: Any additional context or requirements

    Returns:
        Generated post content
    """
    if knowledge_base is None:
        knowledge_base = load_knowledge_base()

    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Build the user prompt
    user_prompt = f"""Create a LinkedIn post about: {topic}

KNOWLEDGE BASE:

--- BEST PERFORMING POSTS (match this style) ---
{knowledge_base['best_posts'][:4000]}

--- ORIGIN STORY (for personal context) ---
{knowledge_base['origin_story'][:3000]}
"""

    if template_name:
        user_prompt += f"\n--- USE THIS TEMPLATE ---\nTemplate: {template_name}\n"

    if additional_context:
        user_prompt += f"\n--- ADDITIONAL CONTEXT ---\n{additional_context}\n"

    user_prompt += """
Write a complete LinkedIn post ready to publish. Include:
- A compelling opening line (hook)
- The main body with bullet points where appropriate
- A strong closing/CTA

Return ONLY the post content, nothing else."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}]
    )

    return response.content[0].text.strip()


def generate_post_with_hooks(
    topic: str,
    knowledge_base: dict = None,
    num_hooks: int = 5
) -> tuple[str, list[str]]:
    """
    Generate a post body and multiple hook options.

    Args:
        topic: The topic/theme for the post
        knowledge_base: Knowledge base dict
        num_hooks: Number of hook options to generate

    Returns:
        Tuple of (post_body, list_of_hooks)
    """
    if knowledge_base is None:
        knowledge_base = load_knowledge_base()

    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # First generate the post body
    body_prompt = f"""Create a LinkedIn post body about: {topic}

STYLE REFERENCE (best performing posts):
{knowledge_base['best_posts'][:3000]}

PERSONAL CONTEXT:
{knowledge_base['origin_story'][:2000]}

Write the BODY of a LinkedIn post (everything EXCEPT the opening hook).
Include bullet points, insights, and a closing CTA.
Return ONLY the body content."""

    body_response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": body_prompt}]
    )

    post_body = body_response.content[0].text.strip()

    # Then generate multiple hooks
    hooks_prompt = f"""Generate {num_hooks} different opening hooks for this LinkedIn post:

POST BODY:
{post_body}

STYLE REFERENCE:
{knowledge_base['best_posts'][:2000]}

Create {num_hooks} different hooks using various styles:
- Question that sparks curiosity
- Controversial/contrarian take
- Personal story opener
- Surprising stat or fact
- Direct bold statement

Format as:
A: [hook 1]
B: [hook 2]
C: [hook 3]
D: [hook 4]
E: [hook 5]

Each hook should be 1-2 lines max. Make them scroll-stopping."""

    hooks_response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=800,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": hooks_prompt}]
    )

    # Parse hooks
    hooks = []
    for line in hooks_response.content[0].text.strip().split("\n"):
        line = line.strip()
        if line and line[0] in "ABCDE" and ":" in line:
            hook = line.split(":", 1)[1].strip()
            hooks.append(hook)

    return post_body, hooks[:num_hooks]


def list_templates() -> list[str]:
    """List available post templates."""
    templates = [
        "Simplify (Avoid/Instead)",
        "Generate Ideas For Hooks (Myths vs Reality)",
        "A Transformation (Timeline)",
        "Year vs Year Evolution",
        "Your #1 Niche Tip",
        "Something Crazy Happened",
        "Harsh Truth",
        "Comparative Changes",
        "Mindset Shift",
        "Give a Hack",
        "Struggles",
        "How To Grow",
        "Decision that Changed Your Life",
        "Skills and Experience",
        "Unique Failure",
        "What Works vs What Doesn't",
        "Stop and Start",
        "Step-By-Step Guide",
        "Lessons Learned",
        "Overnight Success",
    ]
    return templates


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python generate_post.py 'topic'")
        print("\nExample topics:")
        print("  - 'AI coaching and why human coaches still matter'")
        print("  - 'Overcoming fear of rejection in sales'")
        print("  - 'Building systems that scale'")
        sys.exit(1)

    topic = sys.argv[1]
    print(f"Generating post about: {topic}\n")

    # Load knowledge base
    kb = load_knowledge_base()
    print(f"Loaded knowledge base")

    # Generate post with hooks
    print("Generating post body and hooks...\n")
    body, hooks = generate_post_with_hooks(topic, kb)

    print("=" * 50)
    print("HOOK OPTIONS:")
    print("=" * 50)
    for i, hook in enumerate(hooks):
        print(f"{chr(65+i)}: {hook}\n")

    print("=" * 50)
    print("POST BODY:")
    print("=" * 50)
    print(body)
