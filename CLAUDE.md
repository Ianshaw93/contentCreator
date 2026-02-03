# Agent Instructions

3-layer architecture: Directives (what) → Orchestration (you) → Execution (Python scripts)

## File Structure
- `directives/` - SOPs in markdown
- `execution/` - Python scripts
- `.tmp/` - Intermediate files (gitignored)
- `.env` - API keys

## Principles
1. Check `execution/` for existing tools before writing new ones
2. Self-anneal: fix errors, update scripts, update directives
3. Never modify `execution/prompts.py` without permission
4. Be concise
