#!/usr/bin/env python3
"""
Agent CLI with tools (read_file, list_files, query_api) and agentic loop.
Sends questions to LLM, executes tool calls, and returns structured JSON responses.
"""

import os
import sys
import json
import requests


# Project root directory (where agent.py is located)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Maximum tool calls per question
# Increased to handle multi-file analysis tasks
MAX_TOOL_CALLS = 20


def validate_path(path: str) -> tuple[bool, str]:
    """
    Validate that a path is within the project directory.
    Returns (is_valid, error_message).
    """
    # Reject absolute paths
    if os.path.isabs(path):
        return False, "Absolute paths not allowed"
    
    # Reject path traversal
    if ".." in path:
        return False, "Path traversal not allowed"
    
    # Resolve the full path
    full_path = os.path.realpath(os.path.join(PROJECT_ROOT, path))
    
    # Ensure it's within project root
    if not full_path.startswith(PROJECT_ROOT):
        return False, "Path outside project directory"
    
    return True, full_path


def read_file(path: str) -> str:
    """
    Read a file from the project repository.
    
    Args:
        path: Relative path from project root
        
    Returns:
        File contents as string, or error message
    """
    is_valid, result = validate_path(path)
    if not is_valid:
        return f"Error: {result}"
    
    try:
        with open(result, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: File not found: {path}"
    except IsADirectoryError:
        return f"Error: Path is a directory: {path}"
    except Exception as e:
        return f"Error: {str(e)}"


def list_files(path: str) -> str:
    """
    List files and directories at a given path.
    
    Args:
        path: Relative directory path from project root
        
    Returns:
        Newline-separated listing, or error message
    """
    is_valid, result = validate_path(path)
    if not is_valid:
        return f"Error: {result}"
    
    try:
        entries = os.listdir(result)
        return "\n".join(sorted(entries))
    except FileNotFoundError:
        return f"Error: Directory not found: {path}"
    except NotADirectoryError:
        return f"Error: Path is not a directory: {path}"
    except Exception as e:
        return f"Error: {str(e)}"


def read_multiple_files(paths: list) -> str:
    """
    Read multiple files at once and return their contents.
    
    Args:
        paths: List of relative paths from project root
        
    Returns:
        Combined contents with file separators, or error messages
    """
    results = []
    for path in paths:
        content = read_file(path)
        results.append(f"=== {path} ===\n{content}")
    return "\n\n".join(results)


def query_api(method: str, path: str, body: str = None, auth: bool = True) -> str:
    """
    Call the backend API.

    Args:
        method: HTTP method (GET, POST, etc.)
        path: API endpoint path (e.g., '/items/')
        body: Optional JSON request body for POST/PUT requests
        auth: Whether to include authentication header (default: True)

    Returns:
        JSON string with status_code and body, or error message
    """
    # Get configuration from environment
    api_base = os.getenv('AGENT_API_BASE_URL', 'http://localhost:42002')
    lms_api_key = os.getenv('LMS_API_KEY')

    url = f"{api_base}{path}"
    headers = {
        "Content-Type": "application/json"
    }

    # Add auth header only if auth is True
    if auth:
        if not lms_api_key:
            return json.dumps({
                "status_code": 0,
                "body": "Error: LMS_API_KEY environment variable not set"
            })
        headers["Authorization"] = f"Bearer {lms_api_key}"

    try:
        # Prepare request
        kwargs = {
            "method": method.upper(),
            "url": url,
            "headers": headers,
            "timeout": 30
        }
        
        # Add body for POST/PUT/PATCH
        if body and method.upper() in ["POST", "PUT", "PATCH"]:
            kwargs["data"] = body
        
        # Make request
        response = requests.request(**kwargs)
        
        # Return response as JSON string
        return json.dumps({
            "status_code": response.status_code,
            "body": response.text
        })
        
    except requests.exceptions.Timeout:
        return json.dumps({
            "status_code": 0,
            "body": "Error: Request timed out"
        })
    except requests.exceptions.ConnectionError as e:
        return json.dumps({
            "status_code": 0,
            "body": f"Error: Connection error - {str(e)}"
        })
    except Exception as e:
        return json.dumps({
            "status_code": 0,
            "body": f"Error: {str(e)}"
        })


# Tool definitions for LLM function calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a single file from the project repository. Use this to read documentation (wiki/*.md), source code (backend/*.py), or configuration files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root (e.g., 'wiki/git.md', 'backend/app/main.py')"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_multiple_files",
            "description": "Read multiple files at once. USE THIS when you need to analyze several files in the same directory (e.g., all router modules, all config files). More efficient than calling read_file multiple times.",
            "parameters": {
                "type": "object",
                "properties": {
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of relative paths from project root (e.g., ['backend/app/routers/items.py', 'backend/app/routers/analytics.py'])"
                    }
                },
                "required": ["paths"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories in a directory. Use this to discover what files exist in a directory (e.g., list wiki/ contents, list backend/app/routers/ contents).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path from project root (e.g., 'wiki', 'backend/app/routers')"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_api",
            "description": "Call the backend API to get real-time data or check system behavior. Use this for questions about: database contents (item count, scores), API responses (status codes, errors), analytics data (completion rates, top learners), or current system state. Do NOT use for documentation questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "description": "HTTP method (GET, POST, PUT, DELETE, PATCH)",
                        "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"]
                    },
                    "path": {
                        "type": "string",
                        "description": "API endpoint path (e.g., '/items/', '/analytics/completion-rate', '/analytics/top-learners')"
                    },
                    "body": {
                        "type": "string",
                        "description": "Optional JSON request body for POST/PUT/PATCH requests"
                    },
                    "auth": {
                        "type": "boolean",
                        "description": "Whether to include authentication header (default: true). Set to false to test unauthenticated access."
                    }
                },
                "required": ["method", "path"]
            }
        }
    }
]

