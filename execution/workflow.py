#!/usr/bin/env python3
"""
Main workflow script for AI-powered LinkedIn post creation.

Usage:
    python workflow.py generate "topic"     # Generate a new AI post
    python workflow.py list                 # List all drafts
    python workflow.py view <id>            # View a specific draft
    python workflow.py post <id>            # Post to LinkedIn
    python workflow.py hypefury <id>        # Send to Hypefury
    python workflow.py ui                   # Start the web UI
"""
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()


def cmd_generate(args):
    """Generate a new AI-powered post."""
    from generate_post import generate_post_with_hooks, load_knowledge_base
    from draft_storage import create_draft

    print(f"Generating post about: {args.topic}")
    print("Loading knowledge base...")

    kb = load_knowledge_base()
    print("Generating content with AI...")

    body, hooks = generate_post_with_hooks(args.topic, kb)

    draft = create_draft(
        content=body,
        hooks=hooks,
        topic=args.topic
    )

    print(f"\n{'='*50}")
    print(f"Draft created! ID: {draft['id']}")
    print(f"{'='*50}\n")

    print("HOOK OPTIONS:")
    for i, hook in enumerate(hooks):
        print(f"  {chr(65+i)}: {hook}")

    print(f"\nPOST BODY:")
    print(body[:500])
    if len(body) > 500:
        print("...")

    print(f"\n{'='*50}")
    print(f"Next steps:")
    print(f"  - View full draft: python workflow.py view {draft['id']}")
    print(f"  - Edit in web UI:  python workflow.py ui")
    print(f"  - Post to LI:      python workflow.py post {draft['id']}")


def cmd_list(args):
    """List all drafts."""
    from draft_storage import list_drafts

    status_filter = args.status if hasattr(args, 'status') else None
    drafts = list_drafts(status=status_filter)

    if not drafts:
        print("No drafts found.")
        return

    print(f"\n{'ID':<10} {'Status':<12} {'Topic':<30} {'Created':<20}")
    print("-" * 75)

    for draft in drafts:
        topic = (draft.get('topic') or 'No topic')[:28]
        created = draft['created_at'][:16]
        print(f"{draft['id']:<10} {draft['status']:<12} {topic:<30} {created:<20}")

    print(f"\nTotal: {len(drafts)} draft(s)")


def cmd_view(args):
    """View a specific draft."""
    from draft_storage import get_draft, get_final_post

    draft = get_draft(args.id)
    if not draft:
        print(f"Draft '{args.id}' not found.")
        return

    print(f"\n{'='*50}")
    print(f"Draft ID: {draft['id']}")
    print(f"Status: {draft['status']}")
    print(f"Topic: {draft.get('topic', 'Not specified')}")
    print(f"Created: {draft['created_at']}")
    print(f"{'='*50}\n")

    if draft['hooks']:
        print("HOOK OPTIONS:")
        for i, hook in enumerate(draft['hooks']):
            selected = " (SELECTED)" if draft.get('selected_hook') == i else ""
            print(f"  {chr(65+i)}: {hook}{selected}")
        print()

    print("CONTENT:")
    print("-" * 50)
    print(draft['content'])
    print("-" * 50)

    print("\nFINAL POST (with selected hook):")
    print("=" * 50)
    print(get_final_post(args.id))
    print("=" * 50)


def cmd_select_hook(args):
    """Select a hook for a draft."""
    from draft_storage import update_draft, get_draft

    draft = get_draft(args.id)
    if not draft:
        print(f"Draft '{args.id}' not found.")
        return

    hook_idx = ord(args.hook.upper()) - ord('A')
    if hook_idx < 0 or hook_idx >= len(draft.get('hooks', [])):
        print(f"Invalid hook. Use A-{chr(ord('A') + len(draft['hooks']) - 1)}")
        return

    update_draft(args.id, selected_hook=hook_idx)
    print(f"Selected hook {args.hook.upper()} for draft {args.id}")


