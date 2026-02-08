---
name: refill
description: Refill the drafts bank with fresh LinkedIn content. AI generates ideas from knowledge base, then hooks, then full drafts. Use when content bank is running low.
---

# /refill - Refill Drafts Bank with Fresh Content

Generate fresh LinkedIn content from scratch using the knowledge base.

## Context About Ian's Offer

Ian helps B2B founders/coaches/consultants scale their high-ticket offers by:
- Building their personal brand on LinkedIn
- Creating content systems (so they work ON not IN their content)
- Running outreach systems that book sales calls
- Using AI to amplify (not replace) human expertise

Key results: Scaled clients to $25k-$60k/month, 4+ calls/week booked

Content Pillars:
- **Personal**: Stories, anecdotes, personal experiences (door-to-door sales, banana farm, AI hackathon, redlining with clients)
- **Expertise**: How-to's, frameworks, mental models (PESTO content system, buy back your time, systemize everything)
- **Social Proof**: Results, case studies (Mandi $25k, Cam $35k, Wik $60k in 60 days, Evin/Justin IG growth)
- **Opinion**: Contrarian takes ("DMs are sleazy" is BS, "you need CS degree for AI" is wrong)
- **Trending**: AI in coaching, consumer trust, digital nomad life

## Workflow

### Step 1: Get Optional Topic/Direction

Ask user:
- Any specific topic or theme to focus on? (optional)
- Or should I explore the knowledge base and suggest topics?

If user provides topic, use it. Otherwise, suggest 3-5 topics based on knowledge base.

### Step 2: Generate Ideas (15 per topic)

Read the knowledge base files:
- `knowledge_bases/Smiths/Written Posts/Ian Origin Story 2.0.md`
- `knowledge_bases/Smiths/Written Posts/Ian Shaw IP Extraction (2).pdf`
- `knowledge_bases/Smiths/Written Posts/Smiths Ian Best Performing Posts.md`

Generate 15 ideas that connect the topic to Ian's:
- Personal stories and experiences
- Expertise, frameworks, insights
- Case studies and results
- Contrarian perspectives

Present as table with pillar tags. Ask user which ideas to take forward.

### Step 3: Save Selected Ideas

```python
from execution.draft_storage import save_idea_to_bank
save_idea_to_bank(idea_text, topic, angle)
```

### Step 4: Generate Hooks (30 per idea, in parallel)

For each selected idea, generate 30 hooks. Use patterns from:
- `knowledge_bases/Hooks/hooks_condensed.txt`

Vary styles: questions, bold statements, stories, stats, contrarian, warnings.

Present hooks grouped by idea. Ask user to highlight favorites.

### Step 5: Save Selected Hooks

```python
from execution.draft_storage import save_hook_to_bank
save_hook_to_bank(hook_text, topic)
```

### Step 6: Generate Drafts

User picks which hooks to turn into full drafts (or random selection).

For each hook + idea combination, generate a full LinkedIn post that:
- Opens with the hook
- Expands on the idea using knowledge base content
- Uses Ian's voice (direct, no-BS, systems-thinking)
- Short paragraphs, line breaks
- Clear takeaway
- Implicit CTA

Save drafts:
```python
from execution.draft_storage import create_draft, update_draft
draft = create_draft(content, hooks=[hook], topic=topic)
update_draft(draft["id"], selected_hook=0)
```

### Step 7: Summary

Report:
- Ideas saved to bank: X
- Hooks saved to bank: X
- Drafts created: X (with IDs)
- Offer to review/edit any draft or continue generating more

## Important

- Use Claude (this session) for all generation - do NOT call the Anthropic API
- Keep user in the loop at each step - they drive, you generate
- Read knowledge base files to ground content in real stories/expertise
- Each selected idea should generate hooks in parallel (conceptually - present them grouped)
