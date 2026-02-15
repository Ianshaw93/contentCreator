"""
Web UI for LinkedIn post creation with hooks-first workflow.
Built with FastAPI.

Workflow:
1. Enter topic → Generate 30 hooks
2. Review hooks in editable inputs, highlight the best ones
3. Save highlighted hooks to bank, hide non-highlighted
4. Select one or more hooks → Generate draft posts (one per hook)
5. Review and post to LinkedIn
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, Request, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates
import calendar as cal
from datetime import datetime as dt
from dotenv import load_dotenv
import uvicorn
import json

from draft_storage import (
    list_drafts, get_draft, create_draft, update_draft,
    delete_draft, get_final_post, save_hook_to_bank, get_hooks_bank,
    delete_hook_from_bank, save_idea_to_bank, get_ideas_bank, delete_idea_from_bank,
    list_drafts_by_date, get_drafts_for_date
)
from image_storage import save_image, delete_image, list_images, get_image, get_image_url
from generate_post import generate_post_body, load_knowledge_base
from generate_hooks import generate_hooks
from generate_ideas import generate_ideas
from post_to_linkedin import post_to_linkedin, check_token_validity

load_dotenv()

app = FastAPI(title="LinkedIn Content Creator")

TEMPLATES_DIR = Path(__file__).parent / "templates"
TEMPLATES_DIR.mkdir(exist_ok=True)


# =============================================================================
# HTML TEMPLATES
# =============================================================================

BASE_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LinkedIn Content Creator</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        header {
            background: #0077b5;
            color: white;
            padding: 20px;
            margin-bottom: 20px;
        }
        header h1 { font-size: 24px; }
        nav { display: flex; gap: 15px; margin-top: 15px; }
        nav a {
            color: white;
            text-decoration: none;
            padding: 8px 16px;
            background: rgba(255,255,255,0.2);
            border-radius: 4px;
        }
        nav a:hover { background: rgba(255,255,255,0.3); }
        nav a.active { background: rgba(255,255,255,0.4); }
        .card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .card h2 { margin-bottom: 15px; color: #0077b5; }
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            text-decoration: none;
            display: inline-block;
        }
        .btn-primary { background: #0077b5; color: white; }
        .btn-primary:hover { background: #005885; }
        .btn-secondary { background: #6c757d; color: white; }
        .btn-success { background: #28a745; color: white; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-sm { padding: 4px 8px; font-size: 12px; }
        textarea, input[type="text"], select {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            font-family: inherit;
            margin-bottom: 10px;
        }
        textarea:focus, input:focus { border-color: #0077b5; outline: none; }
        label { display: block; margin-bottom: 5px; font-weight: 500; }
        .alert {
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
        }
        .alert-success { background: #d4edda; color: #155724; }
        .alert-error { background: #f8d7da; color: #721c24; }
        .alert-info { background: #cce5ff; color: #004085; }

        /* Hook specific styles */
        .hook-item {
            display: flex;
            gap: 10px;
            align-items: flex-start;
            padding: 10px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            margin-bottom: 10px;
            transition: all 0.2s;
        }
        .hook-item.highlighted {
            border-color: #0077b5;
            background: #e8f4f8;
        }
        .hook-item.hidden {
            display: none;
        }
        .hook-item input[type="text"] {
            flex: 1;
            margin-bottom: 0;
        }
        .hook-item .hook-actions {
            display: flex;
            gap: 5px;
            flex-shrink: 0;
        }
        .hook-number {
            font-weight: bold;
            color: #666;
            min-width: 30px;
        }
        .hooks-toolbar {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
            flex-wrap: wrap;
            align-items: center;
        }
        .hooks-toolbar .count {
            margin-left: auto;
            color: #666;
        }
        .draft-item {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            background: #fafafa;
        }
        .draft-preview {
            white-space: pre-wrap;
            font-size: 14px;
            color: #555;
            max-height: 150px;
            overflow: hidden;
        }
        .preview-box {
            background: #f8f9fa;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            padding: 15px;
            white-space: pre-wrap;
            font-size: 14px;
        }
        .status-draft { background: #fff3cd; color: #856404; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
        .status-scheduled { background: #cce5ff; color: #004085; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
        .status-posted { background: #d4edda; color: #155724; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        @media (max-width: 768px) { .grid-2 { grid-template-columns: 1fr; } }
        .loading { opacity: 0.6; pointer-events: none; }
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1>LinkedIn Content Creator</h1>
            <nav>
                <a href="/" class="{{ 'active' if page == 'home' else '' }}">Create</a>
                <a href="/calendar" class="{{ 'active' if page == 'calendar' else '' }}">Calendar</a>
                <a href="/drafts" class="{{ 'active' if page == 'drafts' else '' }}">Drafts</a>
                <a href="/scheduled" class="{{ 'active' if page == 'scheduled' else '' }}">Scheduled</a>
                <a href="/posted" class="{{ 'active' if page == 'posted' else '' }}">Posted</a>
                <a href="/ideas-bank" class="{{ 'active' if page == 'ideas-bank' else '' }}">Ideas</a>
                <a href="/hooks-bank" class="{{ 'active' if page == 'hooks-bank' else '' }}">Hooks</a>
                <a href="/images" class="{{ 'active' if page == 'images' else '' }}">Images</a>
                <a href="/settings" class="{{ 'active' if page == 'settings' else '' }}">Settings</a>
            </nav>
        </div>
    </header>
    <div class="container">
        {% if message %}
        <div class="alert alert-{{ message_type or 'info' }}">{{ message }}</div>
        {% endif %}
        {% block content %}{% endblock %}
    </div>
    <script>
        function toggleHighlight(el) {
            el.closest('.hook-item').classList.toggle('highlighted');
            updateCount();
        }
        function hideHook(el) {
            el.closest('.hook-item').classList.add('hidden');
            updateCount();
        }
        function showAllHooks() {
            document.querySelectorAll('.hook-item.hidden').forEach(el => el.classList.remove('hidden'));
            updateCount();
        }
        function hideNonHighlighted() {
            document.querySelectorAll('.hook-item:not(.highlighted)').forEach(el => el.classList.add('hidden'));
            updateCount();
        }
        function updateCount() {
            const total = document.querySelectorAll('.hook-item').length;
            const visible = document.querySelectorAll('.hook-item:not(.hidden)').length;
            const highlighted = document.querySelectorAll('.hook-item.highlighted').length;
            const countEl = document.querySelector('.hooks-count');
            if (countEl) countEl.textContent = `${highlighted} highlighted, ${visible}/${total} visible`;
        }
        function getSelectedHooks() {
            const hooks = [];
            document.querySelectorAll('.hook-item.highlighted:not(.hidden)').forEach(el => {
                const input = el.querySelector('input[type="text"]');
                if (input && input.value.trim()) {
                    hooks.push(input.value.trim());
                }
            });
            return hooks;
        }
    </script>
</body>
</html>'''

HOME_CONTENT = '''{% extends "base.html" %}
{% block content %}
<div class="card">
    <h2>Step 1: Enter Topic & Generate Ideas</h2>
    <form action="/generate-ideas" method="POST">
        <label>Topic / Idea</label>
        <input type="text" name="topic" placeholder="e.g., Why AI won't replace coaches" required value="{{ topic or '' }}">
        <label>Additional Context (optional)</label>
        <textarea name="context" rows="2" placeholder="Any specific angle, story, or points to include...">{{ context or '' }}</textarea>
        <button type="submit" class="btn btn-primary">Generate Ideas from Knowledge Base</button>
    </form>
</div>

{% if ideas %}
<div class="card">
    <h2>Step 2: Select Ideas</h2>
    <p style="margin-bottom: 15px; color: #666;">These ideas connect your topic to your knowledge base. Select the best ones to generate hooks.</p>
    <div class="hooks-toolbar">
        <button type="button" class="btn btn-secondary btn-sm" onclick="hideNonHighlighted()">Hide Non-Highlighted</button>
        <button type="button" class="btn btn-secondary btn-sm" onclick="showAllHooks()">Show All</button>
        <span class="hooks-count count">{{ ideas|length }} ideas</span>
    </div>

    <form action="/generate-hooks-from-ideas" method="POST" id="ideas-form">
        <input type="hidden" name="topic" value="{{ topic }}">

        {% for idea in ideas %}
        <div class="hook-item" data-index="{{ loop.index0 }}">
            <span class="hook-number">{{ loop.index }}.</span>
            {% if idea.angle %}<span style="background: #e8f4f8; padding: 2px 6px; border-radius: 4px; font-size: 11px; margin-right: 8px;">{{ idea.angle }}</span>{% endif %}
            <input type="text" name="idea_{{ loop.index0 }}" value="{{ idea.idea }}">
            <input type="hidden" name="angle_{{ loop.index0 }}" value="{{ idea.angle or '' }}">
            <div class="hook-actions">
                <button type="button" class="btn btn-primary btn-sm" onclick="toggleHighlight(this)" title="Highlight">*</button>
                <button type="button" class="btn btn-success btn-sm" onclick="saveIdea(this, '{{ topic }}')" title="Save to Bank">S</button>
                <button type="button" class="btn btn-secondary btn-sm" onclick="hideHook(this)" title="Hide">x</button>
            </div>
        </div>
        {% endfor %}

        <div style="margin-top: 20px; display: flex; gap: 10px;">
            <button type="submit" class="btn btn-primary">Generate Hooks from Highlighted Ideas</button>
            <button type="button" class="btn btn-secondary" onclick="saveAllIdeas('{{ topic }}')">Save All Highlighted to Ideas Bank</button>
        </div>
    </form>
</div>
{% endif %}

{% if hook_groups %}
<form action="/create-drafts" method="POST" id="create-drafts-form">
    <input type="hidden" name="topic" value="{{ topic }}">

    {% for group in hook_groups %}
    <div class="card" style="border-left: 4px solid #0077b5;">
        <h2 style="font-size: 16px; margin-bottom: 5px;">
            {% if group.angle %}<span style="background: #e8f4f8; padding: 2px 8px; border-radius: 4px; font-size: 12px; margin-right: 10px;">{{ group.angle }}</span>{% endif %}
            {{ group.idea[:80] }}{% if group.idea|length > 80 %}...{% endif %}
        </h2>
        <input type="hidden" name="idea_{{ loop.index0 }}" value="{{ group.idea }}">

        <div class="hooks-toolbar" style="margin-top: 10px;">
            <button type="button" class="btn btn-secondary btn-sm" onclick="hideNonHighlightedInGroup(this)">Hide Non-Highlighted</button>
            <button type="button" class="btn btn-secondary btn-sm" onclick="showAllInGroup(this)">Show All</button>
            <span class="group-hooks-count count">{{ group.hooks|length }} hooks</span>
        </div>

        {% for hook in group.hooks %}
        <div class="hook-item hook-section-item" data-group="{{ loop.parent.loop.index0 }}" data-index="{{ loop.index0 }}">
            <span class="hook-number">{{ loop.index }}.</span>
            <input type="text" name="hook_{{ loop.parent.loop.index0 }}_{{ loop.index0 }}" value="{{ hook }}">
            <div class="hook-actions">
                <button type="button" class="btn btn-primary btn-sm" onclick="toggleHighlightHook(this)" title="Highlight">*</button>
                <button type="button" class="btn btn-success btn-sm" onclick="saveHook(this, '{{ topic }}')" title="Save to Bank">S</button>
                <button type="button" class="btn btn-secondary btn-sm" onclick="hideHookSection(this)" title="Hide">x</button>
            </div>
        </div>
        {% endfor %}
    </div>
    {% endfor %}

    <div class="card" style="position: sticky; bottom: 20px; box-shadow: 0 -2px 10px rgba(0,0,0,0.1);">
        <div style="display: flex; gap: 10px; flex-wrap: wrap;">
            <button type="submit" class="btn btn-primary">Create Drafts from Highlighted Hooks</button>
            <button type="button" class="btn btn-secondary" onclick="saveAllHighlightedHooks('{{ topic }}')">Save All Highlighted to Hooks Bank</button>
            <button type="button" class="btn btn-secondary" onclick="hideAllNonHighlighted()">Hide All Non-Highlighted</button>
            <span class="hooks-count-section count" style="margin-left: auto;"></span>
        </div>
    </div>
</form>
{% endif %}

<script>
// Ideas section
async function saveIdea(el, topic) {
    const item = el.closest('.hook-item');
    const idea = item.querySelector('input[type="text"]').value.trim();
    const angle = item.querySelector('input[type="hidden"]').value;
    if (!idea) return;

    const resp = await fetch('/api/save-idea', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({idea, topic, angle})
    });
    if (resp.ok) {
        el.textContent = 'ok';
        el.disabled = true;
    }
}

async function saveAllIdeas(topic) {
    const items = document.querySelectorAll('#ideas-form .hook-item.highlighted:not(.hidden)');
    if (items.length === 0) {
        alert('No ideas highlighted');
        return;
    }

    for (const item of items) {
        const idea = item.querySelector('input[type="text"]').value.trim();
        const angle = item.querySelector('input[type="hidden"]').value;
        if (idea) {
            await fetch('/api/save-idea', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({idea, topic, angle})
            });
        }
    }
    alert(`Saved ${items.length} ideas to bank`);
}

document.getElementById('ideas-form')?.addEventListener('submit', function(e) {
    const highlighted = document.querySelectorAll('#ideas-form .hook-item.highlighted:not(.hidden)');
    if (highlighted.length === 0) {
        e.preventDefault();
        alert('Please highlight at least one idea');
        return;
    }

    highlighted.forEach(el => {
        const idx = el.dataset.index;
        const hidden = document.createElement('input');
        hidden.type = 'hidden';
        hidden.name = 'selected_' + idx;
        hidden.value = '1';
        this.appendChild(hidden);
    });
});

// Hooks section
function toggleHighlightHook(el) {
    el.closest('.hook-section-item').classList.toggle('highlighted');
    updateHooksCount();
    updateGroupCount(el);
}
function hideHookSection(el) {
    el.closest('.hook-section-item').classList.add('hidden');
    updateHooksCount();
    updateGroupCount(el);
}
function hideNonHighlightedInGroup(btn) {
    const card = btn.closest('.card');
    card.querySelectorAll('.hook-section-item:not(.highlighted)').forEach(el => el.classList.add('hidden'));
    updateHooksCount();
    updateGroupCountInCard(card);
}
function showAllInGroup(btn) {
    const card = btn.closest('.card');
    card.querySelectorAll('.hook-section-item.hidden').forEach(el => el.classList.remove('hidden'));
    updateHooksCount();
    updateGroupCountInCard(card);
}
function hideAllNonHighlighted() {
    document.querySelectorAll('.hook-section-item:not(.highlighted)').forEach(el => el.classList.add('hidden'));
    updateHooksCount();
    document.querySelectorAll('.card').forEach(card => updateGroupCountInCard(card));
}
function updateGroupCount(el) {
    const card = el.closest('.card');
    if (card) updateGroupCountInCard(card);
}
function updateGroupCountInCard(card) {
    const total = card.querySelectorAll('.hook-section-item').length;
    const visible = card.querySelectorAll('.hook-section-item:not(.hidden)').length;
    const highlighted = card.querySelectorAll('.hook-section-item.highlighted').length;
    const countEl = card.querySelector('.group-hooks-count');
    if (countEl) countEl.textContent = `${highlighted} highlighted, ${visible}/${total} visible`;
}
function updateHooksCount() {
    const total = document.querySelectorAll('.hook-section-item').length;
    const visible = document.querySelectorAll('.hook-section-item:not(.hidden)').length;
    const highlighted = document.querySelectorAll('.hook-section-item.highlighted').length;
    const countEl = document.querySelector('.hooks-count-section');
    if (countEl) countEl.textContent = `${highlighted} highlighted, ${visible}/${total} visible`;
}

async function saveHook(el, topic) {
    const input = el.closest('.hook-section-item').querySelector('input[type="text"]');
    const hook = input.value.trim();
    if (!hook) return;

    const resp = await fetch('/api/save-hook', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({hook, topic})
    });
    if (resp.ok) {
        el.textContent = 'ok';
        el.disabled = true;
    }
}

async function saveAllHighlightedHooks(topic) {
    const items = document.querySelectorAll('.hook-section-item.highlighted:not(.hidden)');
    if (items.length === 0) {
        alert('No hooks highlighted');
        return;
    }

    for (const item of items) {
        const hook = item.querySelector('input[type="text"]').value.trim();
        if (hook) {
            await fetch('/api/save-hook', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({hook, topic})
            });
        }
    }
    alert(`Saved ${items.length} hooks to bank`);
}

document.getElementById('create-drafts-form')?.addEventListener('submit', function(e) {
    const highlighted = document.querySelectorAll('.hook-section-item.highlighted:not(.hidden)');
    if (highlighted.length === 0) {
        e.preventDefault();
        alert('Please highlight at least one hook');
        return;
    }

    highlighted.forEach(el => {
        const groupIdx = el.dataset.group;
        const hookIdx = el.dataset.index;
        const hidden = document.createElement('input');
        hidden.type = 'hidden';
        hidden.name = 'selected_' + groupIdx + '_' + hookIdx;
        hidden.value = '1';
        this.appendChild(hidden);
    });
});
</script>
{% endblock %}'''

DRAFTS_CONTENT = '''{% extends "base.html" %}
{% block content %}
<div class="card">
    <h2>Your Drafts</h2>
    {% if drafts %}
        {% for draft in drafts %}
        <div class="draft-item">
            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                <span style="font-family: monospace; color: #666;">ID: {{ draft.id }}</span>
                <span class="status-{{ draft.status }}">{{ draft.status.upper() }}</span>
            </div>
            {% if draft.topic %}<strong>Topic:</strong> {{ draft.topic }}<br>{% endif %}
            {% if draft.selected_hook is not none and draft.hooks %}
            <strong>Hook:</strong> {{ draft.hooks[draft.selected_hook][:100] }}...<br>
            {% endif %}
            <div class="draft-preview" style="margin-top: 10px;">{{ draft.content[:300] }}{% if draft.content|length > 300 %}...{% endif %}</div>
            <div style="margin-top: 15px; display: flex; gap: 10px; flex-wrap: wrap;">
                <a href="/edit/{{ draft.id }}" class="btn btn-primary btn-sm">Edit</a>
                <a href="/preview/{{ draft.id }}" class="btn btn-secondary btn-sm">Preview</a>
                <form action="/mark-status/{{ draft.id }}/scheduled" method="POST" style="display:inline;">
                    <button type="submit" class="btn btn-sm" style="background: #cce5ff; color: #004085;">Move to Scheduled</button>
                </form>
                <form action="/mark-status/{{ draft.id }}/posted" method="POST" style="display:inline;">
                    <button type="submit" class="btn btn-success btn-sm">Mark as Posted</button>
                </form>
                <form action="/delete/{{ draft.id }}" method="POST" style="display:inline;">
                    <button type="submit" class="btn btn-danger btn-sm" onclick="return confirm('Delete?')">Delete</button>
                </form>
            </div>
        </div>
        {% endfor %}
    {% else %}
        <p style="color: #666;">No drafts yet. <a href="/">Create one</a></p>
    {% endif %}
</div>
{% endblock %}'''

SCHEDULED_CONTENT = '''{% extends "base.html" %}
{% block content %}
<div class="card">
    <h2>Scheduled Posts</h2>
    {% if drafts %}
        {% for draft in drafts %}
        <div class="draft-item">
            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                <span style="font-family: monospace; color: #666;">ID: {{ draft.id }}</span>
                <span class="status-{{ draft.status }}">{{ draft.status.upper() }}</span>
            </div>
            {% if draft.scheduled_time %}
            <div style="background: #cce5ff; padding: 8px; border-radius: 4px; margin-bottom: 10px;">
                <strong>Scheduled for:</strong> {{ draft.scheduled_time[:16].replace('T', ' ') }}
            </div>
            {% endif %}
            {% if draft.topic %}<strong>Topic:</strong> {{ draft.topic }}<br>{% endif %}
            {% if draft.selected_hook is not none and draft.hooks %}
            <strong>Hook:</strong> {{ draft.hooks[draft.selected_hook][:100] }}...<br>
            {% endif %}
            {% if draft.images %}<strong>Images:</strong> {{ draft.images|length }} attached<br>{% endif %}
            <div class="draft-preview" style="margin-top: 10px;">{{ draft.content[:300] }}{% if draft.content|length > 300 %}...{% endif %}</div>
            <div style="margin-top: 15px; display: flex; gap: 10px; flex-wrap: wrap;">
                <a href="/edit/{{ draft.id }}" class="btn btn-primary btn-sm">Edit</a>
                <a href="/preview/{{ draft.id }}" class="btn btn-secondary btn-sm">Preview</a>
                <form action="/mark-status/{{ draft.id }}/draft" method="POST" style="display:inline;">
                    <button type="submit" class="btn btn-secondary btn-sm">Back to Drafts</button>
                </form>
                <form action="/mark-status/{{ draft.id }}/posted" method="POST" style="display:inline;">
                    <button type="submit" class="btn btn-success btn-sm">Mark as Posted</button>
                </form>
                <form action="/delete/{{ draft.id }}" method="POST" style="display:inline;">
                    <button type="submit" class="btn btn-danger btn-sm" onclick="return confirm('Delete?')">Delete</button>
                </form>
            </div>
        </div>
        {% endfor %}
    {% else %}
        <p style="color: #666;">No scheduled posts. <a href="/drafts">Move drafts here</a></p>
    {% endif %}
</div>
{% endblock %}'''

POSTED_CONTENT = '''{% extends "base.html" %}
{% block content %}
<div class="card">
    <h2>Posted</h2>
    {% if drafts %}
        {% for draft in drafts %}
        <div class="draft-item">
            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                <span style="font-family: monospace; color: #666;">ID: {{ draft.id }}</span>
                <span class="status-{{ draft.status }}">{{ draft.status.upper() }}</span>
            </div>
            <div style="background: #d4edda; padding: 8px; border-radius: 4px; margin-bottom: 10px; display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                <strong>Posted on:</strong>
                <input type="datetime-local"
                       id="posted_at_{{ draft.id }}"
                       value="{{ draft.posted_at[:16] if draft.posted_at else '' }}"
                       style="padding: 4px; border: 1px solid #ccc; border-radius: 4px;">
                <button type="button" class="btn btn-sm btn-primary" onclick="savePostedDate('{{ draft.id }}')">Save Date</button>
            </div>
            {% if draft.topic %}<strong>Topic:</strong> {{ draft.topic }}<br>{% endif %}
            {% if draft.selected_hook is not none and draft.hooks %}
            <strong>Hook:</strong> {{ draft.hooks[draft.selected_hook][:100] }}...<br>
            {% endif %}
            {% if draft.images %}<strong>Images:</strong> {{ draft.images|length }} attached<br>{% endif %}
            <div class="draft-preview" style="margin-top: 10px;">{{ draft.content[:300] }}{% if draft.content|length > 300 %}...{% endif %}</div>
            <div style="margin-top: 15px; display: flex; gap: 10px; flex-wrap: wrap;">
                <a href="/preview/{{ draft.id }}" class="btn btn-secondary btn-sm">Preview</a>
                <form action="/mark-status/{{ draft.id }}/draft" method="POST" style="display:inline;">
                    <button type="submit" class="btn btn-secondary btn-sm">Back to Drafts</button>
                </form>
                <form action="/delete/{{ draft.id }}" method="POST" style="display:inline;">
                    <button type="submit" class="btn btn-danger btn-sm" onclick="return confirm('Delete?')">Delete</button>
                </form>
            </div>
        </div>
        {% endfor %}
    {% else %}
        <p style="color: #666;">No posted content yet.</p>
    {% endif %}
</div>

<script>
async function savePostedDate(draftId) {
    const input = document.getElementById('posted_at_' + draftId);
    const postedAt = input.value;

    const resp = await fetch('/api/drafts/' + draftId + '/posted-date', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({posted_at: postedAt || null})
    });

    if (resp.ok) {
        input.style.borderColor = '#28a745';
        setTimeout(() => { input.style.borderColor = '#ccc'; }, 1500);
    } else {
        alert('Failed to save date');
    }
}
</script>
{% endblock %}'''

HOOKS_BANK_CONTENT = '''{% extends "base.html" %}
{% block content %}
<div class="card">
    <h2>Saved Hooks Bank</h2>
    {% if hooks %}
        {% for hook in hooks %}
        <div class="hook-item">
            <span class="hook-number">{{ loop.index }}.</span>
            <div style="flex: 1;">
                <div>{{ hook.hook }}</div>
                <small style="color: #888;">Topic: {{ hook.topic or 'General' }} | Used: {{ hook.used_count or 0 }} times</small>
            </div>
            <div class="hook-actions">
                <form action="/delete-saved-hook/{{ hook.id }}" method="POST" style="display:inline;">
                    <button type="submit" class="btn btn-danger btn-sm" onclick="return confirm('Delete?')">✕</button>
                </form>
            </div>
        </div>
        {% endfor %}
    {% else %}
        <p style="color: #666;">No saved hooks yet. Generate hooks and save the best ones.</p>
    {% endif %}
</div>
{% endblock %}'''

EDIT_CONTENT = '''{% extends "base.html" %}
{% block content %}
<style>
    .library-thumb { width: 90px; height: 90px; object-fit: cover; border-radius: 4px; cursor: pointer; border: 3px solid transparent; transition: border-color 0.2s; }
    .library-thumb.attached { border-color: #0077b5; box-shadow: 0 0 0 2px #0077b5; }
    .library-thumb:hover { opacity: 0.85; }
</style>
<div class="grid-2">
    <div>
        <div class="card">
            <h2>Edit Draft</h2>
            <form action="/update/{{ draft.id }}" method="POST">
                <label>Hook</label>
                {% if draft.hooks and draft.selected_hook is not none %}
                <input type="text" name="hook" value="{{ draft.hooks[draft.selected_hook] }}">
                {% else %}
                <input type="text" name="hook" placeholder="No hook selected">
                {% endif %}

                <label>Post Body</label>
                <textarea name="content" rows="15">{{ draft.content }}</textarea>

                <div style="display: flex; gap: 10px;">
                    <button type="submit" class="btn btn-primary">Save Changes</button>
                    <a href="/drafts" class="btn btn-secondary">Cancel</a>
                </div>
            </form>
        </div>

        <div class="card">
            <h2>Schedule</h2>
            <label>Scheduled Date & Time</label>
            <input type="datetime-local" id="scheduled_time" value="{{ draft.scheduled_time[:16] if draft.scheduled_time else '' }}">
            <button type="button" class="btn btn-primary" onclick="saveSchedule()">Save Schedule</button>
            {% if draft.scheduled_time %}
            <button type="button" class="btn btn-secondary" onclick="clearSchedule()">Clear</button>
            {% endif %}
            <p style="margin-top: 10px; color: #666; font-size: 12px;">
                Status: <span class="status-{{ draft.status }}">{{ draft.status.upper() }}</span>
                {% if draft.posted_at %}<br>Posted: {{ draft.posted_at[:16] }}{% endif %}
            </p>
        </div>
    </div>

    <div>
        <div class="card">
            <h2>Attached Images</h2>
            <div id="attached-images" style="display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 15px;">
                {% for img in attached_images %}
                <div class="image-item" data-id="{{ img.id }}" style="position: relative;">
                    <img src="/api/images/{{ img.id }}/file" style="width: 100px; height: 100px; object-fit: cover; border-radius: 4px;">
                    <button type="button" onclick="detachImage('{{ img.id }}')" style="position: absolute; top: -5px; right: -5px; background: #dc3545; color: white; border: none; border-radius: 50%; width: 20px; height: 20px; cursor: pointer; font-size: 12px;" title="Detach">x</button>
                </div>
                {% endfor %}
            </div>
            {% if not attached_images %}<p style="color: #999; font-size: 13px;">No images attached. Click images below to attach.</p>{% endif %}
        </div>

        <div class="card">
            <h2>Image Library <a href="/images" class="btn btn-secondary btn-sm" style="float:right;">Manage</a></h2>
            <p style="color: #666; font-size: 12px; margin-bottom: 10px;">Click to attach/detach from this draft.</p>
            <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px;">
                {% for img in library_images %}
                <img src="/api/images/{{ img.id }}/file"
                     class="library-thumb {{ 'attached' if img.id in attached_ids else '' }}"
                     data-id="{{ img.id }}"
                     onclick="toggleAttach('{{ img.id }}')"
                     title="{{ img.original_name }}"
                     loading="lazy">
                {% endfor %}
            </div>
            {% if not library_images %}<p style="color: #999; font-size: 13px;"><a href="/images">Upload images</a> to the library first.</p>{% endif %}

            <div style="border-top: 1px solid #eee; padding-top: 10px; margin-top: 5px;">
                <label>Quick Upload to Library</label>
                <input type="file" id="quick-upload" accept="image/*">
                <button type="button" class="btn btn-primary btn-sm" onclick="quickUpload()" style="margin-top: 5px;">Upload & Attach</button>
            </div>
        </div>

        <div class="card">
            <h2>Preview</h2>
            <div class="preview-box" style="max-height: 300px; overflow-y: auto;">
                {% if draft.hooks and draft.selected_hook is not none %}{{ draft.hooks[draft.selected_hook] }}

{% endif %}{{ draft.content }}</div>
            <p style="margin-top: 10px; color: #888; font-size: 12px;">Character count: {{ (draft.content|length) + (draft.hooks[draft.selected_hook]|length + 2 if draft.hooks and draft.selected_hook is not none else 0) }}</p>
        </div>
    </div>
</div>

<script>
const draftId = '{{ draft.id }}';
const attachedIds = new Set({{ attached_ids | tojson }});

async function saveSchedule() {
    const time = document.getElementById('scheduled_time').value;
    const resp = await fetch('/api/drafts/' + draftId + '/schedule', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({scheduled_time: time || null})
    });
    if (resp.ok) window.location.reload();
    else alert('Failed to save schedule');
}

async function clearSchedule() {
    const resp = await fetch('/api/drafts/' + draftId + '/schedule', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({scheduled_time: null})
    });
    if (resp.ok) window.location.reload();
}

async function toggleAttach(imageId) {
    if (attachedIds.has(imageId)) {
        const resp = await fetch('/api/drafts/' + draftId + '/attach-image/' + imageId, { method: 'DELETE' });
        if (resp.ok) window.location.reload();
    } else {
        const resp = await fetch('/api/drafts/' + draftId + '/attach-image/' + imageId, { method: 'POST' });
        if (resp.ok) window.location.reload();
    }
}

async function detachImage(imageId) {
    const resp = await fetch('/api/drafts/' + draftId + '/attach-image/' + imageId, { method: 'DELETE' });
    if (resp.ok) window.location.reload();
}

async function quickUpload() {
    const input = document.getElementById('quick-upload');
    if (!input.files.length) return;

    const formData = new FormData();
    formData.append('file', input.files[0]);

    // Upload to library
    const resp = await fetch('/api/images', { method: 'POST', body: formData });
    if (!resp.ok) {
        const data = await resp.json();
        alert('Upload failed: ' + (data.detail || 'Unknown error'));
        return;
    }
    const result = await resp.json();

    // Attach to this draft
    await fetch('/api/drafts/' + draftId + '/attach-image/' + result.image.id, { method: 'POST' });
    window.location.reload();
}
</script>
{% endblock %}'''

PREVIEW_CONTENT = '''{% extends "base.html" %}
{% block content %}
<div class="card">
    <h2>Post Preview</h2>
    <div class="preview-box">{{ final_content }}</div>

    {% if attached_images %}
    <div style="margin-top: 15px;">
        <strong>Attached Images:</strong>
        <div style="display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px;">
            {% for img in attached_images %}
            <img src="/api/images/{{ img.id }}/file" style="width: 150px; height: 150px; object-fit: cover; border-radius: 4px;">
            {% endfor %}
        </div>
    </div>
    {% endif %}

    <div style="margin-top: 20px; display: flex; gap: 10px;">
        <a href="/edit/{{ draft.id }}" class="btn btn-primary">Edit</a>
        <form action="/post/{{ draft.id }}" method="POST" style="display:inline;">
            <button type="submit" class="btn btn-success" onclick="return confirm('Post to LinkedIn?{% if attached_images %} (includes {{ attached_images|length }} image(s)){% endif %}')">Post to LinkedIn</button>
        </form>
        <a href="/drafts" class="btn btn-secondary">Back</a>
    </div>
    <p style="margin-top: 15px; color: #888;">Character count: {{ final_content|length }}</p>
</div>
{% endblock %}'''

IDEAS_BANK_CONTENT = '''{% extends "base.html" %}
{% block content %}
<div class="card">
    <h2>Saved Ideas Bank</h2>
    {% if ideas %}
        {% for idea in ideas %}
        <div class="hook-item">
            <span class="hook-number">{{ loop.index }}.</span>
            <div style="flex: 1;">
                {% if idea.angle %}<span style="background: #e8f4f8; padding: 2px 6px; border-radius: 4px; font-size: 11px; margin-right: 8px;">{{ idea.angle }}</span>{% endif %}
                <div>{{ idea.idea }}</div>
                <small style="color: #888;">Topic: {{ idea.topic or 'General' }} | Used: {{ idea.used_count or 0 }} times</small>
            </div>
            <div class="hook-actions">
                <form action="/delete-saved-idea/{{ idea.id }}" method="POST" style="display:inline;">
                    <button type="submit" class="btn btn-danger btn-sm" onclick="return confirm('Delete?')">x</button>
                </form>
            </div>
        </div>
        {% endfor %}
    {% else %}
        <p style="color: #666;">No saved ideas yet. Generate ideas and save the best ones.</p>
    {% endif %}
</div>
{% endblock %}'''

IMAGES_LIBRARY_CONTENT = '''{% extends "base.html" %}
{% block content %}
<div class="card">
    <h2>Image Library</h2>
    <p style="color: #666; margin-bottom: 15px;">Upload images here and attach them to any draft.</p>

    <div style="margin-bottom: 20px;">
        <label>Upload Image</label>
        <input type="file" id="library-upload" accept="image/*" multiple>
        <button type="button" class="btn btn-primary" onclick="uploadToLibrary()" style="margin-top: 10px;">Upload</button>
        <p style="color: #666; font-size: 12px; margin-top: 5px;">Max 10MB per image. JPG, PNG, GIF, WebP supported.</p>
    </div>

    <div id="library-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 15px;">
        {% for img in images %}
        <div class="library-image-card" data-id="{{ img.id }}" style="border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; background: white;">
            <img src="/api/images/{{ img.id }}/file" style="width: 100%; height: 150px; object-fit: cover;" loading="lazy">
            <div style="padding: 8px;">
                <div style="font-size: 12px; color: #666; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{{ img.original_name }}">{{ img.original_name }}</div>
                <div style="font-size: 11px; color: #999;">{{ img.uploaded_at[:10] }}</div>
                <button type="button" class="btn btn-danger btn-sm" onclick="deleteFromLibrary('{{ img.id }}')" style="margin-top: 5px;">Delete</button>
            </div>
        </div>
        {% endfor %}
    </div>
    {% if not images %}
    <p style="color: #999; text-align: center; padding: 40px;">No images uploaded yet.</p>
    {% endif %}
</div>

<script>
async function uploadToLibrary() {
    const input = document.getElementById('library-upload');
    if (!input.files.length) return;

    for (const file of input.files) {
        const formData = new FormData();
        formData.append('file', file);

        const resp = await fetch('/api/images', { method: 'POST', body: formData });
        if (!resp.ok) {
            const data = await resp.json();
            alert('Upload failed: ' + (data.detail || 'Unknown error'));
        }
    }
    window.location.reload();
}

async function deleteFromLibrary(imageId) {
    if (!confirm('Delete this image from the library?')) return;
    const resp = await fetch('/api/images/' + imageId, { method: 'DELETE' });
    if (resp.ok) {
        document.querySelector('.library-image-card[data-id="' + imageId + '"]').remove();
    } else {
        alert('Failed to delete');
    }
}
</script>
{% endblock %}'''

SETTINGS_CONTENT = '''{% extends "base.html" %}
{% block content %}
<div class="card">
    <h2>LinkedIn Connection</h2>
    {% if linkedin_status.valid %}
    <div class="alert alert-success">Connected as: <strong>{{ linkedin_status.name }}</strong></div>
    {% else %}
    <div class="alert alert-error">{{ linkedin_status.error }}</div>
    <p>Run: <code>python execution/linkedin_oauth.py</code></p>
    {% endif %}
</div>
<div class="card">
    <h2>API Keys</h2>
    <ul style="padding-left: 20px;">
        <li>ANTHROPIC_API_KEY: {{ 'Set' if anthropic_key else 'Not set' }}</li>
        <li>LINKEDIN_CLIENT_ID: {{ 'Set' if linkedin_client else 'Not set' }}</li>
        <li>LINKEDIN_CLIENT_SECRET: {{ 'Set' if linkedin_secret else 'Not set' }}</li>
    </ul>
</div>
{% endblock %}'''

CALENDAR_CONTENT = '''{% extends "base.html" %}
{% block content %}
<style>
    .calendar-nav { display: flex; align-items: center; gap: 20px; margin-bottom: 20px; }
    .calendar-nav h2 { margin: 0; min-width: 200px; text-align: center; }
    .calendar-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; background: #e0e0e0; border-radius: 8px; overflow: hidden; }
    .calendar-header { background: #0077b5; color: white; padding: 10px; text-align: center; font-weight: 500; }
    .calendar-day { background: white; min-height: 100px; padding: 8px; cursor: pointer; transition: background 0.2s; }
    .calendar-day:hover { background: #f0f7ff; }
    .calendar-day.other-month { background: #f5f5f5; color: #999; }
    .calendar-day.today { background: #e8f4f8; }
    .calendar-day.selected { background: #cce5ff; }
    .day-number { font-weight: 500; margin-bottom: 5px; }
    .day-posts { font-size: 11px; }
    .day-post { background: #0077b5; color: white; padding: 2px 4px; border-radius: 3px; margin-bottom: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: block; text-decoration: none; }
    .day-post.status-scheduled { background: #ffc107; color: #333; }
    .day-post.status-posted { background: #28a745; }
    .day-post.status-draft { background: #6c757d; }
    .selected-date-posts { margin-top: 20px; }
</style>

<div class="card">
    <div class="calendar-nav">
        <a href="/calendar?month={{ prev_month }}" class="btn btn-secondary">&larr; Prev</a>
        <h2>{{ month_name }} {{ year }}</h2>
        <a href="/calendar?month={{ next_month }}" class="btn btn-secondary">Next &rarr;</a>
        <a href="/calendar" class="btn btn-primary" style="margin-left: auto;">Today</a>
    </div>

    <div class="calendar-grid">
        <div class="calendar-header">Sun</div>
        <div class="calendar-header">Mon</div>
        <div class="calendar-header">Tue</div>
        <div class="calendar-header">Wed</div>
        <div class="calendar-header">Thu</div>
        <div class="calendar-header">Fri</div>
        <div class="calendar-header">Sat</div>

        {% for day in calendar_days %}
        <div class="calendar-day {{ 'other-month' if not day.current_month else '' }} {{ 'today' if day.is_today else '' }} {{ 'selected' if day.date == selected_date else '' }}"
             onclick="selectDate('{{ day.date }}')">
            <div class="day-number">{{ day.day }}</div>
            <div class="day-posts">
                {% for post in day.posts[:3] %}
                <a href="/edit/{{ post.id }}" class="day-post status-{{ post.status }}" title="{{ post.topic or 'Untitled' }}">
                    {{ (post.topic or 'Untitled')[:15] }}
                </a>
                {% endfor %}
                {% if day.posts|length > 3 %}
                <span style="color: #666;">+{{ day.posts|length - 3 }} more</span>
                {% endif %}
            </div>
        </div>
        {% endfor %}
    </div>
</div>

{% if selected_date %}
<div class="card selected-date-posts">
    <h2>Posts for {{ selected_date }}</h2>
    {% if selected_posts %}
        {% for draft in selected_posts %}
        <div class="draft-item">
            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                <span style="font-family: monospace; color: #666;">ID: {{ draft.id }}</span>
                <span class="status-{{ draft.status }}">{{ draft.status.upper() }}</span>
            </div>
            {% if draft.topic %}<strong>Topic:</strong> {{ draft.topic }}<br>{% endif %}
            {% if draft.scheduled_time %}<strong>Scheduled:</strong> {{ draft.scheduled_time[:16] }}<br>{% endif %}
            {% if draft.posted_at %}<strong>Posted:</strong> {{ draft.posted_at[:16] }}<br>{% endif %}
            <div class="draft-preview" style="margin-top: 10px;">{{ draft.content[:200] }}{% if draft.content|length > 200 %}...{% endif %}</div>
            <div style="margin-top: 15px; display: flex; gap: 10px;">
                <a href="/edit/{{ draft.id }}" class="btn btn-primary btn-sm">Edit</a>
                <a href="/preview/{{ draft.id }}" class="btn btn-secondary btn-sm">Preview</a>
            </div>
        </div>
        {% endfor %}
    {% else %}
        <p style="color: #666;">No posts scheduled or posted for this date.</p>
    {% endif %}
</div>
{% endif %}

<script>
function selectDate(date) {
    window.location.href = '/calendar?month={{ year }}-{{ "%02d"|format(month) }}&date=' + date;
}
</script>
{% endblock %}'''

# Write templates
def setup_templates():
    (TEMPLATES_DIR / "base.html").write_text(BASE_TEMPLATE, encoding="utf-8")
    (TEMPLATES_DIR / "home.html").write_text(HOME_CONTENT, encoding="utf-8")
    (TEMPLATES_DIR / "drafts.html").write_text(DRAFTS_CONTENT, encoding="utf-8")
    (TEMPLATES_DIR / "scheduled.html").write_text(SCHEDULED_CONTENT, encoding="utf-8")
    (TEMPLATES_DIR / "posted.html").write_text(POSTED_CONTENT, encoding="utf-8")
    (TEMPLATES_DIR / "hooks_bank.html").write_text(HOOKS_BANK_CONTENT, encoding="utf-8")
    (TEMPLATES_DIR / "ideas_bank.html").write_text(IDEAS_BANK_CONTENT, encoding="utf-8")
    (TEMPLATES_DIR / "edit.html").write_text(EDIT_CONTENT, encoding="utf-8")
    (TEMPLATES_DIR / "preview.html").write_text(PREVIEW_CONTENT, encoding="utf-8")
    (TEMPLATES_DIR / "settings.html").write_text(SETTINGS_CONTENT, encoding="utf-8")
    (TEMPLATES_DIR / "calendar.html").write_text(CALENDAR_CONTENT, encoding="utf-8")
    (TEMPLATES_DIR / "images_library.html").write_text(IMAGES_LIBRARY_CONTENT, encoding="utf-8")

setup_templates()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# =============================================================================
# ROUTES
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, message: str = None, type: str = None):
    return templates.TemplateResponse("home.html", {
        "request": request,
        "page": "home",
        "ideas": None,
        "hooks": None,
        "hook_groups": None,
        "topic": None,
        "message": message,
        "message_type": type
    })


@app.post("/generate-ideas", response_class=HTMLResponse)
async def generate_ideas_route(request: Request, topic: str = Form(...), context: str = Form("")):
    try:
        ideas = generate_ideas(topic, context, num_ideas=15)
        return templates.TemplateResponse("home.html", {
            "request": request,
            "page": "home",
            "ideas": ideas,
            "hooks": None,
            "hook_groups": None,
            "topic": topic,
            "context": context,
            "message": f"Generated {len(ideas)} ideas from your knowledge base",
            "message_type": "success"
        })
    except Exception as e:
        return templates.TemplateResponse("home.html", {
            "request": request,
            "page": "home",
            "ideas": None,
            "hooks": None,
            "hook_groups": None,
            "topic": topic,
            "message": f"Error: {str(e)}",
            "message_type": "error"
        })


@app.post("/generate-hooks-from-ideas", response_class=HTMLResponse)
async def generate_hooks_from_ideas_route(request: Request):
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    form = await request.form()
    topic = form.get("topic", "")

    # Collect selected ideas with their angles
    selected_ideas = []
    for key, value in form.items():
        if key.startswith("selected_") and value == "1":
            idx = key.replace("selected_", "")
            idea_key = f"idea_{idx}"
            angle_key = f"angle_{idx}"
            if idea_key in form:
                idea_text = form[idea_key]
                angle = form.get(angle_key, "")
                if idea_text.strip():
                    selected_ideas.append({
                        "idea": idea_text.strip(),
                        "angle": angle
                    })

    if not selected_ideas:
        return RedirectResponse(url="/?message=No+ideas+selected&type=error", status_code=303)

    # Generate 30 hooks for each idea in parallel
    def generate_for_idea(idea_data):
        try:
            hooks = generate_hooks(topic, context=idea_data["idea"], num_hooks=30)
            return {
                "idea": idea_data["idea"],
                "angle": idea_data["angle"],
                "hooks": hooks
            }
        except Exception as e:
            return {
                "idea": idea_data["idea"],
                "angle": idea_data["angle"],
                "hooks": [],
                "error": str(e)
            }

    try:
        # Run hook generation in parallel using thread pool
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=len(selected_ideas)) as executor:
            hook_groups = await asyncio.gather(*[
                loop.run_in_executor(executor, generate_for_idea, idea)
                for idea in selected_ideas
            ])

        total_hooks = sum(len(g["hooks"]) for g in hook_groups)

        return templates.TemplateResponse("home.html", {
            "request": request,
            "page": "home",
            "ideas": None,
            "hooks": None,
            "hook_groups": hook_groups,
            "topic": topic,
            "message": f"Generated {total_hooks} hooks across {len(hook_groups)} ideas",
            "message_type": "success"
        })
    except Exception as e:
        return templates.TemplateResponse("home.html", {
            "request": request,
            "page": "home",
            "ideas": None,
            "hooks": None,
            "hook_groups": None,
            "topic": topic,
            "message": f"Error: {str(e)}",
            "message_type": "error"
        })


@app.post("/create-drafts")
async def create_drafts_route(request: Request):
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    form = await request.form()
    topic = form.get("topic", "")

    # Collect ideas by group index
    ideas_by_group = {}
    for key, value in form.items():
        if key.startswith("idea_") and not key.startswith("idea_bank"):
            group_idx = key.replace("idea_", "")
            ideas_by_group[group_idx] = value

    # Collect selected hooks with their group (idea) info
    selected_items = []
    for key, value in form.items():
        if key.startswith("selected_") and value == "1":
            # Format: selected_{group}_{hookIdx}
            parts = key.replace("selected_", "").split("_")
            if len(parts) == 2:
                group_idx, hook_idx = parts
                hook_key = f"hook_{group_idx}_{hook_idx}"
                if hook_key in form:
                    hook_text = form[hook_key]
                    idea_text = ideas_by_group.get(group_idx, "")
                    if hook_text.strip():
                        selected_items.append({
                            "hook": hook_text.strip(),
                            "idea": idea_text
                        })

    if not selected_items:
        return RedirectResponse(url="/?message=No+hooks+selected&type=error", status_code=303)

    # Load knowledge base once
    kb = load_knowledge_base()

    # Generate drafts in parallel
    def create_single_draft(item):
        try:
            # Use both the idea and hook as context for body generation
            context = f"Idea/angle: {item['idea']}" if item['idea'] else None
            body = generate_post_body(topic, item['hook'], kb, additional_context=context)
            draft = create_draft(
                content=body,
                hooks=[item['hook']],
                selected_hook=0,
                topic=f"{topic} - {item['idea'][:50]}..." if item['idea'] else topic
            )
            return {"success": True, "draft": draft}
        except Exception as e:
            return {"success": False, "error": str(e)}

    try:
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=min(len(selected_items), 5)) as executor:
            results = await asyncio.gather(*[
                loop.run_in_executor(executor, create_single_draft, item)
                for item in selected_items
            ])

        created_count = sum(1 for r in results if r["success"])
        return RedirectResponse(
            url=f"/drafts?message=Created+{created_count}+draft(s)&type=success",
            status_code=303
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/?message=Error:+{str(e)}&type=error",
            status_code=303
        )


@app.get("/drafts", response_class=HTMLResponse)
async def drafts_page(request: Request, message: str = None, type: str = None):
    drafts = list_drafts(status="draft")
    return templates.TemplateResponse("drafts.html", {
        "request": request,
        "page": "drafts",
        "drafts": drafts,
        "message": message,
        "message_type": type
    })


@app.get("/scheduled", response_class=HTMLResponse)
async def scheduled_page(request: Request, message: str = None, type: str = None):
    drafts = list_drafts(status="scheduled")
    return templates.TemplateResponse("scheduled.html", {
        "request": request,
        "page": "scheduled",
        "drafts": drafts,
        "message": message,
        "message_type": type
    })


@app.get("/posted", response_class=HTMLResponse)
async def posted_page(request: Request, message: str = None, type: str = None):
    drafts = list_drafts(status="posted")
    return templates.TemplateResponse("posted.html", {
        "request": request,
        "page": "posted",
        "drafts": drafts,
        "message": message,
        "message_type": type
    })


@app.post("/mark-status/{draft_id}/{status}")
async def mark_status_route(draft_id: str, status: str):
    if status not in ["draft", "scheduled", "posted"]:
        return RedirectResponse(url="/drafts?message=Invalid+status&type=error", status_code=303)

    draft = get_draft(draft_id)
    if not draft:
        return RedirectResponse(url="/drafts?message=Draft+not+found&type=error", status_code=303)

    updates = {"status": status}
    # Set posted_at when marking as posted
    if status == "posted":
        updates["posted_at"] = dt.now().isoformat()

    update_draft(draft_id, **updates)

    # Redirect to the appropriate page based on the new status
    redirect_map = {
        "draft": "/drafts",
        "scheduled": "/scheduled",
        "posted": "/posted"
    }
    return RedirectResponse(
        url=f"{redirect_map[status]}?message=Status+updated+to+{status}&type=success",
        status_code=303
    )


@app.get("/hooks-bank", response_class=HTMLResponse)
async def hooks_bank_page(request: Request, message: str = None, type: str = None):
    hooks = get_hooks_bank()
    return templates.TemplateResponse("hooks_bank.html", {
        "request": request,
        "page": "hooks-bank",
        "hooks": hooks,
        "message": message,
        "message_type": type
    })


@app.post("/api/save-hook")
async def api_save_hook(request: Request):
    data = await request.json()
    hook = data.get("hook", "").strip()
    topic = data.get("topic", "").strip()

    if not hook:
        raise HTTPException(status_code=400, detail="Hook is required")

    entry = save_hook_to_bank(hook, topic)
    return JSONResponse({"success": True, "id": entry["id"]})


@app.post("/api/save-idea")
async def api_save_idea(request: Request):
    data = await request.json()
    idea = data.get("idea", "").strip()
    topic = data.get("topic", "").strip()
    angle = data.get("angle", "").strip()

    if not idea:
        raise HTTPException(status_code=400, detail="Idea is required")

    entry = save_idea_to_bank(idea, topic, angle)
    return JSONResponse({"success": True, "id": entry["id"]})


@app.get("/ideas-bank", response_class=HTMLResponse)
async def ideas_bank_page(request: Request, message: str = None, type: str = None):
    ideas = get_ideas_bank()
    return templates.TemplateResponse("ideas_bank.html", {
        "request": request,
        "page": "ideas-bank",
        "ideas": ideas,
        "message": message,
        "message_type": type
    })


@app.post("/delete-saved-idea/{idea_id}")
async def delete_saved_idea_route(idea_id: str):
    delete_idea_from_bank(idea_id)
    return RedirectResponse(url="/ideas-bank?message=Idea+deleted&type=success", status_code=303)


@app.post("/delete-saved-hook/{hook_id}")
async def delete_saved_hook_route(hook_id: str):
    delete_hook_from_bank(hook_id)
    return RedirectResponse(url="/hooks-bank?message=Hook+deleted&type=success", status_code=303)


@app.get("/edit/{draft_id}", response_class=HTMLResponse)
async def edit_page(request: Request, draft_id: str, message: str = None, type: str = None):
    draft = get_draft(draft_id)
    if not draft:
        return RedirectResponse(url="/drafts?message=Draft+not+found&type=error", status_code=303)

    # Get attached image IDs from draft
    attached_ids = [img_ref.get("id") or img_ref for img_ref in draft.get("images", [])]

    # Resolve attached images from library
    attached_images = []
    for aid in attached_ids:
        img = get_image(aid) if isinstance(aid, str) else None
        if img:
            attached_images.append(img)

    # All library images
    library_images = list_images()

    return templates.TemplateResponse("edit.html", {
        "request": request,
        "page": "edit",
        "draft": draft,
        "attached_images": attached_images,
        "attached_ids": attached_ids,
        "library_images": library_images,
        "message": message,
        "message_type": type
    })


@app.post("/update/{draft_id}")
async def update_route(draft_id: str, content: str = Form(...), hook: str = Form("")):
    draft = get_draft(draft_id)
    if not draft:
        return RedirectResponse(url="/drafts?message=Draft+not+found&type=error", status_code=303)

    updates = {"content": content}
    if hook.strip():
        updates["hooks"] = [hook.strip()]
        updates["selected_hook"] = 0

    update_draft(draft_id, **updates)
    return RedirectResponse(url="/drafts?message=Draft+updated&type=success", status_code=303)


@app.get("/preview/{draft_id}", response_class=HTMLResponse)
async def preview_page(request: Request, draft_id: str):
    draft = get_draft(draft_id)
    if not draft:
        return RedirectResponse(url="/drafts?message=Draft+not+found&type=error", status_code=303)

    final_content = get_final_post(draft_id)

    # Resolve attached images
    attached_images = []
    for img_ref in draft.get("images", []):
        aid = img_ref.get("id") if isinstance(img_ref, dict) else img_ref
        img = get_image(aid)
        if img:
            attached_images.append(img)

    return templates.TemplateResponse("preview.html", {
        "request": request,
        "page": "preview",
        "draft": draft,
        "final_content": final_content,
        "attached_images": attached_images,
    })


@app.post("/post/{draft_id}")
async def post_to_linkedin_route(draft_id: str):
    draft = get_draft(draft_id)
    if not draft:
        return RedirectResponse(url="/drafts?message=Draft+not+found&type=error", status_code=303)

    final_content = get_final_post(draft_id)

    # Get image URLs from library
    image_urls = []
    for img_ref in draft.get("images", []):
        aid = img_ref.get("id") if isinstance(img_ref, dict) else img_ref
        url = get_image_url(aid)
        if url:
            image_urls.append(url)

    try:
        result = post_to_linkedin(final_content, image_urls if image_urls else None)
        if result["success"]:
            update_draft(draft_id, status="posted", posted_at=dt.now().isoformat())
            return RedirectResponse(url="/drafts?message=Posted+successfully!&type=success", status_code=303)
        else:
            return RedirectResponse(
                url=f"/preview/{draft_id}?message=Error:+{result.get('error', 'Unknown')}&type=error",
                status_code=303
            )
    except Exception as e:
        return RedirectResponse(
            url=f"/preview/{draft_id}?message=Error:+{str(e)}&type=error",
            status_code=303
        )


@app.post("/delete/{draft_id}")
async def delete_route(draft_id: str):
    delete_draft(draft_id)
    return RedirectResponse(url="/drafts?message=Draft+deleted&type=success", status_code=303)


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    linkedin_status = check_token_validity()
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "page": "settings",
        "linkedin_status": linkedin_status,
        "anthropic_key": bool(os.getenv("ANTHROPIC_API_KEY")),
        "linkedin_client": bool(os.getenv("LINKEDIN_CLIENT_ID")),
        "linkedin_secret": bool(os.getenv("LINKEDIN_CLIENT_SECRET")),
    })


# =============================================================================
# CALENDAR ROUTES
# =============================================================================

@app.get("/calendar", response_class=HTMLResponse)
async def calendar_page(request: Request, month: str = None, date: str = None):
    """
    Calendar view showing posts by date.

    Args:
        month: Optional month in YYYY-MM format
        date: Optional selected date in YYYY-MM-DD format
    """
    from datetime import date as date_type

    # Parse month or use current
    today = date_type.today()
    if month:
        try:
            parts = month.split("-")
            year = int(parts[0])
            month_num = int(parts[1])
        except (ValueError, IndexError):
            year = today.year
            month_num = today.month
    else:
        year = today.year
        month_num = today.month

    # Get drafts for this month
    month_drafts = list_drafts_by_date(year, month_num)

    # Build calendar grid
    cal_obj = cal.Calendar(firstweekday=6)  # Sunday first
    calendar_days = []

    for week in cal_obj.monthdatescalendar(year, month_num):
        for day_date in week:
            day_str = day_date.strftime("%Y-%m-%d")
            # Get posts for this day
            day_posts = []
            for draft in month_drafts:
                scheduled = draft.get("scheduled_time", "")
                posted = draft.get("posted_at", "")
                if scheduled and scheduled[:10] == day_str:
                    day_posts.append(draft)
                elif posted and posted[:10] == day_str:
                    day_posts.append(draft)

            calendar_days.append({
                "day": day_date.day,
                "date": day_str,
                "current_month": day_date.month == month_num,
                "is_today": day_date == today,
                "posts": day_posts
            })

    # Get posts for selected date
    selected_posts = []
    if date:
        selected_posts = get_drafts_for_date(date)

    # Calculate prev/next months
    if month_num == 1:
        prev_month = f"{year-1}-12"
    else:
        prev_month = f"{year}-{month_num-1:02d}"

    if month_num == 12:
        next_month = f"{year+1}-01"
    else:
        next_month = f"{year}-{month_num+1:02d}"

    month_name = cal.month_name[month_num]

    return templates.TemplateResponse("calendar.html", {
        "request": request,
        "page": "calendar",
        "year": year,
        "month": month_num,
        "month_name": month_name,
        "calendar_days": calendar_days,
        "prev_month": prev_month,
        "next_month": next_month,
        "selected_date": date,
        "selected_posts": selected_posts
    })


# =============================================================================
# IMAGE LIBRARY ROUTES
# =============================================================================

@app.get("/images", response_class=HTMLResponse)
async def images_library_page(request: Request, message: str = None, type: str = None):
    """Image library page."""
    images = list_images()
    return templates.TemplateResponse("images_library.html", {
        "request": request,
        "page": "images",
        "images": images,
        "message": message,
        "message_type": type,
    })


@app.post("/api/images")
async def api_upload_image(file: UploadFile = File(...)):
    """Upload an image to the library."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large (max 10MB)")

    try:
        image_meta = save_image(content, file.filename or "image.jpg")
        return JSONResponse({"success": True, "image": image_meta})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/images")
