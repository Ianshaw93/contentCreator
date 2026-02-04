"""
Pre-process the Creator Hooks CSV to extract only useful data.
Reduces 712KB -> ~50KB by keeping only titles, frameworks, and hook scores.
"""
import re
from pathlib import Path

HOOKS_CSV = Path(__file__).parent.parent / "knowledge_bases" / "Hooks" / "Creator Hooks - Sheet1.csv"
HOOKS_CONDENSED = Path(__file__).parent.parent / "knowledge_bases" / "Hooks" / "hooks_condensed.txt"


def extract_hooks_from_csv() -> list[dict]:
    """Parse CSV and extract title, framework, hook score entries."""
    if not HOOKS_CSV.exists():
        return []

    content = HOOKS_CSV.read_text(encoding="utf-8")
    hooks = []

    # Pattern to find Title/Framework/Hook score blocks
    # Title: ...
    # Framework: ...
    # Hook score: +XXX or -XXX

    lines = content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line.startswith('Title:'):
            title = line[6:].strip()
            framework = ""
            score = ""

            # Look ahead for framework and score
            for j in range(i + 1, min(i + 10, len(lines))):
                next_line = lines[j].strip()
                if next_line.startswith('Framework:'):
                    framework = next_line[10:].strip()
                elif 'Hook score' in next_line:
                    # Score might be on next line
                    score_match = re.search(r'[+-]?\d+', next_line)
                    if score_match:
                        score = score_match.group()
                    elif j + 1 < len(lines):
                        score_match = re.search(r'[+-]?\d+', lines[j + 1])
                        if score_match:
                            score = score_match.group()
                elif next_line.startswith('Title:'):
                    break

            if title and (framework or score):
                hooks.append({
                    'title': title,
                    'framework': framework,
                    'score': score
                })
        i += 1

    return hooks


def create_condensed_file():
    """Create a condensed hooks reference file."""
    hooks = extract_hooks_from_csv()

    # Sort by score (highest first)
    def get_score(h):
        try:
            return int(h['score'].replace('+', ''))
        except:
            return 0

    hooks_sorted = sorted(hooks, key=get_score, reverse=True)

    # Build condensed output
    lines = ["# High-Performing Hook Examples (sorted by hook score)\n"]
    lines.append("Format: [Score] Title | Framework\n")
    lines.append("-" * 60 + "\n")

    seen_titles = set()
    for h in hooks_sorted:
        title = h['title']
        if title in seen_titles:
            continue
        seen_titles.add(title)

        score = h['score'] if h['score'] else "?"
        framework = h['framework'] if h['framework'] else ""

        if framework:
            lines.append(f"[{score}] {title}\n    Framework: {framework}\n")
        else:
            lines.append(f"[{score}] {title}\n")

    # Write condensed file
    HOOKS_CONDENSED.parent.mkdir(parents=True, exist_ok=True)
    HOOKS_CONDENSED.write_text(''.join(lines), encoding='utf-8')

    print(f"Extracted {len(seen_titles)} unique hooks")
    print(f"Output: {HOOKS_CONDENSED}")
    print(f"Size: {HOOKS_CONDENSED.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    create_condensed_file()
