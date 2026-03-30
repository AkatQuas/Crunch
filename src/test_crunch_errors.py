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
    with pytest.raises(SystemExit) as exit_info:
        src.crunch.main([])
    
    out, err = capsys.readouterr()
    assert len(err) > 0
    assert err.startswith("[ ! ]") is True
    assert exit_info.value.code == 1


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
    def return_bogus_path():
        return os.path.join("bogus", "pngquant")
    monkeypatch.setattr(src.crunch, 'get_pngquant_path', return_bogus_path)
    testpath = os.path.join("testfiles", "robot.png")
    with pytest.raises(SystemExit) as exit_info:
        src.crunch.main([testpath])

    out, err = capsys.readouterr()
    assert err.startswith("[ ! ]") is True
    assert exit_info.value.code == 1
    

def test_crunch_missing_zopflipng_error(capsys, monkeypatch):
    def return_bogus_path():
        return os.path.join("bogus", "zopflipng")
    monkeypatch.setattr(src.crunch, 'get_zopflipng_path', return_bogus_path)
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
# --replace / -r flag tests
#
# ///////////////////////////////////////////////////////


def test_replace_flag_must_be_first(capsys):
    """Test that --replace flag must come first (before --gui/--service)."""
    # When --gui comes first, --replace after it is treated as a file path
    with pytest.raises(SystemExit) as exit_info:
        src.crunch.main(["--gui", "--replace", "testfiles/robot.png"])

    out, err = capsys.readouterr()
    # Should fail with invalid file path error, not the replace error
    assert "does not appear to be a valid path to a PNG file" in err


def test_replace_flag_not_allowed_with_service(capsys):
    """Test that --replace flag is not allowed with --service mode when it comes first."""
    with pytest.raises(SystemExit) as exit_info:
        src.crunch.main(["--replace", "--service", "testfiles/robot.png"])

    out, err = capsys.readouterr()
    assert "--replace / -r flag is not supported in GUI or Service mode" in err
    assert exit_info.value.code == 1


def test_replace_short_flag_with_gui_after(capsys):
    """Test that -r flag is not allowed with --gui when gui comes after."""
    with pytest.raises(SystemExit) as exit_info:
        src.crunch.main(["-r", "--gui", "testfiles/robot.png"])

    out, err = capsys.readouterr()
    assert "--replace / -r flag is not supported in GUI or Service mode" in err
    assert exit_info.value.code == 1


def test_replace_flag_sets_global_variable(monkeypatch):
    """Test that --replace flag sets REPLACE_ORIGINAL to True."""
    # Reset the global variable before test
    monkeypatch.setattr(src.crunch, 'REPLACE_ORIGINAL', False)

    # Mock the dependency paths to avoid missing dependency errors
    monkeypatch.setattr(src.crunch, 'get_pngquant_path', lambda: "bogus_pngquant")
    monkeypatch.setattr(src.crunch, 'get_zopflipng_path', lambda: "bogus_zopflipng")

    with pytest.raises(SystemExit):
        src.crunch.main(["--replace", "testfiles/robot.png"])

    assert src.crunch.REPLACE_ORIGINAL is True


def test_replace_short_flag_sets_global_variable(monkeypatch):
    """Test that -r flag sets REPLACE_ORIGINAL to True."""
    # Reset the global variable before test
    monkeypatch.setattr(src.crunch, 'REPLACE_ORIGINAL', False)

    # Mock the dependency paths to avoid missing dependency errors
    monkeypatch.setattr(src.crunch, 'get_pngquant_path', lambda: "bogus_pngquant")
    monkeypatch.setattr(src.crunch, 'get_zopflipng_path', lambda: "bogus_zopflipng")

    with pytest.raises(SystemExit):
        src.crunch.main(["-r", "testfiles/robot.png"])

    assert src.crunch.REPLACE_ORIGINAL is True
