"""
Web UI for viewing, editing, and scheduling LinkedIn post drafts.
Built with FastAPI.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import uvicorn

from draft_storage import (
    list_drafts, get_draft, create_draft, update_draft,
    delete_draft, get_final_post
)
from generate_post import generate_post_with_hooks, load_knowledge_base, list_templates
from generate_hooks import generate_hooks
from post_to_linkedin import post_to_linkedin, check_token_validity

load_dotenv()

app = FastAPI(title="LinkedIn Draft Manager")

# Create templates directory and set up Jinja2
TEMPLATES_DIR = Path(__file__).parent / "templates"
TEMPLATES_DIR.mkdir(exist_ok=True)

# Write the base template
BASE_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LinkedIn Draft Manager</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        header {
            background: #0077b5;
            color: white;
            padding: 20px;
            margin-bottom: 20px;
        }
        header h1 { font-size: 24px; }
        header p { opacity: 0.9; font-size: 14px; }
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
        .draft-item {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            background: #fafafa;
        }
        .draft-item:hover { border-color: #0077b5; }
        .draft-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .draft-id { font-family: monospace; color: #666; font-size: 12px; }
        .draft-status {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }
        .status-draft { background: #fff3cd; color: #856404; }
        .status-scheduled { background: #cce5ff; color: #004085; }
        .status-posted { background: #d4edda; color: #155724; }
        .draft-preview {
            color: #555;
            font-size: 14px;
            white-space: pre-wrap;
            max-height: 100px;
            overflow: hidden;
        }
        .draft-meta { font-size: 12px; color: #888; margin-top: 10px; }
        .draft-actions { margin-top: 15px; display: flex; gap: 10px; flex-wrap: wrap; }
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
        .btn-secondary:hover { background: #545b62; }
        .btn-success { background: #28a745; color: white; }
        .btn-success:hover { background: #1e7e34; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-danger:hover { background: #c82333; }
        .btn-warning { background: #ffc107; color: #212529; }
        textarea, input[type="text"], select {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            font-family: inherit;
            margin-bottom: 15px;
        }
        textarea { min-height: 200px; resize: vertical; }
        textarea:focus, input:focus { border-color: #0077b5; outline: none; }
        label { display: block; margin-bottom: 5px; font-weight: 500; }
        .hook-option {
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 4px;
            margin-bottom: 10px;
            cursor: pointer;
        }
        .hook-option:hover { border-color: #0077b5; background: #f8f9fa; }
        .hook-option.selected { border-color: #0077b5; background: #e8f4f8; }
        .hook-label { font-weight: bold; color: #0077b5; }
        .alert {
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
        }
        .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .alert-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .alert-info { background: #cce5ff; color: #004085; border: 1px solid #b8daff; }
        .form-row { display: flex; gap: 15px; margin-bottom: 15px; }
        .form-row > div { flex: 1; }
        .empty-state { text-align: center; padding: 40px; color: #666; }
        .empty-state p { margin-bottom: 20px; }
        .preview-box {
            background: #f8f9fa;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            padding: 15px;
            white-space: pre-wrap;
            font-size: 14px;
            max-height: 400px;
            overflow-y: auto;
        }
        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        @media (max-width: 768px) { .grid-2 { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1>LinkedIn Draft Manager</h1>
            <p>Create, edit, and schedule AI-powered LinkedIn posts</p>
            <nav>
                <a href="/" class="{{ 'active' if page == 'home' else '' }}">Drafts</a>
                <a href="/create" class="{{ 'active' if page == 'create' else '' }}">Create New</a>
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
</body>
</html>'''

HOME_CONTENT = '''{% extends "base.html" %}
{% block content %}
<div class="card">
    <h2>Your Drafts</h2>
    {% if drafts %}
        {% for draft in drafts %}
        <div class="draft-item">
            <div class="draft-header">
                <span class="draft-id">ID: {{ draft.id }}</span>
                <span class="draft-status status-{{ draft.status }}">{{ draft.status.upper() }}</span>
            </div>
            {% if draft.topic %}<strong>Topic:</strong> {{ draft.topic }}<br><br>{% endif %}
            {% if draft.hooks %}
            <strong>Hooks ({{ draft.hooks|length }}):</strong>
            <div style="margin: 10px 0; padding-left: 15px; border-left: 3px solid #0077b5;">
                {% for hook in draft.hooks[:3] %}
                <div style="margin-bottom: 5px; font-size: 13px;">
                    {{ loop.index }}. {{ hook[:80] }}{% if hook|length > 80 %}...{% endif %}
                    {% if draft.selected_hook == loop.index0 %} <strong>(selected)</strong>{% endif %}
                </div>
                {% endfor %}
            </div>
            {% endif %}
            <div class="draft-preview">{{ draft.content[:300] }}{% if draft.content|length > 300 %}...{% endif %}</div>
            <div class="draft-meta">
                Created: {{ draft.created_at[:16] }} | Updated: {{ draft.updated_at[:16] }}
                {% if draft.template_used %} | Template: {{ draft.template_used }}{% endif %}
            </div>
            <div class="draft-actions">
                <a href="/edit/{{ draft.id }}" class="btn btn-primary">Edit</a>
                <a href="/preview/{{ draft.id }}" class="btn btn-secondary">Preview</a>
                <form action="/post/{{ draft.id }}" method="POST" style="display:inline;">
                    <button type="submit" class="btn btn-success" onclick="return confirm('Post to LinkedIn now?')">Post to LinkedIn</button>
                </form>
                <form action="/delete/{{ draft.id }}" method="POST" style="display:inline;">
                    <button type="submit" class="btn btn-danger" onclick="return confirm('Delete this draft?')">Delete</button>
                </form>
            </div>
        </div>
        {% endfor %}
    {% else %}
        <div class="empty-state">
            <p>No drafts yet. Create your first AI-powered post!</p>
            <a href="/create" class="btn btn-primary">Create New Draft</a>
        </div>
    {% endif %}
</div>
{% endblock %}'''

CREATE_CONTENT = '''{% extends "base.html" %}
{% block content %}
<div class="grid-2">
    <div class="card">
        <h2>Generate AI Post</h2>
        <form action="/generate" method="POST">
            <label>Topic / Theme</label>
            <input type="text" name="topic" placeholder="e.g., AI coaching and why human coaches still matter" required>
            <label>Additional Context (optional)</label>
            <textarea name="context" rows="3" placeholder="Any specific points, stories, or angles you want included..."></textarea>
            <button type="submit" class="btn btn-primary">Generate Post with AI</button>
        </form>
    </div>
    <div class="card">
        <h2>Create Manual Draft</h2>
        <form action="/create-manual" method="POST">
            <label>Topic (optional)</label>
            <input type="text" name="topic" placeholder="Topic for reference">
            <label>Post Content</label>
            <textarea name="content" placeholder="Write your post content here..." required></textarea>
            <label>Generate Hooks?</label>
            <select name="generate_hooks">
                <option value="yes">Yes - Generate 5 hook options</option>
                <option value="no">No - Use content as-is</option>
            </select>
            <button type="submit" class="btn btn-primary">Create Draft</button>
        </form>
    </div>
</div>
<div class="card">
    <h2>Available Templates</h2>
    <p style="margin-bottom: 15px;">Reference these proven templates when creating content:</p>
    <div style="display: flex; flex-wrap: wrap; gap: 10px;">
        {% for template in templates %}
        <span style="background: #e8f4f8; padding: 5px 10px; border-radius: 4px; font-size: 13px;">{{ template }}</span>
        {% endfor %}
    </div>
</div>
{% endblock %}'''

EDIT_CONTENT = '''{% extends "base.html" %}
{% block content %}
<div class="card">
    <h2>Edit Draft</h2>
    <form action="/update/{{ draft.id }}" method="POST">
        <label>Topic</label>
        <input type="text" name="topic" value="{{ draft.topic or '' }}">
        {% if draft.hooks %}
        <label>Select Hook</label>
        <div style="margin-bottom: 15px;">
            {% for hook in draft.hooks %}
            <div class="hook-option {{ 'selected' if draft.selected_hook == loop.index0 else '' }}"
                 onclick="document.getElementById('hook_{{ loop.index0 }}').checked = true; document.querySelectorAll('.hook-option').forEach(el => el.classList.remove('selected')); this.classList.add('selected');">
                <input type="radio" name="selected_hook" id="hook_{{ loop.index0 }}"
                       value="{{ loop.index0 }}" {{ 'checked' if draft.selected_hook == loop.index0 else '' }}
                       style="margin-right: 10px;">
                <span class="hook-label">{{ loop.index }}.</span> {{ hook }}
            </div>
            {% endfor %}
        </div>
        {% endif %}
        <label>Post Content</label>
        <textarea name="content" rows="12">{{ draft.content }}</textarea>
        <div class="form-row">
            <div>
                <label>Status</label>
                <select name="status">
                    <option value="draft" {{ 'selected' if draft.status == 'draft' else '' }}>Draft</option>
                    <option value="scheduled" {{ 'selected' if draft.status == 'scheduled' else '' }}>Scheduled</option>
                    <option value="posted" {{ 'selected' if draft.status == 'posted' else '' }}>Posted</option>
                </select>
            </div>
        </div>
        <div style="display: flex; gap: 10px;">
            <button type="submit" class="btn btn-primary">Save Changes</button>
            <a href="/" class="btn btn-secondary">Cancel</a>
        </div>
    </form>
</div>
<div class="card">
    <h2>Regenerate Hooks</h2>
    <form action="/regenerate-hooks/{{ draft.id }}" method="POST">
        <p style="margin-bottom: 15px;">Generate new hook options for the current content.</p>
        <button type="submit" class="btn btn-secondary">Regenerate Hooks</button>
    </form>
</div>
{% endblock %}'''

PREVIEW_CONTENT = '''{% extends "base.html" %}
{% block content %}
<div class="card">
    <h2>Post Preview</h2>
    <p style="margin-bottom: 15px;">This is how your post will appear on LinkedIn:</p>
    <div class="preview-box">{{ final_content }}</div>
    <div style="margin-top: 20px; display: flex; gap: 10px;">
        <a href="/edit/{{ draft.id }}" class="btn btn-primary">Edit</a>
        <form action="/post/{{ draft.id }}" method="POST" style="display:inline;">
            <button type="submit" class="btn btn-success" onclick="return confirm('Post to LinkedIn now?')">Post to LinkedIn</button>
        </form>
        <a href="/" class="btn btn-secondary">Back to Drafts</a>
    </div>
</div>
<div class="card">
    <h2>Draft Details</h2>
    <p><strong>ID:</strong> {{ draft.id }}</p>
    <p><strong>Topic:</strong> {{ draft.topic or 'Not specified' }}</p>
    <p><strong>Status:</strong> {{ draft.status }}</p>
    <p><strong>Created:</strong> {{ draft.created_at }}</p>
    <p><strong>Selected Hook:</strong> {{ (draft.selected_hook + 1) if draft.selected_hook is not none else 'None' }}</p>
    <p><strong>Character Count:</strong> {{ final_content|length }}</p>
</div>
{% endblock %}'''

SETTINGS_CONTENT = '''{% extends "base.html" %}
{% block content %}
<div class="card">
    <h2>LinkedIn Connection</h2>
    {% if linkedin_status.valid %}
    <div class="alert alert-success">
        Connected as: <strong>{{ linkedin_status.name }}</strong>
        {% if linkedin_status.email %} ({{ linkedin_status.email }}){% endif %}
    </div>
    {% else %}
    <div class="alert alert-error">{{ linkedin_status.error }}</div>
    <p style="margin-top: 15px;">Run this command to authenticate:</p>
    <pre style="background: #f5f5f5; padding: 15px; border-radius: 4px; overflow-x: auto;">python execution/linkedin_oauth.py</pre>
    {% endif %}
</div>
<div class="card">
    <h2>API Keys</h2>
    <p>Configure these in your <code>.env</code> file:</p>
    <ul style="margin: 15px 0; padding-left: 20px;">
        <li><strong>ANTHROPIC_API_KEY</strong>: {{ 'Set' if anthropic_key else 'Not set' }}</li>
        <li><strong>LINKEDIN_CLIENT_ID</strong>: {{ 'Set' if linkedin_client else 'Not set' }}</li>
        <li><strong>LINKEDIN_CLIENT_SECRET</strong>: {{ 'Set' if linkedin_secret else 'Not set' }}</li>
    </ul>
</div>
<div class="card">
    <h2>Knowledge Base</h2>
    <p>Content loaded from: <code>knowledge_bases/Smiths/Written Posts/</code></p>
    <ul style="margin: 15px 0; padding-left: 20px;">
        <li>Origin Story: {{ 'Loaded' if kb.origin_story else 'Not found' }}</li>
        <li>Best Posts: {{ 'Loaded' if kb.best_posts else 'Not found' }}</li>
        <li>Templates: {{ 'Loaded' if kb.templates else 'Not found' }}</li>
    </ul>
</div>
{% endblock %}'''

# Write templates to files
def setup_templates():
    (TEMPLATES_DIR / "base.html").write_text(BASE_TEMPLATE)
    (TEMPLATES_DIR / "home.html").write_text(HOME_CONTENT)
    (TEMPLATES_DIR / "create.html").write_text(CREATE_CONTENT)
    (TEMPLATES_DIR / "edit.html").write_text(EDIT_CONTENT)
    (TEMPLATES_DIR / "preview.html").write_text(PREVIEW_CONTENT)
    (TEMPLATES_DIR / "settings.html").write_text(SETTINGS_CONTENT)

setup_templates()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, message: str = None, type: str = None):
    drafts = list_drafts()
    return templates.TemplateResponse("home.html", {
        "request": request,
        "page": "home",
        "drafts": drafts,
        "message": message,
        "message_type": type
    })


@app.get("/create", response_class=HTMLResponse)
async def create_page(request: Request, message: str = None, type: str = None):
    template_list = list_templates()
    return templates.TemplateResponse("create.html", {
        "request": request,
        "page": "create",
        "templates": template_list,
        "message": message,
        "message_type": type
    })


@app.post("/generate")
async def generate(topic: str = Form(...), context: str = Form("")):
    try:
        kb = load_knowledge_base()
        body, hooks = generate_post_with_hooks(topic, kb)
        draft = create_draft(content=body, hooks=hooks, topic=topic)
        return RedirectResponse(
            url=f"/edit/{draft['id']}?message=Post+generated+successfully!&type=success",
            status_code=303
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/create?message=Error+generating+post:+{str(e)}&type=error",
            status_code=303
        )


@app.post("/create-manual")
async def create_manual(
    topic: str = Form(""),
    content: str = Form(...),
    generate_hooks_opt: str = Form("no", alias="generate_hooks")
):
    hooks = []
    if generate_hooks_opt == "yes":
        try:
            hooks = generate_hooks(content)
        except Exception:
            pass

    draft = create_draft(content=content, hooks=hooks, topic=topic)
    return RedirectResponse(url="/?message=Draft+created!&type=success", status_code=303)


@app.get("/edit/{draft_id}", response_class=HTMLResponse)
async def edit(request: Request, draft_id: str, message: str = None, type: str = None):
    draft = get_draft(draft_id)
    if not draft:
        return RedirectResponse(url="/?message=Draft+not+found&type=error", status_code=303)

    return templates.TemplateResponse("edit.html", {
        "request": request,
        "page": "edit",
        "draft": draft,
        "message": message,
        "message_type": type
    })


@app.post("/update/{draft_id}")
async def update(
    draft_id: str,
    content: str = Form(...),
    topic: str = Form(""),
    status: str = Form("draft"),
    selected_hook: str = Form(None)
):
    updates = {"content": content, "topic": topic, "status": status}
    if selected_hook is not None and selected_hook != "":
        updates["selected_hook"] = int(selected_hook)

    update_draft(draft_id, **updates)
    return RedirectResponse(url="/?message=Draft+updated!&type=success", status_code=303)


@app.post("/regenerate-hooks/{draft_id}")
async def regenerate_hooks_route(draft_id: str):
    draft = get_draft(draft_id)
    if not draft:
        return RedirectResponse(url="/?message=Draft+not+found&type=error", status_code=303)

    try:
        hooks = generate_hooks(draft["content"])
        update_draft(draft_id, hooks=hooks, selected_hook=None)
        return RedirectResponse(
            url=f"/edit/{draft_id}?message=Hooks+regenerated!&type=success",
            status_code=303
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/edit/{draft_id}?message=Error:+{str(e)}&type=error",
            status_code=303
        )


@app.get("/preview/{draft_id}", response_class=HTMLResponse)
async def preview(request: Request, draft_id: str, message: str = None, type: str = None):
    draft = get_draft(draft_id)
    if not draft:
        return RedirectResponse(url="/?message=Draft+not+found&type=error", status_code=303)

    final_content = get_final_post(draft_id)
    return templates.TemplateResponse("preview.html", {
        "request": request,
        "page": "preview",
        "draft": draft,
        "final_content": final_content,
        "message": message,
        "message_type": type
    })


@app.post("/post/{draft_id}")
async def post_to_li(draft_id: str):
    draft = get_draft(draft_id)
    if not draft:
        return RedirectResponse(url="/?message=Draft+not+found&type=error", status_code=303)

    final_content = get_final_post(draft_id)

    try:
        result = post_to_linkedin(final_content)
        if result["success"]:
            update_draft(draft_id, status="posted")
            return RedirectResponse(
                url="/?message=Posted+to+LinkedIn+successfully!&type=success",
                status_code=303
            )
        else:
            error = result.get("error", "Unknown error")
            return RedirectResponse(
                url=f"/preview/{draft_id}?message=LinkedIn+error:+{error}&type=error",
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
    return RedirectResponse(url="/?message=Draft+deleted&type=success", status_code=303)


@app.get("/settings", response_class=HTMLResponse)
async def settings(request: Request, message: str = None, type: str = None):
    linkedin_status = check_token_validity()
    kb = load_knowledge_base()

    return templates.TemplateResponse("settings.html", {
        "request": request,
        "page": "settings",
        "linkedin_status": linkedin_status,
        "kb": kb,
        "anthropic_key": bool(os.getenv("ANTHROPIC_API_KEY")),
        "linkedin_client": bool(os.getenv("LINKEDIN_CLIENT_ID")),
        "linkedin_secret": bool(os.getenv("LINKEDIN_CLIENT_SECRET")),
        "message": message,
        "message_type": type
    })


# API endpoints
@app.get("/api/drafts")
async def api_drafts():
    return list_drafts()


@app.get("/api/draft/{draft_id}")
async def api_draft(draft_id: str):
    draft = get_draft(draft_id)
    if draft:
        return draft
    raise HTTPException(status_code=404, detail="Draft not found")


def main():
    print("Starting LinkedIn Draft Manager...")
    print("Open http://localhost:5000 in your browser")
    uvicorn.run("web_ui:app", host="0.0.0.0", port=5000, reload=True)


if __name__ == "__main__":
    main()
