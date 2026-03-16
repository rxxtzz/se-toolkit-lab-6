# Task 3: The System Agent

## Overview
Add a `query_api` tool to enable the agent to query the deployed backend API for real-time data and system facts.

## Tool Schema: query_api

### Definition
```json
{
  "type": "function",
  "function": {
    "name": "query_api",
    "description": "Call the backend API to get real-time data or check system behavior. Use this for questions about database contents, API responses, status codes, or analytics.",
    "parameters": {
      "type": "object",
      "properties": {
        "method": {
          "type": "string",
          "description": "HTTP method (GET, POST, etc.)",
          "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"]
        },
        "path": {
          "type": "string",
          "description": "API endpoint path (e.g., '/items/', '/analytics/completion-rate')"
        },
        "body": {
          "type": "string",
          "description": "Optional JSON request body for POST/PUT requests"
        }
      },
      "required": ["method", "path"]
    }
  }
}
```

### Implementation
- Read `LMS_API_KEY` from environment for authentication
- Read `AGENT_API_BASE_URL` from environment (default: `http://localhost:42002`)
- Return JSON string with `status_code` and `body`
- Handle errors gracefully (connection errors, timeouts, HTTP errors)

## Authentication
- Use `Authorization: Bearer <LMS_API_KEY>` header
- `LMS_API_KEY` comes from `.env.docker.secret` (different from `LLM_API_KEY`)
- Must read from environment variable, not hardcoded

## System Prompt Update
Update the system prompt to guide tool selection:

1. **Use `list_files`** when the user asks about what files exist in a directory
2. **Use `read_file`** when the user asks about:
   - Documentation in the wiki
   - Source code files (backend, frontend, Docker configs)
   - Configuration files (docker-compose.yml, Dockerfile, etc.)
3. **Use `query_api`** when the user asks about:
   - Current database contents (item count, scores)
   - API behavior (status codes, error messages)
   - Analytics data (completion rates, top learners)
   - Real-time system state

## Environment Variables
The agent must read from environment variables (not hardcoded):
- `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL` - LLM configuration
- `LMS_API_KEY` - Backend API authentication
- `AGENT_API_BASE_URL` - Backend URL (optional, defaults to `http://localhost:42002`)

## Benchmark Questions Analysis

| # | Topic | Tool Required | Strategy |
|---|-------|---------------|----------|
| 0 | Protect branch (wiki) | read_file | Read wiki/git-workflow.md |
| 1 | SSH connection (wiki) | read_file | Read wiki/ssh.md or wiki/vm.md |
| 2 | Web framework (code) | read_file | Read backend/app/main.py |
| 3 | API routers | list_files | List backend/app/routers/ |
| 4 | Item count | query_api | GET /items/ |
| 5 | Auth status code | query_api | GET /items/ without auth |
| 6 | ZeroDivisionError | query_api + read_file | Query endpoint, then read analytics.py |
| 7 | TypeError bug | query_api + read_file | Query endpoint, then read analytics.py |
| 8 | Request lifecycle | read_file | Read docker-compose.yml, Dockerfile |
| 9 | ETL idempotency | read_file | Read etl.py |

## Iteration Strategy
1. Implement `query_api` tool with proper authentication
2. Update system prompt for clear tool selection
3. Run `run_eval.py` to identify failures
4. For each failure:
   - Check if correct tool was called
   - Verify tool returns expected data
   - Adjust system prompt if LLM chooses wrong tool
   - Fix any bugs in tool implementation
5. Repeat until all 10 questions pass

## Final Score
**10/10 PASSED** ✓

### All Questions Passing:
- Q0: Protect branch (wiki) ✓
- Q1: SSH connection (wiki) ✓
- Q2: Web framework (FastAPI) ✓
- Q3: Router modules ✓
- Q4: Item count ✓
- Q5: Unauthenticated status code (401) ✓
- Q6: ZeroDivisionError bug ✓
- Q7: Top-learners bug ✓
- Q8: Request lifecycle ✓
- Q9: ETL idempotency ✓

## Key Fixes That Made It Work

1. **Added `read_multiple_files` tool** - Allows reading multiple files in one call, reducing iterations
2. **Added explicit examples in system prompt** - Shows the LLM exactly what steps to follow
3. **Added guidance for direct file access** - For questions about specific files (etl.py, main.py), read directly without listing
4. **Fixed message ordering** - Assistant message with tool_calls must come BEFORE tool response messages (Qwen API requirement)
5. **Added `auth` parameter to query_api** - Allows testing unauthenticated access

## What Works Now
- Single file lookups (wiki questions)
- Multi-file analysis (using read_multiple_files)
- Bug diagnosis with API errors
- ETL pipeline analysis
- Request lifecycle tracing