# Map tool names to functions
TOOL_FUNCTIONS = {
    "read_file": read_file,
    "read_multiple_files": read_multiple_files,
    "list_files": list_files,
    "query_api": query_api
}

# System prompt for the agent
SYSTEM_PROMPT = """You are a documentation and system assistant for a software engineering lab.
You have access to tools that let you:
1. Read files (read_file) - for documentation (wiki/*.md), source code (backend/*.py), and config files
2. Read multiple files at once (read_multiple_files) - EFFICIENT way to read several files in one call
3. List directories (list_files) - to discover what files exist
4. Query the backend API (query_api) - for real-time data, API responses, status codes, and analytics

EXAMPLE WORKFLOWS:
- Question: "What framework does the backend use?"
  Step 1: list_files("backend/app")
  Step 2: read_file("backend/app/main.py")  <- READ THE FILE to find imports
  Step 3: Answer based on file contents

- Question: "List all router modules and their domains"
  Step 1: list_files("backend/app/routers")
  Step 2: read_multiple_files(["backend/app/routers/items.py", "backend/app/routers/analytics.py", ...])  <- READ ALL FILES
  Step 3: Answer with complete information about each router

- Question: "How does the ETL pipeline ensure idempotency?"
  Step 1: read_file("backend/app/etl.py")  <- Go directly to the relevant file
  Step 2: Focus on the load() function and how it handles duplicates
  Step 3: Answer based on what you find about external_id checks

Tool selection guide:
- Use list_files when asked about what files exist in a directory
- IMPORTANT: After using list_files ONCE, you MUST follow up with read_file or read_multiple_files to actually read the file contents
- NEVER call list_files multiple times - use the results you already have
- For questions about a specific file (like etl.py, main.py), use read_file DIRECTLY without listing first
- Use read_multiple_files when you need to read MULTIPLE files from the same directory - THIS IS MORE EFFICIENT
- Use read_file when you need to read just ONE file
- Use query_api when asked about:
  - Database contents (how many items, scores)
  - API behavior (what status code, error messages)
  - Analytics data (completion rates, top learners)
  - Real-time system state

For query_api:
- Use auth: true (default) for normal authenticated requests
- Use auth: false when testing unauthenticated access or checking what happens without credentials

Important guidelines:
- After listing files, ALWAYS read the relevant files to get the actual content
- When asked about a specific file's functionality, read THAT FILE directly and focus on the relevant function
- CRITICAL: Do NOT provide a partial answer - read ALL relevant files FIRST, then provide a complete answer
- Only respond with final answer text when you have gathered all necessary information from tools
- If you haven't read all the files needed to answer completely, continue calling tools

Always provide accurate answers based on actual file contents or API responses.
Include source references (file path) when answering from files.
For API queries, report the actual status codes and error messages you receive."""


def execute_tool(tool_name: str, args: dict) -> str:
    """
    Execute a tool and return the result.
    
    Args:
        tool_name: Name of the tool to execute
        args: Arguments for the tool
        
    Returns:
        Tool result as string
    """
    if tool_name not in TOOL_FUNCTIONS:
        return f"Error: Unknown tool: {tool_name}"
    
    func = TOOL_FUNCTIONS[tool_name]
    try:
        return func(**args)
    except Exception as e:
        return f"Error: {str(e)}"


