# Task 1: Call an LLM from Code

## LLM Provider
- **Provider**: Qwen Code API (local deployment on VM)
- **Model**: qwen3-coder-plus
- **API Base**: http://10.93.26.29:8000/v1
- **API Key**: sk-403859a3412d4b61931d989ae20863f9

## Architecture
The agent will:
1. Read configuration from `.env.agent.secret`
2. Take a question as command-line argument
3. Send request to OpenAI-compatible chat completions endpoint
4. Parse response and output JSON with required format

## Implementation Plan
- Use `python-dotenv` for environment variables
- Use `requests` for HTTP calls
- Handle errors gracefully
- Output only valid JSON to stdout
- Send debug info to stderr
