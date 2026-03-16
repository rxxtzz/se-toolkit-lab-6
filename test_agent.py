#!/usr/bin/env python3
"""
Regression tests for agent.py - Fixed version
"""

import unittest
import subprocess
import json
import os
import sys


class TestAgent(unittest.TestCase):
    """Test the agent CLI"""
    
    def setUp(self):
        """Check that agent.py exists"""
        self.agent_path = os.path.join(os.path.dirname(__file__), 'agent.py')
        self.assertTrue(os.path.exists(self.agent_path), "agent.py not found")
    
    def test_agent_requires_question(self):
        """Test that agent fails without question"""
        # Set minimal valid env vars
        env = os.environ.copy()
        env['LLM_API_KEY'] = 'dummy-key'
        env['LLM_API_BASE'] = 'http://dummy-api/v1'
        env['LLM_MODEL'] = 'dummy-model'
        
        result = subprocess.run(
            [sys.executable, self.agent_path],
            capture_output=True,
            text=True,
            env=env
        )
        
        # Should exit with error
        self.assertNotEqual(result.returncode, 0)
        
        # Should output valid JSON
        try:
            output = json.loads(result.stdout)
            self.assertIn('answer', output)
            self.assertIn('tool_calls', output)
        except json.JSONDecodeError:
            self.fail(f"Output is not valid JSON: {result.stdout}")
    
    def test_agent_requires_env_vars(self):
        """Test that agent fails without required env vars"""
        # Run without setting env vars
        result = subprocess.run(
            [sys.executable, self.agent_path, "test question"],
            capture_output=True,
            text=True,
            env={}  # Empty environment
        )
        
        # Should exit with error
        self.assertNotEqual(result.returncode, 0)
        
        # Should output valid JSON with error message
        try:
            output = json.loads(result.stdout)
            self.assertIn('answer', output)
            self.assertIn('tool_calls', output)
            # Should mention missing API key
            self.assertTrue(
                'LLM_API_KEY' in output['answer'] or 
                'API key' in output['answer'].lower()
            )
        except json.JSONDecodeError:
            self.fail(f"Output is not valid JSON: {result.stdout}")
    
    def test_agent_output_format(self):
        """Test that agent produces correct JSON format (without real API call)"""
        # This test just checks that the script runs and produces JSON
        # It will fail because API is not reachable, but that's expected
        env = os.environ.copy()
        env['LLM_API_KEY'] = 'test-key'
        env['LLM_API_BASE'] = 'http://localhost:9999'  # Non-existent port
        env['LLM_MODEL'] = 'test-model'

        result = subprocess.run(
            [sys.executable, self.agent_path, "test"],
            capture_output=True,
            text=True,
            env=env,
            timeout=5  # Prevent hanging
        )

        # Should output valid JSON even on error
        try:
            output = json.loads(result.stdout)
            self.assertIn('answer', output)
            self.assertIn('tool_calls', output)
            # tool_calls should be a list
            self.assertIsInstance(output['tool_calls'], list)
        except json.JSONDecodeError:
            self.fail(f"Output is not valid JSON: {result.stdout}")

    def test_agent_has_source_field(self):
        """Test that agent output includes source field (Task 2 requirement)"""
        env = os.environ.copy()
        env['LLM_API_KEY'] = 'test-key'
        env['LLM_API_BASE'] = 'http://localhost:9999'
        env['LLM_MODEL'] = 'test-model'

        result = subprocess.run(
            [sys.executable, self.agent_path, "test question"],
            capture_output=True,
            text=True,
            env=env,
            timeout=5
        )

        # Should output valid JSON with source field
        try:
            output = json.loads(result.stdout)
            self.assertIn('source', output)
        except json.JSONDecodeError:
            self.fail(f"Output is not valid JSON: {result.stdout}")

    def test_agent_tools_exist(self):
        """Test that the agent has read_file and list_files tools implemented"""
        # This test verifies the tools are implemented by checking the agent code
        with open(self.agent_path, 'r') as f:
            code = f.read()

        # Check that read_file function exists
        self.assertIn('def read_file', code, "read_file function not implemented")

        # Check that list_files function exists
        self.assertIn('def list_files', code, "list_files function not implemented")

        # Check that tools are registered
        self.assertIn('"read_file"', code, "read_file tool not registered")
        self.assertIn('"list_files"', code, "list_files tool not registered")

        # Check that agentic loop exists
        self.assertIn('MAX_TOOL_CALLS', code, "Max tool calls limit not implemented")

    def test_agent_query_api_tool_exists(self):
        """Test that the agent has query_api tool implemented (Task 3 requirement)"""
        with open(self.agent_path, 'r') as f:
            code = f.read()

        # Check that query_api function exists
        self.assertIn('def query_api', code, "query_api function not implemented")

        # Check that query_api tool is registered
        self.assertIn('"query_api"', code, "query_api tool not registered")

        # Check that auth parameter is supported
        self.assertIn('auth', code, "query_api auth parameter not implemented")

    def test_agent_read_multiple_files_exists(self):
        """Test that the agent has read_multiple_files tool (Task 3 optimization)"""
        with open(self.agent_path, 'r') as f:
            code = f.read()

        # Check that read_multiple_files function exists
        self.assertIn('def read_multiple_files', code, "read_multiple_files function not implemented")

        # Check that read_multiple_files tool is registered
        self.assertIn('"read_multiple_files"', code, "read_multiple_files tool not registered")

    def test_agent_system_question_response(self):
        """Test that agent produces valid JSON for system questions (Task 3 requirement)"""
        # This test verifies the agent can handle questions about the system
        # It will fail because API is not reachable, but should still produce valid JSON
        env = os.environ.copy()
        env['LLM_API_KEY'] = 'test-key'
        env['LLM_API_BASE'] = 'http://localhost:9999'
        env['LLM_MODEL'] = 'test-model'
        env['LMS_API_KEY'] = 'test-lms-key'

        result = subprocess.run(
            [sys.executable, self.agent_path, "How many items are in the database?"],
            capture_output=True,
            text=True,
            env=env,
            timeout=10  # Short timeout since API won't respond
        )

        # Should output valid JSON even on error
        try:
            output = json.loads(result.stdout)
            self.assertIn('answer', output)
            self.assertIn('tool_calls', output)
            self.assertIn('source', output)
        except json.JSONDecodeError:
            self.fail(f"Output is not valid JSON: {result.stdout}")


if __name__ == '__main__':
    unittest.main()
