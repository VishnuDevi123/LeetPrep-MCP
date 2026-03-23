"""
mcp server that exposes leetcode prep tools over stdio.

this module wires together two layers:
1) local sqlite storage (problem list + progress history)
2) live reads from alfa-leetcode-api for problem/user data
"""

import json

from mcp import types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server

try:
    from . import db, leetcode_client
except ImportError:
    import db  # type: ignore
    import leetcode_client  # type: ignore


server = Server("leetprep-mcp-server")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """return the complete tool catalog and each tool's input schema."""
    return [
        types.Tool(
            name="add_problem",
            description="Add a LeetCode problem to the local database for tracking.",
            inputSchema={
                "type": "object",
                "properties": {
                    "leetcode_id": {"type": "integer", "description": "LeetCode problem id."},
                    "title": {"type": "string", "description": "LeetCode problem title."},
                    "slug": {"type": "string", "description": "LeetCode problem URL slug."},
                    "difficulty": {"type": "string", "description": "Difficulty: easy/medium/hard."},
                    "patterns": {
                        "description": "Pattern list as JSON array string or array of strings.",
                        "oneOf": [
                            {"type": "string"},
                            {"type": "array", "items": {"type": "string"}},
                        ],
                    },
                    "companies": {
                        "description": "Company list as JSON array string or array of strings.",
                        "oneOf": [
                            {"type": "string"},
                            {"type": "array", "items": {"type": "string"}},
                        ],
                    },
                    "created_at": {"type": "string", "description": "Created timestamp (ISO-8601)."},
                },
                "required": [
                    "leetcode_id",
                    "title",
                    "slug",
                    "difficulty",
                    "patterns",
                    "companies",
                    "created_at",
                ],
            },
        ),
        types.Tool(
            name="fetch_problem",
            description="Fetch LeetCode problem metadata by title slug from Alpha LeetCode API.",
            inputSchema={
                "type": "object",
                "properties": {
                    "slug": {"type": "string", "description": "Problem URL slug (e.g., two-sum)."}
                },
                "required": ["slug"],
            },
        ),
        types.Tool(
            name="track_progress",
            description="Track progress on a LeetCode problem with status, time taken, and notes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "leetcode_id": {"type": "integer", "description": "LeetCode problem id."},
                    "status": {
                        "type": "string",
                        "description": "One of: solved, attempted, not_started, reviewing, skipped.",
                    },
                    "time_taken_mins": {
                        "type": "integer",
                        "description": "Time taken in minutes.",
                        "default": 0,
                    },
                    "notes": {"type": "string", "description": "Optional notes.", "default": ""},
                },
                "required": ["leetcode_id", "status"],
            },
        ),
        types.Tool(
            name="fetch_user_state",
            description="Fetch user state from Alpha LeetCode API (aggregated profile/solved/progress with fallback).",
            inputSchema={
                "type": "object",
                "properties": {
                    "username": {"type": "string", "description": "LeetCode username."}
                },
                "required": ["username"],
            },
        ),
        types.Tool(
            name="fetch_submissions",
            description="Fetch recent submissions from Alpha LeetCode API.",
            inputSchema={
                "type": "object",
                "properties": {
                    "username": {"type": "string", "description": "LeetCode username."},
                    "limit": {"type": "integer", "description": "Maximum submissions to fetch.", "default": 20},
                },
                "required": ["username"],
            },
        ),
        types.Tool(
            name="fetch_profile",
            description="Fetch user profile information from Alpha LeetCode API.",
            inputSchema={
                "type": "object",
                "properties": {
                    "username": {"type": "string", "description": "LeetCode username."}
                },
                "required": ["username"],
            },
        ),
        types.Tool(
            name="check_api_health",
            description="Run health checks against Alpha LeetCode API endpoints used by this server.",
            inputSchema={
                "type": "object",
                "properties": {
                    "slug": {"type": "string", "description": "Problem slug to probe.", "default": "two-sum"},
                    "username": {
                        "type": "string",
                        "description": "Username for profile probe.",
                        "default": "leetcode",
                    },
                },
                "required": [],
            },
        ),
        types.Tool(
            name="get_stats_overview",
            description="Get local progress analytics (solved/attempted/avg time/activity).",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="get_problem_history",
            description="Get progress history events, optionally filtered by problem id.",
            inputSchema={
                "type": "object",
                "properties": {
                    "leetcode_id": {"type": "integer", "description": "Optional problem id filter."},
                    "limit": {"type": "integer", "description": "Result limit (1-200).", "default": 20},
                },
                "required": [],
            },
        ),
    ]


def _array_to_json_string(value: object, field_name: str) -> str:
    """
    normalize list-like inputs so db functions always receive json string fields.

    accepted input:
    - python list[str]
    - already-serialized json array string
    """
    if isinstance(value, list):
        # reject mixed-type lists early to keep db records predictable.
        if not all(isinstance(item, str) for item in value):
            raise ValueError(f"{field_name} must contain only strings.")
        return json.dumps(value)
    if isinstance(value, str):
        return value
    raise ValueError(f"{field_name} must be a JSON array string or array of strings.")


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """
    dispatch a tool call by name, run the target function, and return json text.

    mcp expects text content responses, so all tool outputs are serialized here.
    """
    try:
        # simple router: map tool names to db or api functions.
        if name == "add_problem":
            result = db.add_problem(
                arguments["leetcode_id"],
                arguments["title"],
                arguments["slug"],
                arguments["difficulty"],
                _array_to_json_string(arguments["patterns"], "patterns"),
                _array_to_json_string(arguments["companies"], "companies"),
                arguments["created_at"],
            )
        elif name == "fetch_problem":
            result = leetcode_client.fetch_problem(arguments["slug"])
        elif name == "track_progress":
            result = db.track_progress(
                arguments["leetcode_id"],
                arguments["status"],
                arguments.get("time_taken_mins", 0),
                arguments.get("notes", ""),
            )
        elif name == "fetch_user_state":
            result = leetcode_client.fetch_user_state(arguments["username"])
        elif name == "fetch_submissions":
            result = leetcode_client.fetch_submissions(
                arguments["username"], arguments.get("limit", 20)
            )
        elif name == "fetch_profile":
            result = leetcode_client.fetch_profile(arguments["username"])
        elif name == "check_api_health":
            result = leetcode_client.check_api_health(
                arguments.get("slug", "two-sum"),
                arguments.get("username", "leetcode"),
            )
        elif name == "get_stats_overview":
            result = db.get_stats_overview()
        elif name == "get_problem_history":
            result = db.get_problem_history(
                arguments.get("leetcode_id"), arguments.get("limit", 20)
            )
        else:
            raise ValueError(f"Unknown tool: {name}")
    # convert common bad-input failures into structured tool errors.
    except (KeyError, TypeError, ValueError) as exc:
        result = {"error": True, "message": str(exc)}
    # safety net so unexpected failures still return valid json.
    except Exception as exc:
        result = {"error": True, "message": str(exc)}

    return [types.TextContent(type="text", text=json.dumps(result))]


async def run() -> None:
    """initialize local state and start the stdio mcp event loop."""
    db.init_db()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="leetprep-mcp-server",
                server_version="0.2.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(run())
