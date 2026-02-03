# LinkedIn Post Pipeline

## Overview
Generate LinkedIn posts with multiple hook options, push to Hypefury as drafts for human review.

## Flow
1. User generates post body in Claude Project
2. User pastes body into `create_draft.py`
3. Script generates 3-5 hook options via Claude API
4. Script assembles post (hooks at top + body) and pushes to Hypefury drafts
5. User reviews in Hypefury, picks hook, edits, schedules

## Input
- Post body text (from Claude Project)

## Output
- Hypefury draft with format:
```
[HOOK OPTIONS - delete the ones you don't want]
A: Hook option 1...
B: Hook option 2...
C: Hook option 3...
---

[POST BODY]
The actual post content...
```

## Scripts
- `execution/create_draft.py` - Main entry point, orchestrates the flow
- `execution/generate_hooks.py` - Generates hook options via Claude API
- `execution/push_to_hypefury.py` - Creates draft in Hypefury
- `execution/prompts.py` - All AI prompts (do not modify without permission)

## Environment Variables
- `ANTHROPIC_API_KEY` - For Claude API (hook generation)
- `HYPEFURY_API_KEY` - For Hypefury API

## Usage
```bash
python execution/create_draft.py "Your post body here..."
# or
python execution/create_draft.py --file post.txt
```

## Notes
- Hook generator focuses on scroll-stopping first lines
- Hooks should match user's voice/style (configure in prompts.py)
- Hypefury API: https://docs.hypefury.com/api
