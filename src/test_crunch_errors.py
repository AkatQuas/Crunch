#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import pytest

import src.crunch

# ///////////////////////////////////////////////////////
#
# pytest capsys capture tests
#    confirms capture of std output and std error streams
#
# ///////////////////////////////////////////////////////


def test_pytest_capsys(capsys):
    print("bogus text for a test")
    sys.stderr.write("more text for a test")
    out, err = capsys.readouterr()
    assert out == "bogus text for a test\n"
    assert out != "something else"
    assert err == "more text for a test"
    assert err != "something else"


# ///////////////////////////////////////////////////////
#
# Command line error tests
#
# ///////////////////////////////////////////////////////


def test_crunch_missing_argument_error(capsys):
    # Empty argv falls back to ["-h"], which shows help and exits with code 0
    with pytest.raises(SystemExit) as exit_info:
        src.crunch.main([])

    out, err = capsys.readouterr()
    assert "crunch is a command line executable" in out
    assert exit_info.value.code == 0


def test_crunch_missing_file_error(capsys):
    with pytest.raises(SystemExit) as exit_info:
        src.crunch.main(["bogusfile.png"])

    out, err = capsys.readouterr()
    assert len(err) > 0
    assert err.startswith("[ ! ]") is True
    assert exit_info.value.code == 1


def test_crunch_bad_filepath_error(capsys):
    with pytest.raises(SystemExit) as exit_info:
        src.crunch.main(["src/test_crunch_errors.py"])

    out, err = capsys.readouterr()
    assert len(err) > 0
    assert err.startswith("[ ! ]") is True
    assert exit_info.value.code == 1


# ///////////////////////////////////////////////////////
#
# Missing dependency error tests
#
# ///////////////////////////////////////////////////////

def test_crunch_missing_pngquant_error(capsys, monkeypatch):
    def fake_resolve(mode):
        return os.path.join("bogus", "pngquant"), src.crunch.ZOPFLIPNG_CLI_PATH

    monkeypatch.setattr(src.crunch, "resolve_dependency_paths", fake_resolve)
    testpath = os.path.join("testfiles", "robot.png")
    with pytest.raises(SystemExit) as exit_info:
        src.crunch.main([testpath])

    out, err = capsys.readouterr()
    assert err.startswith("[ ! ]") is True
    assert exit_info.value.code == 1


def test_crunch_missing_zopflipng_error(capsys, monkeypatch):
    def fake_resolve(mode):
        return src.crunch.PNGQUANT_CLI_PATH, os.path.join("bogus", "zopflipng")

    monkeypatch.setattr(src.crunch, "resolve_dependency_paths", fake_resolve)
    testpath = os.path.join("testfiles", "robot.png")
    with pytest.raises(SystemExit) as exit_info:
        src.crunch.main([testpath])

    out, err = capsys.readouterr()
    assert err.startswith("[ ! ]") is True
    assert exit_info.value.code == 1


# ///////////////////////////////////////////////////////
#
# Multiprocessing.Pool error tests
#
# ///////////////////////////////////////////////////////

def test_crunch_exception_multiprocessing_pool(capsys, monkeypatch):
    def raise_ioerror():
        raise IOError
    monkeypatch.setattr(src.crunch, 'optimize_png', raise_ioerror)
    testpath1 = os.path.join("testfiles", "robot.png")
    testpath2 = os.path.join("testfiles", "robot.png")
    with pytest.raises(SystemExit) as exit_info:
        src.crunch.main([testpath1, testpath2])

    out, err = capsys.readouterr()
    assert "[ ! ]" in err
    assert exit_info.value.code == 1


# ///////////////////////////////////////////////////////
#
# --output / -o flag tests
#
# ///////////////////////////////////////////////////////


def test_output_flag_not_allowed_with_gui(capsys):
    """Test that --output flag is not allowed with --gui mode."""
    with pytest.raises(SystemExit) as exit_info:
        src.crunch.main(["--gui", "-o", "out.png", "testfiles/robot.png"])

    out, err = capsys.readouterr()
    assert "--output / -o flag is not supported in GUI or Service mode" in err
    assert exit_info.value.code == 1


def test_output_flag_not_allowed_with_service(capsys):
    """Test that --output flag is not allowed with --service mode."""
    with pytest.raises(SystemExit) as exit_info:
        src.crunch.main(["-o", "out.png", "--service", "testfiles/robot.png"])

    out, err = capsys.readouterr()
    assert "--output / -o flag is not supported in GUI or Service mode" in err
    assert exit_info.value.code == 1


def test_replace_flag_removed(capsys):
    """Test that removed --replace flag reports a helpful error."""
    with pytest.raises(SystemExit) as exit_info:
        src.crunch.main(["--replace", "testfiles/robot.png"])

    out, err = capsys.readouterr()
    assert "--replace / -r has been removed" in err
    assert exit_info.value.code == 1


def test_replace_short_flag_removed(capsys):
    """Test that removed -r flag reports a helpful error."""
    with pytest.raises(SystemExit) as exit_info:
        src.crunch.main(["-r", "testfiles/robot.png"])

    out, err = capsys.readouterr()
    assert "--replace / -r has been removed" in err
    assert exit_info.value.code == 1


def test_output_flag_missing_argument(capsys):
    """Test that --output without a path reports an error."""
    with pytest.raises(SystemExit) as exit_info:
        src.crunch.main(["-o"])

    out, err = capsys.readouterr()
    assert "Missing argument for -o" in err
    assert exit_info.value.code == 1


def test_output_flag_not_allowed_with_multiple_files(capsys, monkeypatch):
    """Test that --output is rejected when multiple input files are provided."""
    with pytest.raises(SystemExit) as exit_info:
        src.crunch.main(
            ["-o", "out.png", "testfiles/robot.png", "testfiles/cat.png"]
        )

    out, err = capsys.readouterr()
    assert "--output / -o can only be used with a single input file" in err
    assert exit_info.value.code == 1
