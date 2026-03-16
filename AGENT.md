# Agent CLI Documentation

## Overview
This agent connects to an LLM via OpenAI-compatible API and returns structured JSON responses.

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
{"answer": "Response from LLM", "tool_calls": []}
```

## Error Handling
- Missing `LLM_API_KEY`: exits with error JSON
- Missing `LLM_API_BASE`: exits with error JSON
- No question argument: exits with error JSON
- API timeout (60s): exits with error JSON
- Connection errors: exits with error JSON

All errors are returned as valid JSON with the `answer` field containing the error message.