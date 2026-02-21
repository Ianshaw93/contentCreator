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

## Cross-Repo Knowledge Sharing

This project is part of a 3-repo system. Read `.claude/CROSS_REPO.md` for shared context (endpoints, data flows, conventions).

### Proactive Propagation

**After completing work, assess whether sibling repos need to know about it.** Propagate when you've created or changed:
- Content models or DB schema (shared database)
- Draft generation pipelines that feed into outreach messaging
- New skills that could benefit other repos
- Content performance metrics or hooks data that informs prospecting
- Conventions or patterns that apply across repos

### How to Propagate

1. Update `C:\Users\IanShaw\localProgramming\smiths\CROSS_REPO.md` (canonical source)
2. Copy to all repos: `cp ../CROSS_REPO.md .claude/CROSS_REPO.md` (and siblings)
3. If a sibling's CLAUDE.md needs project-specific updates, edit it directly
4. Commit and push in each affected repo

Or run `/sync-siblings` to follow the full workflow.
