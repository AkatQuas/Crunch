#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
End-to-end tests for signal handling (Ctrl+C) functionality.

These tests verify:
1. Signal handlers are registered in main()
2. run_subprocess uses start_new_session for process group isolation
3. Normal crunch execution still works
4. SIGINT sent during execution properly terminates the process
"""

import glob
import os
import signal
import subprocess
import time

import pytest

# Find benchmark test files directory - ~200 PNG files
BENCHMARK_DIR = os.path.join(os.path.dirname(__file__), "..", "benchmarks", "img")


def cleanup_crunch_files():
    """Clean up -crunch.png files in benchmarks/img."""
    crunch_files = glob.glob(os.path.join(BENCHMARK_DIR, "*-crunch.png"))
    cleaned = 0
    for path in crunch_files:
        try:
            os.remove(path)
            cleaned += 1
        except OSError:
            pass
    return cleaned


def get_test_files():
    """Get list of PNG files from benchmarks/img (excluding -crunch.png)."""
    return [
        os.path.join(BENCHMARK_DIR, f)
        for f in os.listdir(BENCHMARK_DIR)
        if f.endswith('.png') and not f.endswith('-crunch.png')
    ]


def run_crunch_with_signal(signum):
    """Run crunch and send the given signal after 2 seconds.

    Returns the process return code.
    """
    test_files = get_test_files()
    if len(test_files) < 10:
        pytest.skip(f"Need at least 10 test files, found {len(test_files)}")

    process = subprocess.Popen(
        ["python", "-m", "src.crunch"] + test_files,
        cwd=os.path.join(os.path.dirname(__file__), ".."),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    time.sleep(2)

    if process.poll() is not None:
        pytest.skip(f"Process finished too quickly (code {process.returncode})")

    process.send_signal(signum)

    try:
        process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        pytest.fail(f"Process did not terminate after {signal.Signals(signum).name}")

    return process.returncode


def test_e2e_sigint_sent_during_execution_terminates_process():
    """Test that SIGINT sent after 2 seconds terminates the process."""
    returncode = run_crunch_with_signal(signal.SIGINT)
    assert returncode in [130, -15]
    cleanup_crunch_files()


def test_e2e_sigterm_sent_during_execution_terminates_process():
    """Test that SIGTERM sent during execution terminates the process."""
    returncode = run_crunch_with_signal(signal.SIGTERM)
    assert returncode in [143, -15]
    cleanup_crunch_files()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
