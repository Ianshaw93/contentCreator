#!/usr/bin/env python3
"""
Main workflow script for AI-powered LinkedIn post creation.

WORKFLOW:
    1. python workflow.py hooks "topic"       # Generate hook options
    2. python workflow.py draft <id> <hook>   # Select hook & generate body
    3. python workflow.py post <id>           # Post to LinkedIn

OTHER COMMANDS:
    python workflow.py list                   # List all drafts
    python workflow.py view <id>              # View a specific draft
    python workflow.py delete <id>            # Delete a draft
    python workflow.py ui                     # Start the web UI
"""
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()


def cmd_hooks(args):
    """Step 1: Generate hook options for a topic."""
    from generate_hooks import generate_hooks
    from draft_storage import create_draft

    print(f"Generating hooks for: {args.topic}")
    if args.context:
        print(f"Context: {args.context}")

    hooks = generate_hooks(args.topic, args.context or "")

    # Create draft with hooks only (no body yet)
    draft = create_draft(
        content="",  # Body generated after hook selection
        hooks=hooks,
        topic=args.topic
    )

    print(f"\n{'='*50}")
    print(f"Draft created! ID: {draft['id']}")
    print(f"{'='*50}\n")

    print("HOOK OPTIONS:")
    for i, hook in enumerate(hooks):
        print(f"  {chr(65+i)}: {hook}\n")

    print(f"{'='*50}")
    print(f"Next step - select a hook and generate the post body:")
    print(f"  python workflow.py draft {draft['id']} A")
    print(f"  python workflow.py draft {draft['id']} B")
    print(f"  etc.")


def cmd_draft(args):
    """Step 2: Select a hook and generate the post body."""
    from generate_post import generate_post_body, load_knowledge_base
    from draft_storage import get_draft, update_draft

    draft = get_draft(args.id)
    if not draft:
        print(f"Draft '{args.id}' not found.")
        return

    if not draft.get('hooks'):
        print(f"Draft has no hooks. Run 'workflow.py hooks' first.")
        return

    hook_idx = ord(args.hook.upper()) - ord('A')
    if hook_idx < 0 or hook_idx >= len(draft['hooks']):
        print(f"Invalid hook. Use A-{chr(ord('A') + len(draft['hooks']) - 1)}")
        return

    selected_hook = draft['hooks'][hook_idx]
    topic = draft.get('topic', '')

    print(f"Selected hook {args.hook.upper()}: {selected_hook}")
    print(f"\nGenerating post body...")

    kb = load_knowledge_base()
    body = generate_post_body(topic, selected_hook, kb)

    # Update draft with body and selected hook
    update_draft(args.id, content=body, selected_hook=hook_idx)

    print(f"\n{'='*50}")
    print(f"FULL POST:")
    print(f"{'='*50}")
    print(f"{selected_hook}\n")
    print(body)
    print(f"{'='*50}")
    print(f"\nNext steps:")
    print(f"  - View:    python workflow.py view {args.id}")
    print(f"  - Post:    python workflow.py post {args.id}")
    print(f"  - Edit:    python workflow.py ui")


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
Workflow:
    1. %(prog)s hooks "AI coaching"           # Generate hooks
    2. %(prog)s draft abc123 B                # Select hook B, generate body
    3. %(prog)s post abc123                   # Post to LinkedIn

Other commands:
    %(prog)s list
    %(prog)s view abc123
    %(prog)s delete abc123
    %(prog)s ui
        """
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    # Step 1: Generate hooks
    hooks_parser = subparsers.add_parser('hooks', help='Step 1: Generate hook options for a topic')
    hooks_parser.add_argument('topic', help='Topic/idea for the post')
    hooks_parser.add_argument('-c', '--context', help='Optional additional context')
    hooks_parser.set_defaults(func=cmd_hooks)

    # Step 2: Select hook and generate body
    draft_parser = subparsers.add_parser('draft', help='Step 2: Select hook and generate post body')
    draft_parser.add_argument('id', help='Draft ID')
    draft_parser.add_argument('hook', help='Hook letter (A-E)')
    draft_parser.set_defaults(func=cmd_draft)

    # List
    list_parser = subparsers.add_parser('list', help='List all drafts')
    list_parser.add_argument('--status', choices=['draft', 'scheduled', 'posted'],
                            help='Filter by status')
    list_parser.set_defaults(func=cmd_list)

    # View
    view_parser = subparsers.add_parser('view', help='View a draft')
    view_parser.add_argument('id', help='Draft ID')
    view_parser.set_defaults(func=cmd_view)

    # Post to LinkedIn
    post_parser = subparsers.add_parser('post', help='Step 3: Post to LinkedIn')
    post_parser.add_argument('id', help='Draft ID')
    post_parser.add_argument('-y', '--yes', action='store_true',
                            help='Skip confirmation')
    post_parser.set_defaults(func=cmd_post)

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
