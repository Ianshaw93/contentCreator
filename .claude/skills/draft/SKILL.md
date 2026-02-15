---
name: draft
description: Generate a full LinkedIn post draft from a given hook. Use when you already have a hook and want to turn it into a complete post.
---

# /draft - Create a Post from a Hook

Takes a hook and turns it into a full LinkedIn post draft.

## Context About Ian's Offer

Ian helps B2B founders/coaches/consultants scale their high-ticket offers by:
- Building their personal brand on LinkedIn
- Creating content systems (so they work ON not IN their content)
- Running outreach systems that book sales calls
- Using AI to amplify (not replace) human expertise

Key results: Scaled clients to $25k-$60k/month, 4+ calls/week booked

## Workflow

### Step 1: Get the Hook

If not provided via $ARGUMENTS, ask:
1. What's the hook?
2. What topic/idea is this hook about? (brief context)

### Step 2: Load Knowledge Base

Read these files to ground the post in Ian's voice/expertise:
- `knowledge_bases/Smiths/Written Posts/Ian Origin Story 2.0.md` - personal stories
- `knowledge_bases/Smiths/Written Posts/Ian Shaw IP Extraction (2).pdf` - expertise, frameworks, beliefs
- `knowledge_bases/Smiths/Written Posts/Smiths Ian Best Performing Posts.md` - what resonates
- `knowledge_bases/Smiths/Written Posts/LI Content Templates.md` - post structures

### Step 3: Generate Draft

Create a full LinkedIn post that:
- Opens with the exact hook provided
- Expands on the hook's promise
- Uses Ian's voice: direct, no fluff, actionable
- Short paragraphs (1-2 sentences max)
- Liberal use of line breaks for readability
- Includes a clear takeaway or framework
- Ends with implicit or explicit CTA

**Post Structure Options:**
- **Story → Lesson:** Personal experience that proves the point
- **Problem → Solution:** Pain point then actionable fix
- **Myth → Reality:** What people think vs what's true
- **Framework:** Numbered steps or bullet points
- **Contrarian take:** Challenge then defend with logic

Target length: 1200-1800 characters (optimal LinkedIn engagement)

### Step 4: Save Draft

Save the draft:
```python
from execution.draft_storage import create_draft, update_draft
draft = create_draft(content, hooks=[hook], topic=topic)
update_draft(draft["id"], selected_hook=0)
```

### Step 5: Present to User

Show the full draft and offer:
- Edit/revise if needed
- Generate alternative version
- Save to drafts bank

## Important

- Use Claude (this session) for generation - do NOT call the Anthropic API
- The hook must appear exactly as provided at the start of the post
- Match Ian's voice from the knowledge base - no corporate speak, no fluff
