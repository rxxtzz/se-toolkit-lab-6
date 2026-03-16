#!/usr/bin/env python3
"""
Agent CLI with tools (read_file, list_files) and agentic loop.
Sends questions to LLM, executes tool calls, and returns structured JSON responses.
"""

import os
import sys
import json
import requests


# Project root directory (where agent.py is located)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Maximum tool calls per question
MAX_TOOL_CALLS = 10


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


# Tool definitions for LLM function calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file from the project repository. Use this to read specific files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root (e.g., 'wiki/git.md')"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories in a directory. Use this to discover what files exist.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path from project root (e.g., 'wiki')"
                    }
                },
                "required": ["path"]
            }
        }
    }
]

# Map tool names to functions
TOOL_FUNCTIONS = {
    "read_file": read_file,
    "list_files": list_files
}

# System prompt for the agent
SYSTEM_PROMPT = """You are a documentation assistant for a software engineering lab. 
You have access to tools that let you read files and list directories in the project wiki.

When answering questions:
1. Use `list_files` to discover what files exist in the wiki directory
2. Use `read_file` to read specific files and find the answer
3. Include a source reference in your answer (file path + section anchor if applicable)
4. Only call tools when necessary to find accurate information

Always provide accurate answers based on the actual file contents you read."""


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


def call_lllm(api_key: str, api_base: str, model: str, messages: list) -> dict:
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
                # Try to find a section anchor from the answer
                # For now, just return the file path
                return path
    
    return "wiki"


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
        response_data = call_lllm(api_key, api_base, model, messages)
        
        # Get the assistant message
        assistant_message = response_data["choices"][0]["message"]
        
        # Check for tool calls
        tool_calls = assistant_message.get("tool_calls", [])
        
        if not tool_calls:
            # No tool calls - this is the final answer
            answer = assistant_message.get("content", "No answer provided")
            source = extract_source_from_answer(answer, tool_calls_log)
            
            return {
                "answer": answer,
                "source": source,
                "tool_calls": tool_calls_log
            }
        
        # Execute tool calls
        for tool_call in tool_calls:
            if tool_call["type"] != "function":
                continue
            
            function = tool_call["function"]
            tool_name = function["name"]
            
            try:
                args = json.loads(function["arguments"])
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
                "tool_call_id": tool_call["id"],
                "content": result
            })
        
        # Add assistant message to conversation
        messages.append(assistant_message)
    
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
