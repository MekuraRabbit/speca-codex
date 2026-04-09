"""
Tests for the APIRunner — OpenAI-compatible tool-loop runner.

Covers:
  - Tool execution functions (Read, Grep, Glob, Write)
  - Result normalization
  - Result extraction from response messages
  - Runner construction and interface compatibility
"""

import asyncio
import json
import os
import sys
import tempfile

import pytest

# Ensure the scripts directory is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from orchestrator.api_runner import (
    APIRunner,
    _execute_read,
    _execute_grep,
    _execute_glob,
    _execute_write,
    TOOL_DEFINITIONS,
    TOOL_EXECUTORS,
)
from orchestrator.config import get_phase_config
from orchestrator.runner import CircuitBreaker


# ---------------------------------------------------------------------------
# Tool execution tests
# ---------------------------------------------------------------------------


class TestReadTool:
    """Tests for the Read tool executor."""

    def test_read_existing_file(self, tmp_path):
        content = "line1\nline2\nline3\n"
        f = tmp_path / "test.txt"
        f.write_text(content)

        result = _execute_read({"file_path": str(f)})
        assert "1\tline1" in result
        assert "2\tline2" in result
        assert "3\tline3" in result

    def test_read_nonexistent_file(self):
        result = _execute_read({"file_path": "/nonexistent/file.txt"})
        assert "Error" in result
        assert "not found" in result.lower()

    def test_read_with_offset_and_limit(self, tmp_path):
        lines = [f"line{i}\n" for i in range(20)]
        f = tmp_path / "long.txt"
        f.write_text("".join(lines))

        result = _execute_read({"file_path": str(f), "offset": 5, "limit": 3})
        assert "6\tline5" in result
        assert "7\tline6" in result
        assert "8\tline7" in result
        assert "line8" not in result

    def test_read_empty_file(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("")

        result = _execute_read({"file_path": str(f)})
        assert "empty" in result.lower() or result.strip() == ""

    def test_read_directory_error(self, tmp_path):
        result = _execute_read({"file_path": str(tmp_path)})
        assert "Error" in result


class TestGrepTool:
    """Tests for the Grep tool executor."""

    def test_grep_finds_matches(self, tmp_path):
        f = tmp_path / "code.c"
        f.write_text("int main() {\n  return 0;\n}\n")

        result = _execute_grep({"pattern": "main", "path": str(tmp_path)})
        assert "main" in result

    def test_grep_no_matches(self, tmp_path):
        f = tmp_path / "code.c"
        f.write_text("int foo() { return 0; }\n")

        result = _execute_grep({"pattern": "zzz_nonexistent_zzz", "path": str(tmp_path)})
        assert "No matches" in result

    def test_grep_with_glob_filter(self, tmp_path):
        (tmp_path / "a.c").write_text("hello world\n")
        (tmp_path / "b.py").write_text("hello python\n")

        result = _execute_grep({
            "pattern": "hello",
            "path": str(tmp_path),
            "glob": "*.c",
        })
        assert "world" in result
        # .py file should not match with *.c glob
        assert "python" not in result


class TestGlobTool:
    """Tests for the Glob tool executor."""

    def test_glob_finds_files(self, tmp_path):
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        (tmp_path / "c.py").write_text("c")

        result = _execute_glob({"pattern": "*.txt", "path": str(tmp_path)})
        assert "a.txt" in result
        assert "b.txt" in result
        assert "c.py" not in result

    def test_glob_no_matches(self, tmp_path):
        result = _execute_glob({"pattern": "*.xyz", "path": str(tmp_path)})
        assert "No matching" in result

    def test_glob_recursive(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "deep.go").write_text("package main")

        result = _execute_glob({"pattern": "**/*.go", "path": str(tmp_path)})
        assert "deep.go" in result


class TestWriteTool:
    """Tests for the Write tool executor."""

    def test_write_creates_file(self, tmp_path):
        target = tmp_path / "output.json"
        result = _execute_write({
            "file_path": str(target),
            "content": '{"key": "value"}',
        })
        assert "Successfully" in result
        assert target.exists()
        assert json.loads(target.read_text()) == {"key": "value"}

    def test_write_creates_parent_dirs(self, tmp_path):
        target = tmp_path / "a" / "b" / "c" / "out.txt"
        result = _execute_write({
            "file_path": str(target),
            "content": "hello",
        })
        assert "Successfully" in result
        assert target.read_text() == "hello"


# ---------------------------------------------------------------------------
# Tool definitions sanity
# ---------------------------------------------------------------------------


class TestToolDefinitions:
    """Verify tool definitions match executors."""

    def test_all_tools_have_executors(self):
        tool_names = {t["function"]["name"] for t in TOOL_DEFINITIONS}
        executor_names = set(TOOL_EXECUTORS.keys())
        assert tool_names == executor_names

    def test_tool_definitions_valid_schema(self):
        for tool in TOOL_DEFINITIONS:
            assert tool["type"] == "function"
            func = tool["function"]
            assert "name" in func
            assert "description" in func
            assert "parameters" in func
            assert func["parameters"]["type"] == "object"
            assert "required" in func["parameters"]


# ---------------------------------------------------------------------------
# Result normalization
# ---------------------------------------------------------------------------


class TestResultNormalization:
    """Test APIRunner._normalize_result_data."""

    def _make_runner(self):
        config = get_phase_config("03")
        sem = asyncio.Semaphore(1)
        return APIRunner(config, sem)

    def test_normalize_list(self):
        runner = self._make_runner()
        data = [{"property_id": "a"}, {"property_id": "b"}]
        result = runner._normalize_result_data(data)
        assert len(result) == 2

    def test_normalize_dict_with_result_key(self):
        runner = self._make_runner()
        data = {"audit_items": [{"property_id": "a"}], "metadata": {}}
        result = runner._normalize_result_data(data)
        assert len(result) == 1
        assert result[0]["property_id"] == "a"

    def test_normalize_empty_list(self):
        runner = self._make_runner()
        assert runner._normalize_result_data([]) == []

    def test_normalize_dict_no_known_key(self):
        runner = self._make_runner()
        data = {"property_id": "a", "classification": "vulnerability"}
        result = runner._normalize_result_data(data)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# Response extraction
# ---------------------------------------------------------------------------


class TestResponseExtraction:
    """Test extracting results from assistant messages."""

    def _make_runner(self):
        config = get_phase_config("03")
        sem = asyncio.Semaphore(1)
        return APIRunner(config, sem)

    def test_extract_from_json_block(self):
        runner = self._make_runner()
        messages = [
            {"role": "user", "content": "audit"},
            {
                "role": "assistant",
                "content": 'Here are the results:\n```json\n{"audit_items": [{"property_id": "P1", "classification": "vulnerability"}]}\n```',
            },
        ]
        result = runner._extract_results_from_response(messages)
        assert result is not None
        assert len(result) == 1
        assert result[0]["property_id"] == "P1"

    def test_extract_from_raw_json(self):
        runner = self._make_runner()
        messages = [
            {
                "role": "assistant",
                "content": '{"audit_items": [{"property_id": "P2"}]}',
            },
        ]
        result = runner._extract_results_from_response(messages)
        assert result is not None
        assert result[0]["property_id"] == "P2"

    def test_extract_no_json(self):
        runner = self._make_runner()
        messages = [
            {"role": "assistant", "content": "No results found."},
        ]
        result = runner._extract_results_from_response(messages)
        assert result is None


# ---------------------------------------------------------------------------
# Runner interface compatibility
# ---------------------------------------------------------------------------


class TestRunnerInterface:
    """Verify APIRunner has the same interface as ClaudeRunner."""

    def test_constructor_signature(self):
        config = get_phase_config("03")
        sem = asyncio.Semaphore(1)
        cb = CircuitBreaker(config)

        runner = APIRunner(config, sem, circuit_breaker=cb)
        assert runner.config is config
        assert runner.semaphore is sem
        assert runner.circuit_breaker is cb

    def test_has_run_batch(self):
        config = get_phase_config("03")
        sem = asyncio.Semaphore(1)
        runner = APIRunner(config, sem)
        assert hasattr(runner, "run_batch")
        assert asyncio.iscoroutinefunction(runner.run_batch)

    def test_default_model(self):
        config = get_phase_config("03")
        sem = asyncio.Semaphore(1)
        runner = APIRunner(config, sem)
        assert runner.model  # Should have a default model
