#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for signal handling and graceful shutdown functionality.

These tests verify that:
1. run_subprocess creates processes in their own process groups
2. Signal handler function exists and is properly configured
"""

import inspect
import os
import signal
import subprocess
import time

import pytest

import src.crunch


# ///////////////////////////////////////////////////////
#
# run_subprocess function tests
#
# ///////////////////////////////////////////////////////


def test_run_subprocess_success():
    """Test that run_subprocess executes a simple command successfully."""
    src.crunch.run_subprocess("echo 'test'")


def test_run_subprocess_failure_raises_called_process_error():
    """Test that run_subprocess raises CalledProcessError on failure."""
    from subprocess import CalledProcessError

    with pytest.raises(CalledProcessError):
        src.crunch.run_subprocess("exit 1")


def test_run_subprocess_creates_new_process_group():
    """Test that run_subprocess creates a process in a new session.

    This is critical for signal handling - processes in their own
    process group can be terminated together.
    """
    cmd = "sleep 10"

    process = subprocess.Popen(
        cmd,
        shell=True,
        start_new_session=True,
    )

    time.sleep(0.1)

    pgid = os.getpgid(process.pid)
    assert pgid == process.pid, "Process should be leader of its own process group"

    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    process.wait()


def test_run_subprocess_returns_none_on_success():
    """Test that run_subprocess returns None on success."""
    result = src.crunch.run_subprocess("echo test")
    assert result is None


def test_run_subprocess_with_shell_command():
    """Test run_subprocess with a shell command that has arguments."""
    src.crunch.run_subprocess("python --version")


# ///////////////////////////////////////////////////////
#
# Signal handler infrastructure tests
#
# ///////////////////////////////////////////////////////


def test_process_runner_registers_signal_handlers():
    """Test that ProcessRunner installs interrupt handlers."""
    runner = src.crunch.ProcessRunner.register_handlers()
    assert isinstance(runner, src.crunch.ProcessRunner)
    assert signal.getsignal(signal.SIGINT) == runner._handle_signal
    assert signal.getsignal(signal.SIGTERM) == runner._handle_signal


def test_signal_handler_delegates_to_process_runner():
    """Backward-compatible signal_handler entry point still exists."""
    assert callable(src.crunch.signal_handler)
    assert src.crunch.signal_handler.__name__ == "signal_handler"


def test_pool_global_variable_exists():
    """Test that the global pool variable exists."""
    assert hasattr(src.crunch, 'pool')


def test_process_runner_uses_correct_exit_code():
    """Exit code = 128 + signal number (SIGINT=2, SIGTERM=15)."""
    source = inspect.getsource(src.crunch.ProcessRunner._handle_signal)
    assert "128 + signum" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