async def api_list_images():
    """List all library images."""
    return JSONResponse({"images": list_images()})


@app.get("/api/images/{image_id}/file")
async def api_serve_image(image_id: str):
    """Proxy an image from S3 to the browser."""
    from s3_storage import download_bytes
    img = get_image(image_id)
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")

    ext = img.get("s3_key", "").rsplit(".", 1)[-1].lower()
    content_types = {
        "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "png": "image/png", "gif": "image/gif", "webp": "image/webp",
    }
    content_type = content_types.get(ext, "image/jpeg")

    try:
        data = download_bytes(img["s3_key"])
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to fetch image from storage")

    return Response(
        content=data,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.delete("/api/images/{image_id}")
async def api_delete_image(image_id: str):
    """Delete an image from the library."""
    deleted = delete_image(image_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Image not found")
    return JSONResponse({"success": True})


@app.post("/api/drafts/{draft_id}/attach-image/{image_id}")
async def attach_image_to_draft(draft_id: str, image_id: str):
    """Attach a library image to a draft."""
    draft = get_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    img = get_image(image_id)
    if not img:
        raise HTTPException(status_code=404, detail="Image not found in library")

    images = draft.get("images", [])
    # Don't double-attach
    existing_ids = {
        (ref.get("id") if isinstance(ref, dict) else ref) for ref in images
    }
    if image_id not in existing_ids:
        images.append({"id": image_id})
        update_draft(draft_id, images=images)

    return JSONResponse({"success": True})


@app.delete("/api/drafts/{draft_id}/attach-image/{image_id}")
async def detach_image_from_draft(draft_id: str, image_id: str):
    """Detach a library image from a draft."""
    draft = get_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    images = draft.get("images", [])
    images = [
        ref for ref in images
        if (ref.get("id") if isinstance(ref, dict) else ref) != image_id
    ]
    update_draft(draft_id, images=images)

    return JSONResponse({"success": True})


@app.post("/api/drafts/{draft_id}/schedule")
async def schedule_draft(request: Request, draft_id: str):
    """Set or update the scheduled time for a draft."""
    draft = get_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    data = await request.json()
    scheduled_time = data.get("scheduled_time")

    updates = {"scheduled_time": scheduled_time}
    if scheduled_time:
        updates["status"] = "scheduled"

    update_draft(draft_id, **updates)
    return JSONResponse({"success": True})


@app.post("/api/drafts/{draft_id}/posted-date")
async def set_posted_date(request: Request, draft_id: str):
    """Set or update the posted_at date for a draft."""
    draft = get_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    data = await request.json()
    posted_at = data.get("posted_at")

    update_draft(draft_id, posted_at=posted_at)
    return JSONResponse({"success": True})


def main():
    print("Starting LinkedIn Content Creator...")
    print("Open http://localhost:5000 in your browser")
    uvicorn.run("web_ui:app", host="0.0.0.0", port=5000, reload=True)


if __name__ == "__main__":
    main()
