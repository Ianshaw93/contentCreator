# Agent Instructions

**Read `.claude/CROSS_REPO.md` first** — shared hard rules, routing table, and system facts for the 3-repo system. It is an auto-generated copy; the canonical file is `../CROSS_REPO.md` in the umbrella repo (which also has `DECISIONS.md` and step-by-step `playbooks/`).

## Related Projects

Part of a 3-project system under `C:\Users\IanShaw\Documents\localProgramming\smiths\LI_cross_repo\`:

| Project | Path | Purpose |
|---------|------|---------|
| **speed_to_lead** | `../speed_to_lead` | Prospecting & lead tracking (owns DB schema, deployment, ALL API endpoints) |
| **multichannel-outreach** | `../multichannel-outreach` | Messaging & outreach automation |
| **contentCreator** | (this repo) | Content generation |

3-layer architecture: Directives (`directives/`, what) → Orchestration (you) → Execution (`execution/`, deterministic Python).

## Current Strategy Constraint (2026-07-07)

**No content engine gets built before the first client is signed. YouTube is upload-only.** Don't re-litigate or start building content-production systems without an explicit trigger from Ian. See `../DECISIONS.md`.

## File Structure

- `directives/` — SOPs in markdown
- `execution/` — Python scripts
- `.tmp/` — Intermediate files (gitignored)
- `.env` — API keys

## Database

- Shared Railway PostgreSQL (same instance as speed_to_lead) — connection procedure: `../playbooks/query-funnel-state.md`
- SQLAlchemy ORM in `execution/database.py`; models: Draft, Hook, Idea, Insight, Image
- `create_tables()` runs on web UI startup (idempotent). This is a legacy exception — new shared-schema changes go through speed_to_lead's Alembic (CROSS_REPO.md rule 3).
- Storage functions in `draft_storage.py` / `image_storage.py` use DB sessions internally

## Principles

1. Check `execution/` for existing tools before writing new ones
2. Self-anneal: fix errors, update scripts, update directives
3. Never modify `execution/prompts.py` without permission
4. Be concise
5. **Log costs** for any paid action to the speed_to_lead DB (CROSS_REPO.md "Cost Tracking")
6. **Assess health check needs after building** any new data flow: `../playbooks/add-health-check.md`

## Cross-Repo Propagation

After completing work, assess whether siblings need to know (content models / schema, pipelines feeding outreach, conventions). Run `/sync-siblings`: edit the canonical `../CROSS_REPO.md`, log decisions in `../DECISIONS.md`, regenerate copies with `../sync_cross_repo.sh`. Never hand-edit `.claude/CROSS_REPO.md`.
