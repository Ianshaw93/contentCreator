"""
Generate content ideas/angles from a topic using the knowledge base.
This is the first step: Topic → Ideas → Hooks → Drafts
"""
import os
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

KNOWLEDGE_BASE_PATH = Path(__file__).parent.parent / "knowledge_bases"


def load_knowledge_base_for_ideas(client_name: str = "Smiths") -> dict:
    """Load knowledge base content for idea generation."""
    kb_path = KNOWLEDGE_BASE_PATH / client_name / "Written Posts"

    content = {
        "origin_story": "",
        "ip_extraction": "",
        "best_posts": "",
    }

    # Load origin story
    origin_file = kb_path / "Ian Origin Story 2.0.md"
    if origin_file.exists():
        content["origin_story"] = origin_file.read_text(encoding="utf-8")

    # Load IP extraction (pre-extracted text file for performance)
    ip_file = kb_path / "Ian Shaw IP Extraction (2).txt"
    if ip_file.exists():
        content["ip_extraction"] = ip_file.read_text(encoding="utf-8")

    # Load best posts
    best_posts_file = kb_path / "Smiths Ian Best Performing Posts.md"
    if best_posts_file.exists():
        content["best_posts"] = best_posts_file.read_text(encoding="utf-8")

    return content


SYSTEM_PROMPT = """You are a content strategist helping to generate LinkedIn post ideas.

Analyze the knowledge base (IP extraction, origin story, best posts) to find relevant:
- Personal stories and experiences that relate to the topic
- Expertise, frameworks, and insights that apply
- Lessons learned and transformations
- Contrarian or unique perspectives

Generate ideas across the content pillars:
- Personal: Stories, anecdotes, personal experiences
- Expertise: How-to's, frameworks, mental models, listicles
- Social Proof: Results, testimonials, proof of work
- Opinions: Contrarian takes, industry observations
- Trending: Timely angles on the topic
"""


def generate_ideas(topic: str, context: str = "", num_ideas: int = 15) -> list[dict]:
    """
    Generate content ideas/angles for a topic using the knowledge base.

    Args:
        topic: The topic/idea to explore
        context: Optional additional context
        num_ideas: Number of ideas to generate

    Returns:
        List of dicts with 'idea' and 'angle' keys
    """
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    kb = load_knowledge_base_for_ideas()

    user_prompt = f"""Generate {num_ideas} content ideas/angles for a LinkedIn post about: {topic}

KNOWLEDGE BASE:

--- IP EXTRACTION (expertise, knowledge, frameworks) ---
{kb['ip_extraction'][:6000]}

--- ORIGIN STORY (personal experiences, journey) ---
{kb['origin_story'][:4000]}

--- BEST PERFORMING POSTS (what resonates) ---
{kb['best_posts'][:3000]}
"""

    if context:
        user_prompt += f"\n--- ADDITIONAL CONTEXT ---\n{context}\n"

    user_prompt += f"""
Generate {num_ideas} unique content ideas that connect the topic to the knowledge base.
Each idea should be a specific angle or story that could become a post.

Format each idea on its own line:
1. [PILLAR] Idea description
2. [PILLAR] Idea description
...

Where PILLAR is one of: Personal, Expertise, Social Proof, Opinion, Trending

Example format:
1. [Personal] Share the story of when I struggled with X and how it taught me Y
2. [Expertise] Break down my 3-step framework for handling Z
3. [Opinion] Challenge the common belief that A leads to B
"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=3000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}]
    )

    # Parse response into list of ideas
    content = response.content[0].text
    ideas = []

    for line in content.strip().split("\n"):
        line = line.strip()
        if not line:
            continue

        # Try to parse numbered lines like "1. [Personal] idea text"
        for i in range(1, num_ideas + 2):
            prefixes = [f"{i}.", f"{i})", f"{i}:"]
            for prefix in prefixes:
                if line.startswith(prefix):
                    rest = line[len(prefix):].strip()

                    # Extract pillar if present
                    angle = None
                    idea_text = rest

                    if rest.startswith("["):
                        bracket_end = rest.find("]")
                        if bracket_end > 0:
                            angle = rest[1:bracket_end]
                            idea_text = rest[bracket_end + 1:].strip()

                    if idea_text:
                        ideas.append({
                            "idea": idea_text,
                            "angle": angle
                        })
                    break

    return ideas[:num_ideas]


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python generate_ideas.py 'topic'")
        sys.exit(1)

    topic = sys.argv[1]
    context = sys.argv[2] if len(sys.argv) > 2 else ""

    print(f"Generating ideas for: {topic}\n")
    ideas = generate_ideas(topic, context)

    print(f"Generated {len(ideas)} ideas:\n")
    for i, idea in enumerate(ideas, 1):
        angle = f"[{idea['angle']}]" if idea.get('angle') else ""
        print(f"{i}. {angle} {idea['idea']}\n")
