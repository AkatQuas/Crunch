#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import os.path
import pytest
import tempfile
import shutil

from src.crunch import ImageFile


def test_crunch_imagefile_obj_instantiation():
    imgfile = ImageFile(os.path.join("testfiles", "robot.png"))
    assert imgfile.pre_filepath == os.path.join("testfiles", "robot.png")
    assert imgfile.post_filepath == os.path.join("testfiles", "robot-crunch.png")
    assert imgfile.pre_size > 0


def test_crunch_imagefile_obj_get_post_filesize_method():
    imgfile = ImageFile(os.path.join("testfiles", "robot.png"))
    # Create the post file for testing
    shutil.copy(imgfile.pre_filepath, imgfile.post_filepath)
    imgfile.get_post_filesize()
    assert imgfile.post_size > 0
    # Cleanup
    os.remove(imgfile.post_filepath)


def test_crunch_imagefile_obj_get_compression_percent_method():
    imgfile = ImageFile(os.path.join("testfiles", "robot.png"))
    imgfile.pre_size = 100
    imgfile.post_size = 10
    percent = imgfile.get_compression_percent()
    assert percent == float(10)


# ///////////////////////////////////////////////////////
#
# ImageFile finalize_output tests
#
# ///////////////////////////////////////////////////////


def test_crunch_imagefile_obj_finalize_output_replace_original(monkeypatch):
    """Test that finalize_output replaces original with optimized file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_file = os.path.join(tmpdir, "test.png")
        temp_file = os.path.join(tmpdir, "test-crunch.png")

        with open(original_file, 'wb') as f:
            f.write(b'original content')
        with open(temp_file, 'wb') as f:
            f.write(b'optimized content')

        monkeypatch.setattr(
            "src.crunch.OUTPUT_PATHS", {original_file: None}
        )

        imgfile = ImageFile(original_file)
        imgfile.post_filepath = temp_file
        imgfile.post_size = len(b'optimized content')
        imgfile.finalize_output()

        assert os.path.exists(original_file)
        assert not os.path.exists(temp_file)
        with open(original_file, 'rb') as f:
            assert f.read() == b'optimized content'


def test_crunch_imagefile_obj_finalize_output_to_custom_path(monkeypatch):
    """Test that finalize_output writes to a custom output path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_file = os.path.join(tmpdir, "test.png")
        temp_file = os.path.join(tmpdir, "test-crunch.png")
        output_file = os.path.join(tmpdir, "out", "optimized.png")

        with open(original_file, 'wb') as f:
            f.write(b'original content')
        with open(temp_file, 'wb') as f:
            f.write(b'optimized content')

        monkeypatch.setattr(
            "src.crunch.OUTPUT_PATHS", {original_file: output_file}
        )

        imgfile = ImageFile(original_file)
        imgfile.post_filepath = temp_file
        imgfile.post_size = len(b'optimized content')
        imgfile.finalize_output()

        assert os.path.exists(original_file)
        assert not os.path.exists(temp_file)
        assert os.path.exists(output_file)
        with open(original_file, 'rb') as f:
            assert f.read() == b'original content'
        with open(output_file, 'rb') as f:
            assert f.read() == b'optimized content'


def test_crunch_imagefile_obj_finalize_output_no_temp_file(monkeypatch):
    """Test that finalize_output handles missing temp file gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_file = os.path.join(tmpdir, "test.png")

        with open(original_file, 'wb') as f:
            f.write(b'original content')

        monkeypatch.setattr(
            "src.crunch.OUTPUT_PATHS", {original_file: None}
        )

        imgfile = ImageFile(original_file)
        imgfile.post_filepath = os.path.join(tmpdir, "nonexistent-crunch.png")
        imgfile.finalize_output()

        assert os.path.exists(original_file)
