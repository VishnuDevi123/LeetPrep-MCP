"""
http client helpers for alfa-leetcode-api.

this module centralizes:
- resilient get requests (timeout + retries + backoff)
- response normalization
- endpoint-specific adapters used by the mcp tool layer
"""

import requests
import time
from typing import Any

ALFA_API_BASE = "https://alfa-leetcode-api.onrender.com"
DEFAULT_TIMEOUT_SECS = 20
DEFAULT_RETRIES = 2


def _request_json(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    perform a get request and always return a structured result object.

    response shape:
    - success: {"error": False, "status_code": int, "data": {...}}
    - failure: {"error": True, "status_code": int|None, "message": str, ...}
    """
    url = f"{ALFA_API_BASE}{path}"
    # exponential backoff seed used for transient transport/rate-limit errors.
    delay = 0.6
    for attempt in range(DEFAULT_RETRIES + 1):
        try:
            response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT_SECS)
        except requests.RequestException as exc:
            # network-level failure: retry only while attempts remain.
            if attempt < DEFAULT_RETRIES:
                time.sleep(delay)
                delay *= 2
                continue
            return {
                "error": True,
                "status_code": None,
                "message": f"Request failed for {path}: {exc}",
            }

        # retry common transient server/rate-limit statuses.
        if response.status_code in {429, 500, 502, 503, 504} and attempt < DEFAULT_RETRIES:
            time.sleep(delay)
            delay *= 2
            continue

        # non-200 response is treated as an error with a short body preview for debugging.
        if response.status_code != 200:
            body_preview = response.text[:300] if response.text else ""
            return {
                "error": True,
                "status_code": response.status_code,
                "message": f"API returned status {response.status_code} for {path}",
                "body_preview": body_preview,
            }

        try:
            data = response.json()
        # some upstream failures return html/text even with 200; catch that explicitly.
        except ValueError:
            return {
                "error": True,
                "status_code": response.status_code,
                "message": f"Non-JSON response for {path}",
                "body_preview": response.text[:300],
            }
        return {"error": False, "status_code": response.status_code, "data": data}

    return {"error": True, "status_code": None, "message": "Unexpected request failure"}


def _unwrap(result: dict[str, Any]) -> dict[str, Any]:
    """return payload data when successful, otherwise pass through the error object."""
    if result.get("error"):
        return result
    return result["data"]


def fetch_problem(slug: str) -> dict:
    """
    fetch problem details and map api fields into local project schema.

    Args:
        slug: problem url slug (example: "two-sum")

    Returns:
        dict ready for db insertion or an error object from `_request_json`
    """
    api_result = _request_json("/select", params={"titleSlug": slug})
    if api_result.get("error"):
        return api_result

    data = api_result["data"]

    # extract topic tag names into a flat list for easier storage/search.
    patterns = [tag.get("name") for tag in data.get("topicTags", []) if tag.get("name")]
    return {
        # keep int when possible because local db column is integer-centric.
        "leetcode_id": int(data.get("questionId"))
        if str(data.get("questionId", "")).isdigit()
        else data.get("questionId"),
        "title": data.get("questionTitle"),
        "slug": data.get("titleSlug"),
        "difficulty": data.get("difficulty"),
        "patterns": patterns,
        # api payload may not consistently include company metadata.
        "companies": [],
    }


def fetch_user_stats(username: str) -> dict:
    """
    fetch user stats from alfa-leetcode-api.

    Args:
        username: leetcode username
    Returns:
        user stats dict (or aggregated fallback)
    """
    # try legacy endpoint first, then fallback to aggregated state.
    stats_result = _request_json(f"/{username}/stats")
    if not stats_result.get("error"):
        return stats_result["data"]
    return fetch_user_state(username)


def fetch_user_state(username: str) -> dict:
    """
    collect profile + solved + progress in a single response envelope.

    this method does partial-failure tolerant aggregation: each section can carry its
    own error object while still returning whatever succeeded.
    """
    profile = _request_json(f"/{username}/profile")
    solved = _request_json(f"/{username}/solved")
    progress = _request_json(f"/{username}/progress")

    parts = {
        "profile": _unwrap(profile),
        "solved": _unwrap(solved),
        "progress": _unwrap(progress),
    }
    return {
        "username": username,
        "ok": not any(v.get("error") for v in [profile, solved, progress]),
        "data": parts,
    }


def fetch_submissions(username: str, limit: int = 20) -> dict:
    """
    fetch recent submissions for a user from alfa-leetcode-api.

    Args:
        username: leetcode username
        limit: max submissions to fetch
    Returns:
        submissions payload or detailed fallback error info
    """
    # clamp to protect upstream and avoid accidental large responses.
    safe_limit = max(1, min(int(limit), 100))
    # preferred path from current docs.
    primary = _request_json(f"/{username}/submission", params={"limit": safe_limit})
    if not primary.get("error"):
        return primary["data"]
    # fallback to older plural path in case provider routing changed.
    fallback = _request_json(f"/{username}/submissions", params={"limit": safe_limit})
    if not fallback.get("error"):
        return fallback["data"]
    return {
        "error": True,
        "message": "Both submission endpoints failed",
        "primary_error": primary,
        "fallback_error": fallback,
    }


def fetch_profile(username: str) -> dict:
    """
    fetch user profile information from alfa-leetcode-api.

    Args:
        username: leetcode username

    Returns:
        profile payload or structured error object
    """
    return _unwrap(_request_json(f"/{username}/profile"))


def check_api_health(slug: str = "two-sum", username: str = "leetcode") -> dict:
    """
    run a lightweight health probe across key api endpoints used by this project.

    includes per-check latency so failures are easier to troubleshoot.
    """
    checks: list[tuple[str, str, dict[str, Any] | None]] = [
        ("root", "/", None),
        ("problem_lookup", "/select", {"titleSlug": slug}),
        ("profile_lookup", f"/{username}/profile", None),
    ]

    results = []
    for name, path, params in checks:
        # measure end-to-end request time for each check.
        start = time.perf_counter()
        result = _request_json(path, params=params)
        latency_ms = round((time.perf_counter() - start) * 1000, 1)
        results.append(
            {
                "check": name,
                "path": path,
                "ok": not result.get("error"),
                "status_code": result.get("status_code"),
                "latency_ms": latency_ms,
                "details": result if result.get("error") else "ok",
            }
        )

    return {
        "base_url": ALFA_API_BASE,
        "all_checks_passed": all(item["ok"] for item in results),
        "checks": results,
    }
