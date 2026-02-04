# LinkedIn Post Pipeline

## Overview
AI-powered LinkedIn content creation with knowledge base integration, draft management, and direct LinkedIn publishing.

## Architecture
```
Knowledge Base     →   AI Generation   →   Draft Storage   →   Review/Edit   →   Publish
(origin story,         (Claude API)        (.drafts.json)      (Web UI or      (LinkedIn)
 best posts,                                                    CLI)
 templates)
```

## Workflow Options

### Option 1: Web UI (Recommended)
```bash
python execution/workflow.py ui
# Opens http://localhost:5000
```
- Create AI posts from topics
- View and edit drafts
- Select hooks
- Post directly to LinkedIn

### Option 2: CLI
```bash
# Generate AI post from topic
python execution/workflow.py generate "AI coaching and the human element"

# List drafts
python execution/workflow.py list

# View a draft
python execution/workflow.py view <draft_id>

# Select a hook
python execution/workflow.py select <draft_id> B

# Post to LinkedIn
python execution/workflow.py post <draft_id>
```

### Option 3: Legacy (Manual Body)
```bash
python execution/create_draft.py "Your post body here..."
python execution/create_draft.py --file post.txt
```

## Scripts

### Core Workflow
- `execution/workflow.py` - Main CLI with all commands
- `execution/web_ui.py` - Web interface (Flask)

### AI Generation
- `execution/generate_post.py` - Full post generation using knowledge base
- `execution/generate_hooks.py` - Hook generation for existing content
- `execution/prompts.py` - AI prompts (do not modify without permission)

### Storage & Publishing
- `execution/draft_storage.py` - JSON-based draft management
- `execution/post_to_linkedin.py` - Direct LinkedIn posting
- `execution/linkedin_oauth.py` - LinkedIn OAuth setup (one-time)

## Knowledge Base
Located in `knowledge_bases/Smiths/Written Posts/`:
- `Ian Origin Story 2.0.md` - Personal background for authentic content
- `Smiths Ian Best Performing Posts.md` - Style reference
- `LI Content Templates.md` - Proven post templates

## Environment Variables
```bash
# Required
ANTHROPIC_API_KEY=     # Claude API for AI generation
LINKEDIN_CLIENT_ID=    # LinkedIn OAuth
LINKEDIN_CLIENT_SECRET=
```

## Draft Format
Drafts are stored in `.drafts.json`:
```json
{
  "id": "abc123",
  "content": "Post body...",
  "hooks": ["Hook A...", "Hook B...", ...],
  "selected_hook": 0,
  "topic": "AI Coaching",
  "status": "draft|scheduled|posted",
  "created_at": "2024-01-01T12:00:00",
  "updated_at": "2024-01-01T12:00:00"
}
```

## First-Time Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create `.env` file with API keys

3. (Optional) Set up LinkedIn OAuth:
   ```bash
   python execution/linkedin_oauth.py
   ```

4. Start creating:
   ```bash
   python execution/workflow.py ui
   ```

## Notes
- AI generation uses knowledge base for authentic, personalized content
- Hooks are optimized for scroll-stopping engagement
- Web UI provides full draft lifecycle management
- Direct LinkedIn API publishing (no third-party schedulers)
