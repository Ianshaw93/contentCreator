"""
Generate hook options for a LinkedIn post using Claude API.
Hooks are generated FIRST from a topic, then the post body is written based on the selected hook.
"""
import os
from pathlib import Path
from anthropic import Anthropic
from prompts import HOOK_GENERATOR_SYSTEM

HOOKS_CONDENSED_PATH = Path(__file__).parent.parent / "knowledge_bases" / "Hooks" / "hooks_condensed.txt"
HOOKS_CSV_PATH = Path(__file__).parent.parent / "knowledge_bases" / "Hooks" / "Creator Hooks - Sheet1.csv"


def load_hooks_knowledge_base(max_examples: int = 100) -> str:
    """
    Load condensed hooks reference material.

    Args:
        max_examples: Limit number of hook examples to include (default 100).
                     Set to 0 for no limit.
    """
    # Prefer condensed file (35KB vs 712KB)
    if HOOKS_CONDENSED_PATH.exists():
        content = HOOKS_CONDENSED_PATH.read_text(encoding="utf-8")

        if max_examples > 0:
            # Limit to top N examples (already sorted by score)
            lines = content.split('\n')
            header_lines = []
            example_lines = []
            example_count = 0

            for line in lines:
                if line.startswith('[') and example_count < max_examples:
                    example_lines.append(line)
                    example_count += 1
                elif line.startswith('    Framework:') and example_count <= max_examples:
                    example_lines.append(line)
                elif example_count == 0:
                    header_lines.append(line)

            return '\n'.join(header_lines + example_lines)

        return content

    return ""


def generate_hooks(topic: str, context: str = "", num_hooks: int = 30) -> list[str]:
    """
    Generate hook options for a topic/idea.

    Args:
        topic: The topic/idea for the post
        context: Optional additional context
        num_hooks: Number of hooks to generate (default 5)

    Returns:
        List of hook strings
    """
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Load hooks knowledge base
    hooks_kb = load_hooks_knowledge_base()

    # Build system prompt with knowledge base
    system_prompt = HOOK_GENERATOR_SYSTEM
    if hooks_kb:
        system_prompt += f"\n\n--- CREATOR HOOKS REFERENCE (higher hook scores = better performance) ---\n{hooks_kb}"

    # Build user prompt
    user_prompt = f"""Generate {num_hooks} different opening hooks for a LinkedIn post about: {topic}"""
    if context:
        user_prompt += f"\n\nAdditional context: {context}"

    user_prompt += f"""

Create {num_hooks} unique, scroll-stopping hooks. Each hook should be 1-2 lines max.
Vary the styles: questions, bold statements, stories, numbers/stats, contrarian takes, warnings, etc.

Format each hook on its own line, numbered 1-{num_hooks}:
1. [hook]
2. [hook]
...
{num_hooks}. [hook]"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )

    # Parse response into list of hooks
    content = response.content[0].text
    hooks = []
    for line in content.strip().split("\n"):
        line = line.strip()
        # Match lines starting with number followed by . or )
        if line and len(line) > 2:
            # Try to extract hook after number prefix
            for i in range(1, num_hooks + 1):
                prefixes = [f"{i}.", f"{i})", f"{i}:"]
                for prefix in prefixes:
                    if line.startswith(prefix):
                        hook = line[len(prefix):].strip()
                        if hook:
                            hooks.append(hook)
                        break

    return hooks[:num_hooks]


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv()

    if len(sys.argv) < 2:
        print("Usage: python generate_hooks.py 'topic/idea' ['optional context']")
        sys.exit(1)

    topic = sys.argv[1]
    context = sys.argv[2] if len(sys.argv) > 2 else ""
    hooks = generate_hooks(topic, context)

    print(f"Generated hooks for: {topic}\n")
    for i, hook in enumerate(hooks):
        print(f"{chr(65+i)}: {hook}")
