# Agent CLI Documentation

## Overview
This agent connects to an LLM via OpenAI-compatible API and returns structured JSON responses. It has tools (`read_file`, `read_multiple_files`, `list_files`, `query_api`) that allow it to navigate the project wiki, read source code, and query the backend API for real-time data.

## LLM Provider
- **Provider**: Qwen Code API (local deployment)
- **Model**: qwen3-coder-plus
- **API Base**: http://10.93.26.29:42005/v1

## Setup
1. Copy environment example:
   ```bash
   cp .env.agent.example .env.agent.secret
   cp .env.docker.example .env.docker.secret
   ```

2. Edit `.env.agent.secret` with your LLM credentials:
   ```bash
   LLM_API_KEY=your-api-key
   LLM_API_BASE=http://your-vm-ip:port/v1
   LLM_MODEL=qwen3-coder-plus
   ```

3. Edit `.env.docker.secret` with your backend API key:
   ```bash
   LMS_API_KEY=your-backend-api-key
   ```

4. Run the agent:
   ```bash
   python agent.py "Your question here"
   ```

## Output Format
The agent outputs a single JSON line to stdout:
```json
{
  "answer": "Response from LLM",
  "source": "wiki/filename.md#section-anchor",
  "tool_calls": [
    {"tool": "list_files", "args": {"path": "wiki"}, "result": "file1.md\nfile2.md"},
    {"tool": "read_multiple_files", "args": {"paths": ["backend/app/routers/items.py", "..."]}, "result": "...combined file contents..."},
    {"tool": "query_api", "args": {"method": "GET", "path": "/items/"}, "result": "{\"status_code\": 200, \"body\": \"...\"}"}
  ]
}
```

### Fields
- `answer` (string): The LLM's answer to the question
- `source` (string): Reference to the wiki file(s) or source code used to find the answer
- `tool_calls` (array): List of all tool calls made during the agentic loop

## Tools

### read_file
Read the contents of a single file from the project repository.

**Parameters:**
- `path` (string): Relative path from project root (e.g., `wiki/git.md`, `backend/app/main.py`)

**Returns:** File contents as string, or error message

**Use when:** You need to read ONE specific file

### read_multiple_files
Read multiple files at once and return their combined contents.

**Parameters:**
- `paths` (array): List of relative paths from project root

**Returns:** Combined contents with file separators, or error messages

**Use when:** You need to analyze several files from the same directory (e.g., all router modules). This is MORE EFFICIENT than calling `read_file` multiple times.

### list_files
List files and directories in a directory.

**Parameters:**
- `path` (string): Relative directory path from project root (e.g., `wiki`, `backend/app/routers`)

**Returns:** Newline-separated listing of entries, or error message

**Use when:** You need to discover what files exist in a directory

### query_api
Call the backend API to get real-time data or check system behavior.

**Parameters:**
- `method` (string): HTTP method (GET, POST, PUT, DELETE, PATCH)
- `path` (string): API endpoint path (e.g., `/items/`, `/analytics/completion-rate`)
- `body` (string, optional): JSON request body for POST/PUT/PATCH requests
- `auth` (boolean, default: true): Whether to include authentication header. Set to `false` to test unauthenticated access.

**Returns:** JSON string with `status_code` and `body`, or error message

**Authentication:** Uses `LMS_API_KEY` from environment variables when `auth: true`.

## Agentic Loop

The agent uses an agentic loop to answer questions:

1. **Send question**: The user's question + tool definitions + system prompt are sent to the LLM
2. **Check for tool calls**: 
   - If LLM returns `tool_calls`: execute each tool, append results as `tool` role messages, go to step 1
   - If no `tool_calls`: this is the final answer, output JSON and exit
3. **Maximum iterations**: The loop stops after 20 tool calls

```
User Question → LLM → Tool Calls? → Execute Tools → Results → LLM → Final Answer
                     ↓ No
                  Output JSON
```

## System Prompt Strategy

The system prompt includes **explicit examples** showing the LLM exactly how to approach different types of questions:

