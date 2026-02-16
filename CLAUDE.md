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

## Database
- **PostgreSQL** hosted on Railway (connection string in `DATABASE_URL` env var)
- **SQLAlchemy ORM** in `execution/database.py`
- **Models**: Draft, Hook, Idea, Insight, Image
- `create_tables()` runs on web UI startup (idempotent)
- `migrate_json_to_db()` one-time import from legacy JSON files (skips if tables have data)
- All storage functions in `draft_storage.py` and `image_storage.py` use DB sessions internally

## Principles
1. Check `execution/` for existing tools before writing new ones
2. Self-anneal: fix errors, update scripts, update directives
3. Never modify `execution/prompts.py` without permission
4. Be concise
