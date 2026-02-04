# Agent Instructions

## Related Projects

This is part of a 3-project prospecting/outreach system:

| Project | Path | Purpose |
|---------|------|---------|
| **speed_to_lead** | `C:\Users\IanShaw\localProgramming\smiths\speed_to_lead` | Prospecting & lead tracking |
| **multichannel-outreach** | `C:\Users\IanShaw\localProgramming\smiths\multichannel-outreach` | Messaging & outreach automation |
| **contentCreator** | `C:\Users\IanShaw\localProgramming\smiths\contentCreator` | Content generation |

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
