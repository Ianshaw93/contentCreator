"""
AI Post Generator - Creates LinkedIn posts using knowledge base content.
"""
import os
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv
from prompts import POST_GENERATOR_SYSTEM

load_dotenv()

KNOWLEDGE_BASE_PATH = Path(__file__).parent.parent / "knowledge_bases"


def load_pdf_text(pdf_path: Path) -> str:
    """Extract text from a PDF file."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Warning: Could not read PDF {pdf_path}: {e}")
        return ""


def load_knowledge_base(client_name: str = "Smiths") -> dict:
    """
    Load knowledge base content for a client.

    Returns dict with:
        - origin_story: The client's origin story
        - ip_extraction: IP/expertise extraction content
        - best_posts: Examples of high-performing posts
        - templates: Post templates
    """
    kb_path = KNOWLEDGE_BASE_PATH / client_name / "Written Posts"

    content = {
        "origin_story": "",
        "ip_extraction": "",
        "best_posts": "",
        "templates": "",
    }

    # Load origin story
    origin_file = kb_path / "Ian Origin Story 2.0.md"
    if origin_file.exists():
        content["origin_story"] = origin_file.read_text(encoding="utf-8")

    # Load IP extraction (PDF)
    ip_file = kb_path / "Ian Shaw IP Extraction (2).pdf"
    if ip_file.exists():
        content["ip_extraction"] = load_pdf_text(ip_file)

    # Load best posts
    best_posts_file = kb_path / "Smiths Ian Best Performing Posts.md"
    if best_posts_file.exists():
        content["best_posts"] = best_posts_file.read_text(encoding="utf-8")

    # Load templates
    templates_file = kb_path / "LI Content Templates.md"
    if templates_file.exists():
        content["templates"] = templates_file.read_text(encoding="utf-8")

    return content


SYSTEM_PROMPT = POST_GENERATOR_SYSTEM


def generate_post_body(
    topic: str,
    hook: str,
    knowledge_base: dict = None,
    additional_context: str = None
) -> str:
    """
    Generate a LinkedIn post body based on a selected hook.

    Flow: Topic → Hooks (generated first) → User picks hook → This function generates body

    Args:
        topic: The topic/idea for the post
        hook: The selected hook to build the post around
        knowledge_base: Dict with origin_story, ip_extraction, best_posts, templates
        additional_context: Any additional context

    Returns:
        Generated post body (without the hook - hook is prepended separately)
    """
    if knowledge_base is None:
        knowledge_base = load_knowledge_base()

    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Build the user prompt
    ip_content = knowledge_base.get('ip_extraction', '')[:4000]
    user_prompt = f"""Create a LinkedIn post body for this topic and hook:

TOPIC: {topic}

HOOK (already written - build the post body to follow this):
{hook}

KNOWLEDGE BASE:

--- IP EXTRACTION (expertise and knowledge) ---
{ip_content}

--- BEST PERFORMING POSTS (match this style) ---
{knowledge_base['best_posts'][:4000]}

--- ORIGIN STORY (for personal context) ---
{knowledge_base['origin_story'][:3000]}

--- CONTENT TEMPLATES ---
{knowledge_base.get('templates', '')[:2000]}
"""

    if additional_context:
        user_prompt += f"\n--- ADDITIONAL CONTEXT ---\n{additional_context}\n"

    user_prompt += """
Write the POST BODY that follows the hook above. Include:
- Content that delivers on the hook's promise
- Bullet points where appropriate
- A strong closing/CTA

Return ONLY the body content (the hook will be prepended separately)."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}]
    )

    return response.content[0].text.strip()


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

    if len(sys.argv) < 3:
        print("Usage: python generate_post.py 'topic' 'selected hook'")
        print("\nExample:")
        print("  python generate_post.py 'AI coaching' 'Most coaches are afraid of AI. They shouldn't be.'")
        print("\nNote: Generate hooks first with: python generate_hooks.py 'topic'")
        sys.exit(1)

    topic = sys.argv[1]
    hook = sys.argv[2]
    print(f"Generating post body for topic: {topic}")
    print(f"Using hook: {hook}\n")

    # Load knowledge base
    kb = load_knowledge_base()
    print("Loaded knowledge base")

    # Generate post body
    print("Generating post body...\n")
    body = generate_post_body(topic, hook, kb)

    print("=" * 50)
    print("FULL POST:")
    print("=" * 50)
    print(f"{hook}\n")
    print(body)
