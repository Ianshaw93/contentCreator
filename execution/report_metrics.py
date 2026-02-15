#!/usr/bin/env python3
"""
Report Metrics - Send content creation metrics to speed_to_lead reporting system.

Reads from .drafts.json, .hooks_bank.json, .ideas_bank.json to calculate
activity since last report and POSTs to speed_to_lead.

Usage:
    # Daily sync (reports all activity for today)
    python report_metrics.py

    # Manual reporting with specific counts
    python report_metrics.py --drafts 3 --hooks 10 --ideas 5
"""

import argparse
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

# Files
DRAFTS_FILE = Path(__file__).parent.parent / ".drafts.json"
HOOKS_BANK_FILE = Path(__file__).parent.parent / ".hooks_bank.json"
IDEAS_BANK_FILE = Path(__file__).parent.parent / ".ideas_bank.json"
LAST_REPORT_FILE = Path(__file__).parent.parent / ".tmp" / ".last_metrics_report.json"

# API endpoint
SPEED_TO_LEAD_API_URL = os.getenv(
    "SPEED_TO_LEAD_API_URL",
    "https://speedtolead-production.up.railway.app"
)


def _load_json(file_path: Path) -> dict:
    """Load JSON from file, return empty dict if not exists."""
    if not file_path.exists():
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(file_path: Path, data: dict) -> None:
    """Save JSON to file, creating parent dirs if needed."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def _count_items_for_date(items: list, date_str: str, date_field: str = "created_at") -> int:
    """Count items created/updated on a specific date."""
    count = 0
    for item in items:
        item_date = item.get(date_field, "")
        if item_date and item_date.startswith(date_str):
            count += 1
    return count


def calculate_daily_metrics(target_date: Optional[date] = None) -> Dict[str, int]:
    """
    Calculate content metrics for a specific date.

    Args:
        target_date: Date to calculate metrics for (defaults to today).

    Returns:
        Dict with metric counts.
    """
    target_date = target_date or date.today()
    date_str = target_date.isoformat()

    # Load data files
    drafts_data = _load_json(DRAFTS_FILE)
    hooks_data = _load_json(HOOKS_BANK_FILE)
    ideas_data = _load_json(IDEAS_BANK_FILE)

    drafts = drafts_data.get("drafts", [])
    hooks = hooks_data.get("hooks", [])
    ideas = ideas_data.get("ideas", [])

    # Count items created today
    drafts_created = _count_items_for_date(drafts, date_str, "created_at")
    hooks_generated = _count_items_for_date(hooks, date_str, "created_at")
    ideas_added = _count_items_for_date(ideas, date_str, "created_at")

    # Count drafts scheduled and posted today
    drafts_scheduled = 0
    drafts_posted = 0

    for draft in drafts:
        scheduled_time = draft.get("scheduled_time", "")
        posted_at = draft.get("posted_at", "")

        if scheduled_time and scheduled_time.startswith(date_str):
            drafts_scheduled += 1

        if posted_at and posted_at.startswith(date_str):
            drafts_posted += 1

    return {
        "drafts_created": drafts_created,
        "drafts_scheduled": drafts_scheduled,
        "drafts_posted": drafts_posted,
        "hooks_generated": hooks_generated,
        "ideas_added": ideas_added,
    }


def report_metrics(
    drafts_created: int = 0,
    drafts_scheduled: int = 0,
    drafts_posted: int = 0,
    hooks_generated: int = 0,
    ideas_added: int = 0,
    target_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Report metrics to speed_to_lead.

    Args:
        drafts_created: Number of content drafts created.
        drafts_scheduled: Number of drafts scheduled.
        drafts_posted: Number of drafts posted.
        hooks_generated: Number of hooks generated.
        ideas_added: Number of ideas added.
        target_date: Date for the metrics (defaults to today).

    Returns:
        API response dict.
    """
    payload = {
        "date": (target_date or date.today()).isoformat(),
        "drafts_created": drafts_created,
        "drafts_scheduled": drafts_scheduled,
        "drafts_posted": drafts_posted,
        "hooks_generated": hooks_generated,
        "ideas_added": ideas_added,
    }

    url = f"{SPEED_TO_LEAD_API_URL}/api/metrics/content"

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        print(f"Metrics reported successfully: {result}")

        # Save last report timestamp
        _save_json(LAST_REPORT_FILE, {
            "last_report": datetime.now().isoformat(),
            "date_reported": (target_date or date.today()).isoformat(),
            "metrics": payload,
        })

        return result
    except requests.RequestException as e:
        print(f"Failed to report metrics: {e}")
        return {"status": "error", "error": str(e)}


def report_daily_metrics(target_date: Optional[date] = None) -> Dict[str, Any]:
    """
    Calculate and report daily metrics.

    Args:
        target_date: Date to report (defaults to today).

    Returns:
        API response dict.
    """
    metrics = calculate_daily_metrics(target_date)
    print(f"Calculated metrics for {target_date or date.today()}: {metrics}")

    return report_metrics(
        drafts_created=metrics["drafts_created"],
        drafts_scheduled=metrics["drafts_scheduled"],
        drafts_posted=metrics["drafts_posted"],
        hooks_generated=metrics["hooks_generated"],
        ideas_added=metrics["ideas_added"],
        target_date=target_date,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Report content creation metrics to speed_to_lead"
    )
    parser.add_argument(
        "--auto", action="store_true",
        help="Automatically calculate metrics from local files"
    )
    parser.add_argument(
        "--drafts", type=int, default=0,
        help="Number of drafts created"
    )
    parser.add_argument(
        "--scheduled", type=int, default=0,
        help="Number of drafts scheduled"
    )
    parser.add_argument(
        "--posted", type=int, default=0,
        help="Number of drafts posted"
    )
    parser.add_argument(
        "--hooks", type=int, default=0,
        help="Number of hooks generated"
    )
    parser.add_argument(
        "--ideas", type=int, default=0,
        help="Number of ideas added"
    )

    args = parser.parse_args()

    if args.auto or (not any([args.drafts, args.scheduled, args.posted, args.hooks, args.ideas])):
        # Auto-calculate from files
        result = report_daily_metrics()
    else:
        # Use provided values
        result = report_metrics(
            drafts_created=args.drafts,
            drafts_scheduled=args.scheduled,
            drafts_posted=args.posted,
            hooks_generated=args.hooks,
            ideas_added=args.ideas,
        )

    if result.get("status") == "ok":
        print("Metrics reported successfully")
        sys.exit(0)
    else:
        print(f"Failed to report metrics: {result}")
        sys.exit(1)


if __name__ == "__main__":
    main()
