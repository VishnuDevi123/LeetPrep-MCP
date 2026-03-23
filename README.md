# leetprep-mcp

`leetprep-mcp` is a lightweight MCP (model context protocol) server for leetcode preparation.
it gives an MCP-compatible client one place to save problems, track practice progress, and fetch live leetcode metadata.

## at a glance

- tracks problems and progress locally in sqlite
- fetches live data from `alfa-leetcode-api`
- exposes MCP tools over stdio for AI/tooling integration

## why this project

personnaly I wanted to explore more of the mpc world and I thought why not start of with something related to leetcode. leetcode prep usually gets scattered across notes, browser tabs, and manual logs. This project creates one programmable interface so your assistant/scripts can:

- store problems you care about
- log solve attempts consistently
- query recent history and progress analytics quickly

## how it is built

### core stack

- python
- MCP python SDK (`mcp.server.*`)
- sqlite (`sqlite3`)
- requests (`requests`)
- external provider: `https://alfa-leetcode-api.onrender.com`

### project architecture

- `src/leetprep_mcp/server.py`: MCP server setup, tool schemas, tool router
- `src/leetprep_mcp/db.py`: local database schema, writes, analytics queries
- `src/leetprep_mcp/leetcode_client.py`: resilient API client (timeout/retry/backoff)
- 
## tools implemented

| tool | purpose |
|---|---|
| `add_problem` | save a leetcode problem in local db |
| `fetch_problem` | fetch problem metadata by slug |
| `track_progress` | append progress event (status, time, notes) |
| `fetch_user_state` | aggregated user payload (profile/solved/progress) |
| `fetch_submissions` | recent submissions for a user |
| `fetch_profile` | fetch profile details |
| `check_api_health` | probe key API endpoints + latency |
| `get_stats_overview` | local stats summary |
| `get_problem_history` | recent progress events, optional problem filter |

## local database model

db file: `data/app_database.db`

- `problems`: metadata for tracked problems
- `progress`: append-only timeline of attempts/solves/reviews

valid `status` values:

- `solved`
- `attempted`
- `not_started`
- `reviewing`
- `skipped`

## setup

### 1. create and activate env

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. install dependencies

```bash
pip install -r requirements.txt
```

if needed in your environment:

```bash
pip install requests mcp
```

### 3. run MCP server

```bash
from /src
python -m leetprep_mcp.server
```

## simple walkthrough

1. call `fetch_problem` with a slug like `two-sum`
2. call `add_problem` with the returned problem metadata
3. after practice, call `track_progress` with status/time/notes
4. call `get_stats_overview` to see totals and activity
5. call `get_problem_history` to inspect recent progress events

## reliability notes that you can refer

- API calls use timeout + retry + exponential backoff for transient errors
- user-state endpoint aggregation supports partial failures gracefully
- submissions path uses fallback (`/submission` then `/submissions`)

## future improvements

1. need to work on proper unit/integration tests for each MCP tool path
2. add richer analytics maybe

## notes

- `test_api.py` and `test_db.py` are quick manual scripts, not full test suites.
- database initialization runs automatically when server starts.