def cmd_post(args):
    """Post to LinkedIn."""
    from draft_storage import get_draft, get_final_post, update_draft
    from post_to_linkedin import post_to_linkedin, check_token_validity

    # Check token first
    status = check_token_validity()
    if not status['valid']:
        print(f"LinkedIn token issue: {status['error']}")
        print("Run: python execution/linkedin_oauth.py")
        return

    draft = get_draft(args.id)
    if not draft:
        print(f"Draft '{args.id}' not found.")
        return

    content = get_final_post(args.id)

    print(f"Posting to LinkedIn as {status['name']}...")
    print(f"Content preview: {content[:100]}...")

    if not args.yes:
        confirm = input("\nProceed? [y/N]: ")
        if confirm.lower() != 'y':
            print("Cancelled.")
            return

    result = post_to_linkedin(content)

    if result['success']:
        update_draft(args.id, status='posted')
        print(f"\nSuccess! Post ID: {result['post_id']}")
    else:
        print(f"\nFailed: {result.get('error', 'Unknown error')}")


def cmd_hypefury(args):
    """Send to Hypefury."""
    from draft_storage import get_draft, get_final_post, update_draft
    from push_to_hypefury import create_draft as hypefury_draft, format_post_with_hooks

    draft = get_draft(args.id)
    if not draft:
        print(f"Draft '{args.id}' not found.")
        return

    # Include hook options if none selected
    if draft.get('selected_hook') is None and draft.get('hooks'):
        content = format_post_with_hooks(draft['hooks'], draft['content'])
    else:
        content = get_final_post(args.id)

    print("Sending to Hypefury...")
    print(f"Content preview: {content[:100]}...")

    try:
        result = hypefury_draft(content)
        update_draft(args.id, status='scheduled')
        print(f"\nSuccess! Draft created in Hypefury.")
        print(f"Response: {result}")
    except Exception as e:
        print(f"\nFailed: {str(e)}")


def cmd_ui(args):
    """Start the web UI."""
    from web_ui import main
    main()


def cmd_delete(args):
    """Delete a draft."""
    from draft_storage import delete_draft, get_draft

    draft = get_draft(args.id)
    if not draft:
        print(f"Draft '{args.id}' not found.")
        return

    if not args.yes:
        confirm = input(f"Delete draft {args.id}? [y/N]: ")
        if confirm.lower() != 'y':
            print("Cancelled.")
            return

    delete_draft(args.id)
    print(f"Deleted draft {args.id}")


def main():
    parser = argparse.ArgumentParser(
        description="AI-powered LinkedIn post workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s generate "AI coaching and why human touch still matters"
    %(prog)s list
    %(prog)s view abc123
    %(prog)s select abc123 B
    %(prog)s post abc123
    %(prog)s ui
        """
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    # Generate
    gen_parser = subparsers.add_parser('generate', help='Generate a new AI post')
    gen_parser.add_argument('topic', help='Topic for the post')
    gen_parser.set_defaults(func=cmd_generate)

    # List
    list_parser = subparsers.add_parser('list', help='List all drafts')
    list_parser.add_argument('--status', choices=['draft', 'scheduled', 'posted'],
                            help='Filter by status')
    list_parser.set_defaults(func=cmd_list)

    # View
    view_parser = subparsers.add_parser('view', help='View a draft')
    view_parser.add_argument('id', help='Draft ID')
    view_parser.set_defaults(func=cmd_view)

    # Select hook
    select_parser = subparsers.add_parser('select', help='Select a hook')
    select_parser.add_argument('id', help='Draft ID')
    select_parser.add_argument('hook', help='Hook letter (A-E)')
    select_parser.set_defaults(func=cmd_select_hook)

    # Post to LinkedIn
    post_parser = subparsers.add_parser('post', help='Post to LinkedIn')
    post_parser.add_argument('id', help='Draft ID')
    post_parser.add_argument('-y', '--yes', action='store_true',
                            help='Skip confirmation')
    post_parser.set_defaults(func=cmd_post)

    # Send to Hypefury
    hf_parser = subparsers.add_parser('hypefury', help='Send to Hypefury')
    hf_parser.add_argument('id', help='Draft ID')
    hf_parser.set_defaults(func=cmd_hypefury)

    # Delete
    del_parser = subparsers.add_parser('delete', help='Delete a draft')
    del_parser.add_argument('id', help='Draft ID')
    del_parser.add_argument('-y', '--yes', action='store_true',
                            help='Skip confirmation')
    del_parser.set_defaults(func=cmd_delete)

    # Web UI
    ui_parser = subparsers.add_parser('ui', help='Start web UI')
    ui_parser.set_defaults(func=cmd_ui)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