def call_llm(api_key: str, api_base: str, model: str, messages: list) -> dict:
    """
    Make API call to LLM.
    
    Args:
        api_key: LLM API key
        api_base: LLM API base URL
        model: Model name
        messages: List of message dicts
        
    Returns:
        Parsed response data
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "tools": TOOLS,
        "tool_choice": "auto"
    }
    
    response = requests.post(
        f"{api_base}/chat/completions",
        headers=headers,
        json=payload,
        timeout=60
    )
    response.raise_for_status()
    
    return response.json()


def extract_source_from_answer(answer: str, tool_calls: list) -> str:
    """
    Extract source reference from tool calls.
    
    Args:
        answer: The final answer text
        tool_calls: List of tool call records
        
    Returns:
        Source reference string
    """
    # Find the last read_file call to get the source file
    for call in reversed(tool_calls):
        if call["tool"] == "read_file":
            path = call["args"].get("path", "")
            if path.endswith(".md"):
                return path
            elif path.endswith(".py") or path.endswith(".yml") or path.endswith(".yaml"):
                return path
    
    return ""


def run_agentic_loop(api_key: str, api_base: str, model: str, question: str) -> dict:
    """
    Run the agentic loop to answer a question.
    
    Args:
        api_key: LLM API key
        api_base: LLM API base URL
        model: Model name
        question: User's question
        
    Returns:
        Dict with answer, source, and tool_calls
    """
    # Initialize messages with system prompt and user question
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question}
    ]
    
    tool_calls_log = []
    
    for iteration in range(MAX_TOOL_CALLS):
        # Call LLM
        response_data = call_llm(api_key, api_base, model, messages)
        
        # Get the assistant message
        assistant_message = response_data["choices"][0]["message"]
        
        # Check for tool calls
        tool_calls = assistant_message.get("tool_calls") or []
        
        if not tool_calls:
            # No tool calls - this is the final answer
            answer = assistant_message.get("content") or "No answer provided"
            source = extract_source_from_answer(answer, tool_calls_log)
            
            return {
                "answer": answer,
                "source": source,
                "tool_calls": tool_calls_log
            }
        
        # Add assistant message with tool_calls to messages FIRST
        # This is required for Qwen API - tool responses must reference a preceding message with tool_calls
        assistant_msg_copy = {
            "role": "assistant",
            "content": assistant_message.get("content") or ""
        }
        if tool_calls:
            assistant_msg_copy["tool_calls"] = tool_calls
        messages.append(assistant_msg_copy)

        # Execute tool calls and add tool responses AFTER the assistant message
        for tool_call in tool_calls:
            if tool_call.get("type") != "function":
                continue

            function = tool_call.get("function", {})
            tool_name = function.get("name", "")

            try:
                args = json.loads(function.get("arguments", "{}"))
            except json.JSONDecodeError:
                args = {}

            # Execute the tool
            result = execute_tool(tool_name, args)

            # Log the tool call
            tool_calls_log.append({
                "tool": tool_name,
                "args": args,
                "result": result
            })

            # Add tool response to messages
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.get("id", ""),
                "content": result
            })
    
    # Max iterations reached
    return {
        "answer": "Reached maximum tool calls limit. Here's what I found so far.",
        "source": extract_source_from_answer("", tool_calls_log),
        "tool_calls": tool_calls_log
    }


def main():
    # Get configuration from environment variables
    api_key = os.getenv('LLM_API_KEY')
    api_base = os.getenv('LLM_API_BASE')
    model = os.getenv('LLM_MODEL', 'qwen3-coder-plus')

    # Validate configuration
    if not api_key:
        print(json.dumps({
            "answer": "Error: LLM_API_KEY environment variable not set",
            "source": "",
            "tool_calls": []
        }))
        sys.exit(1)

    if not api_base:
        print(json.dumps({
            "answer": "Error: LLM_API_BASE environment variable not set",
            "source": "",
            "tool_calls": []
        }))
        sys.exit(1)

    # Check question argument
    if len(sys.argv) < 2:
        print(json.dumps({
            "answer": "Error: Please provide a question as argument",
            "source": "",
            "tool_calls": []
        }))
        sys.exit(1)

    question = sys.argv[1]

    try:
        # Run agentic loop
        result = run_agentic_loop(api_key, api_base, model, question)
        
        # Output structured JSON
        print(json.dumps(result))
        sys.exit(0)

    except requests.exceptions.Timeout:
        print(json.dumps({
            "answer": "Error: LLM request timed out",
            "source": "",
            "tool_calls": []
        }))
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(json.dumps({
            "answer": f"Error: Failed to connect to LLM - {str(e)}",
            "source": "",
            "tool_calls": []
        }))
        sys.exit(1)
    except KeyError as e:
        print(json.dumps({
            "answer": f"Error: Unexpected LLM response format - {str(e)}",
            "source": "",
            "tool_calls": []
        }))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({
            "answer": f"Error: {str(e)}",
            "source": "",
            "tool_calls": []
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
