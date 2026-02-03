"""
Main entry point: generate hooks and push to Hypefury as draft.
"""
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

from generate_hooks import generate_hooks
from push_to_hypefury import create_draft, format_post_with_hooks


def main():
    parser = argparse.ArgumentParser(description="Create LinkedIn draft with hook options")
    parser.add_argument("body", nargs="?", help="Post body text")
    parser.add_argument("--file", "-f", help="Read post body from file")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Print output without pushing to Hypefury")

    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Get post body
    if args.file:
        body = Path(args.file).read_text(encoding="utf-8")
    elif args.body:
        body = args.body
    else:
        print("Error: Provide post body as argument or use --file")
        sys.exit(1)

    body = body.strip()
    print(f"Post body ({len(body)} chars):\n{body[:100]}...\n")

    # Generate hooks
    print("Generating hooks...")
    hooks = generate_hooks(body)
    print(f"Generated {len(hooks)} hooks\n")

    # Format post
    formatted = format_post_with_hooks(hooks, body)

    if args.dry_run:
        print("=== DRY RUN - Would push this to Hypefury ===\n")
        print(formatted)
        return

    # Push to Hypefury
    print("Pushing to Hypefury...")
    result = create_draft(formatted)
    print(f"Draft created successfully!")
    print(f"Response: {result}")


if __name__ == "__main__":
    main()
