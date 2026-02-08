---
name: idea
description: Generate LinkedIn hooks and drafts from a user-provided idea/topic. Use when the user already has a specific content idea they want to develop into posts.
---

# /idea - Develop a Content Idea into Drafts

The user has a specific idea they want to turn into LinkedIn content. Skip idea generation, go straight to hooks.

**Benchmark:** See `content/human-taste-curation.md` for expected hook output format (30 hooks organized by framework score, each with framework pattern noted).

## Context About Ian's Offer

Ian helps B2B founders/coaches/consultants scale their high-ticket offers by:
- Building their personal brand on LinkedIn
- Creating content systems (so they work ON not IN their content)
- Running outreach systems that book sales calls
- Using AI to amplify (not replace) human expertise

Key results: Scaled clients to $25k-$60k/month, 4+ calls/week booked

## Workflow

### Step 1: Gather Context

Ask the user:
1. What's the topic/idea? (if not already provided via $ARGUMENTS)
2. Any specific angle, story, or points to include?
3. Which content pillar? (Personal story, Expertise/how-to, Social Proof/case study, Opinion/contrarian, Trending)
4. **ICP targeting (optional):** Who should this content call out? Examples:
   - B2B founders scaling to $50k/month
   - Coaches/consultants stuck under $10k/month
   - CEOs who want to build a personal brand
   - Solo founders doing everything themselves
   - Skip if targeting general audience

### Step 2: Generate 30 Hooks

Using the knowledge base files in `knowledge_bases/`:
- `Smiths/Written Posts/Ian Origin Story 2.0.md` - personal stories
- `Smiths/Written Posts/Ian Shaw IP Extraction (2).pdf` - expertise, frameworks, beliefs
- `Smiths/Written Posts/Smiths Ian Best Performing Posts.md` - what resonates
- `Hooks/hooks_condensed.txt` - hook patterns with scores (use higher-scoring frameworks first)

Generate 30 scroll-stopping hooks. Vary styles:
- Questions
- Bold statements
- Story openers
- Numbers/stats
- Contrarian takes
- Warnings
- Pattern interrupts

**ICP Integration (if specified):**
When user provides an ICP target, weave it into hooks naturally:
- Direct callouts: "B2B founders: stop doing X"
- Implicit targeting: "If you're stuck at $10k/month..."
- Identity hooks: "The difference between 6-figure and 7-figure coaches"
- Pain points specific to that audience
- Aspirational states that audience wants

**Output Format:**
Present 30 hooks organized by framework score tier (see `human-taste-curation.md` for benchmark):
```
### [790]-Score Frameworks (Top Tier)
1. Hook text here
   *Framework: Framework pattern used*

### [92]-Score Frameworks
...
```

Ask user to select their favorites (e.g., "1, 5, 12, 23").

### Step 3: Save Selected Hooks

For each selected hook, save to hooks bank:
```python
from execution.draft_storage import save_hook_to_bank
save_hook_to_bank(hook_text, topic)
```

### Step 4: Generate Drafts

For each selected hook (or user picks top 3-5), generate a full LinkedIn post draft that:
- Opens with the hook
- Connects to Ian's experience/expertise from knowledge base
- Uses short paragraphs, line breaks for readability
- Includes a clear takeaway
- Ends with implicit or explicit CTA

Save each draft:
```python
from execution.draft_storage import create_draft, update_draft
draft = create_draft(content, hooks=[hook], topic=topic)
update_draft(draft["id"], selected_hook=0)
```

### Step 5: Summary

Show user:
- How many hooks saved to bank
- Draft IDs created
- Offer to review/edit any draft

## Important

- Use Claude (this session) for all generation - do NOT call the Anthropic API
- Keep the user in the loop at each step
- Read the knowledge base files to ground content in Ian's actual stories/expertise
