#!/usr/bin/env python3
"""
Agent CLI that sends questions to LLM and returns structured JSON responses.
"""

import os
import sys
import json
import requests


def main():
    # Get configuration from environment variables
    api_key = os.getenv('LLM_API_KEY')
    api_base = os.getenv('LLM_API_BASE')
    model = os.getenv('LLM_MODEL', 'qwen3-coder-plus')
    
    # Validate configuration - MUST exit with error if missing
    if not api_key:
        print(json.dumps({
            "answer": "Error: LLM_API_KEY environment variable not set",
            "tool_calls": []
        }))
        sys.exit(1)  # Non-zero exit code for error
    
    if not api_base:
        print(json.dumps({
            "answer": "Error: LLM_API_BASE environment variable not set",
            "tool_calls": []
        }))
        sys.exit(1)  # Non-zero exit code for error
    
    # Check question argument
    if len(sys.argv) < 2:
        print(json.dumps({
            "answer": "Error: Please provide a question as argument",
            "tool_calls": []
        }))
        sys.exit(1)
    
    question = sys.argv[1]
    
    try:
        # Make API call to LLM
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": question}
            ]
        }
        
        response = requests.post(
            f"{api_base}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        
        # Parse response
        data = response.json()
        answer = data["choices"][0]["message"]["content"]
        
        # Output structured JSON
        print(json.dumps({
            "answer": answer,
            "tool_calls": []
        }))
        sys.exit(0)  # Success
        
    except requests.exceptions.Timeout:
        print(json.dumps({
            "answer": "Error: LLM request timed out",
            "tool_calls": []
        }))
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(json.dumps({
            "answer": f"Error: Failed to connect to LLM - {str(e)}",
            "tool_calls": []
        }))
        sys.exit(1)
    except KeyError as e:
        print(json.dumps({
            "answer": f"Error: Unexpected LLM response format - {str(e)}",
            "tool_calls": []
        }))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({
            "answer": f"Error: {str(e)}",
            "tool_calls": []
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()