### Example Workflows

1. **Framework identification**: list_files → read_file → answer
2. **Multi-file analysis**: list_files → read_multiple_files → answer
3. **Specific file functionality**: read_file directly → focus on relevant function → answer

### Tool Selection Guide
- **Documentation questions** (wiki): Use `list_files` then `read_file`
- **Multi-file analysis** (routers, configs): Use `list_files` then `read_multiple_files`
- **Specific file questions** (etl.py, main.py): Use `read_file` directly
- **Database/API questions**: Use `query_api`
- **Unauthenticated access testing**: Use `query_api` with `auth: false`

## Security

Path validation prevents accessing files outside the project directory:
- Absolute paths are rejected
- Path traversal (`..`) is rejected
- All paths are resolved and checked to be within project root

## Environment Variables

The agent reads all configuration from environment variables (not hardcoded):

| Variable | Purpose | Source |
|----------|---------|--------|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` |
| `LLM_API_BASE` | LLM API endpoint URL | `.env.agent.secret` |
| `LLM_MODEL` | Model name | `.env.agent.secret` |
| `LMS_API_KEY` | Backend API authentication | `.env.docker.secret` |
| `AGENT_API_BASE_URL` | Backend URL (optional) | Defaults to `http://localhost:42002` |

> **Important:** The autochecker runs your agent with different credentials. Never hardcode these values.

## Error Handling
- Missing `LLM_API_KEY`: exits with error JSON
- Missing `LLM_API_BASE`: exits with error JSON
- No question argument: exits with error JSON
- API timeout (60s): exits with error JSON
- Connection errors: exits with error JSON
- Tool execution errors: returned as tool result message

All errors are returned as valid JSON with the `answer` field containing the error message.

## Example Usage

```bash
# Wiki lookup
python agent.py "How do you resolve a merge conflict?"

# Multi-file analysis
python agent.py "List all API router modules and their domains"

# Single file functionality
python agent.py "How does the ETL pipeline ensure idempotency?"

# Database query
python agent.py "How many items are in the database?"

# Unauthenticated access test
python agent.py "What status code does /items/ return without authentication?"
```

## Benchmark Results

### Final Score: 10/10 PASSED ✓

All local benchmark questions pass:
1. ✓ Wiki: Branch protection steps
2. ✓ Wiki: SSH connection steps
3. ✓ Source code: FastAPI framework identification
4. ✓ Multi-file: Router modules analysis
5. ✓ API: Item count query
6. ✓ API: Unauthenticated status code (401)
7. ✓ Bug diagnosis: ZeroDivisionError in completion-rate
8. ✓ Bug diagnosis: TypeError in top-learners
9. ✓ System architecture: Request lifecycle
10. ✓ ETL pipeline: Idempotency mechanism

## Lessons Learned

### Key Challenges and Solutions

1. **LLM Task Persistence**
   - **Problem**: The qwen3-coder-plus model would stop mid-task, responding with "Let me continue..." instead of continuing tool calls
   - **Solution**: Added `read_multiple_files` tool to reduce iterations, plus explicit examples in system prompt

2. **Multi-File Analysis**
   - **Problem**: LLM would read 2-3 of 6 files then give partial answer
   - **Solution**: `read_multiple_files` tool reads all files in one call

3. **List Files Loop**
   - **Problem**: LLM would call list_files multiple times on same directory
   - **Solution**: Added explicit guidance "NEVER call list_files multiple times"

4. **Qwen API Message Ordering**
   - **Problem**: 500 errors from Qwen API
   - **Solution**: Assistant message with tool_calls must come BEFORE tool response messages

5. **Unauthenticated Testing**
   - **Problem**: Agent always used LMS_API_KEY, couldn't test 401 responses
   - **Solution**: Added `auth` parameter to `query_api`

### Test Suite
8 regression tests covering:
- Basic CLI interface (question required, env vars required)
- Output format (answer, source, tool_calls fields)
- Tool existence (read_file, list_files, read_multiple_files, query_api)
- System question response format

All tests pass.
