# Task 2: The Documentation Agent

## Overview
Build an agentic loop that allows the LLM to use tools (`read_file`, `list_files`) to navigate the wiki and find answers.

## Tool Schemas

### read_file
- **Purpose**: Read contents of a file from the project repository
- **Parameters**: `path` (string) - relative path from project root
- **Returns**: File contents as string, or error message if file doesn't exist
- **Security**: Validate path doesn't contain `..` traversal

### list_files
- **Purpose**: List files and directories at a given path
- **Parameters**: `path` (string) - relative directory path from project root
- **Returns**: Newline-separated listing of entries
- **Security**: Validate path doesn't contain `..` traversal

## Function Calling Schema Format
Tools will be defined as JSON schemas in the `tools` parameter of the chat completions API:

```json
{
  "type": "function",
  "function": {
    "name": "read_file",
    "description": "Read a file from the project repository",
    "parameters": {
      "type": "object",
      "properties": {
        "path": {"type": "string", "description": "Relative path from project root"}
      },
      "required": ["path"]
    }
  }
}
```

## Agentic Loop Algorithm

1. **Initialize**: Create messages list with system prompt + user question
2. **Loop** (max 10 iterations):
   - Send messages + tool definitions to LLM
   - Parse response:
     - If `tool_calls` present: execute each tool, append results as `tool` role messages, continue
     - If no `tool_calls`: extract answer, break loop
3. **Output**: Return JSON with `answer`, `source`, and `tool_calls`

## Path Security
- Resolve the full path using `os.path.join(project_root, path)`
- Use `os.path.realpath()` to resolve symlinks
- Check that resolved path starts with project root
- Reject any path containing `..` or absolute paths

## System Prompt Strategy
The system prompt will instruct the LLM to:
1. Use `list_files` to discover wiki files when needed
2. Use `read_file` to read specific files for answers
3. Include source reference (file path + section anchor) in the final answer
4. Only call tools when necessary to find the answer

## Output Format
```json
{
  "answer": "The answer to the user's question",
  "source": "wiki/filename.md#section-anchor",
  "tool_calls": [
    {"tool": "list_files", "args": {"path": "wiki"}, "result": "..."},
    {"tool": "read_file", "args": {"path": "wiki/filename.md"}, "result": "..."}
  ]
}
```

## Error Handling
- Tool execution errors: return error message as tool result
- LLM API errors: return error JSON and exit
- Path security violations: return error message as tool result
- Max iterations (10): stop looping and return best available answer
