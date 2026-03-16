# Agent CLI Documentation

## Overview
This agent connects to an LLM via OpenAI-compatible API and returns structured JSON responses. It has tools (`read_file`, `list_files`) that allow it to navigate the project wiki and find answers from actual documentation.

## LLM Provider
- **Provider**: Qwen Code API (local deployment)
- **Model**: qwen3-coder-plus
- **API Base**: http://10.93.26.29:8000/v1

## Setup
1. Copy environment example:
   ```bash
   cp .env.agent.example .env.agent.secret
   ```

2. Edit `.env.agent.secret` with your credentials:
   ```bash
   LLM_API_KEY=your-api-key
   LLM_API_BASE=http://your-vm-ip:port/v1
   LLM_MODEL=qwen3-coder-plus
   ```

3. Run the agent:
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
    {"tool": "read_file", "args": {"path": "wiki/filename.md"}, "result": "...file contents..."}
  ]
}
```

### Fields
- `answer` (string): The LLM's answer to the question
- `source` (string): Reference to the wiki file(s) used to find the answer
- `tool_calls` (array): List of all tool calls made during the agentic loop

## Tools

### read_file
Read the contents of a file from the project repository.

**Parameters:**
- `path` (string): Relative path from project root (e.g., `wiki/git.md`)

**Returns:** File contents as string, or error message

### list_files
List files and directories in a directory.

**Parameters:**
- `path` (string): Relative directory path from project root (e.g., `wiki`)

**Returns:** Newline-separated listing of entries, or error message

## Agentic Loop

The agent uses an agentic loop to answer questions:

1. **Send question**: The user's question + tool definitions are sent to the LLM
2. **Check for tool calls**: 
   - If LLM returns `tool_calls`: execute each tool, append results as `tool` role messages, go to step 1
   - If no `tool_calls`: this is the final answer, output JSON and exit
3. **Maximum iterations**: The loop stops after 10 tool calls

```
User Question → LLM → Tool Calls? → Execute Tools → Results → LLM → Final Answer
                     ↓ No
                  Output JSON
```

## System Prompt Strategy

The system prompt instructs the LLM to:
1. Use `list_files` to discover what files exist in the wiki directory
2. Use `read_file` to read specific files and find accurate answers
3. Include source references (file path + section anchor) in answers
4. Only call tools when necessary

## Security

Path validation prevents accessing files outside the project directory:
- Absolute paths are rejected
- Path traversal (`..`) is rejected
- All paths are resolved and checked to be within project root

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
# Ask a question about git workflow
python agent.py "How do you resolve a merge conflict?"

# Ask about files in the wiki
python agent.py "What files are in the wiki directory?"
```
