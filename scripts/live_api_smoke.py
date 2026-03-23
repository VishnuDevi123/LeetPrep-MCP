#!/usr/bin/env python3
"""
Live smoke test for Alpha LeetCode API integration.

Usage:
  venv/bin/python scripts/live_api_smoke.py --username leetcode --slug two-sum
"""

from __future__ import annotations

import argparse
import json
import os
import sys


def main() -> int:
    # parse command-line inputs so smoke checks can target custom user/slug pairs.
    parser = argparse.ArgumentParser(description="Run live API smoke checks.")
    parser.add_argument("--username", default="leetcode", help="LeetCode username for profile checks")
    parser.add_argument("--slug", default="two-sum", help="Problem slug for select checks")
    args = parser.parse_args()

    # import from local src directory so the script works without package installation.
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
    from leetprep_mcp import leetcode_client  # noqa: WPS433

    # run both high-level health checks and one concrete problem fetch sample.
    health = leetcode_client.check_api_health(slug=args.slug, username=args.username)
    problem = leetcode_client.fetch_problem(args.slug)

    # keep output compact and easy to scan in terminals/ci logs.
    output = {
        "health": health,
        "problem_summary": {
            "error": problem.get("error"),
            "leetcode_id": problem.get("leetcode_id"),
            "title": problem.get("title"),
            "slug": problem.get("slug"),
            "difficulty": problem.get("difficulty"),
        },
    }
    print(json.dumps(output, indent=2))
    # non-zero exit makes this useful in automation/ci smoke checks.
    return 0 if health.get("all_checks_passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
