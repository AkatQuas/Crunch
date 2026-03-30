#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import os.path
import pytest
import tempfile
import shutil

from src.crunch import ImageFile, REPLACE_ORIGINAL


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
# ImageFile with REPLACE_ORIGINAL flag tests
#
# ///////////////////////////////////////////////////////


def test_crunch_imagefile_obj_instantiation_with_replace_flag(monkeypatch):
    """Test that ImageFile uses temp file path when REPLACE_ORIGINAL is True."""
    # Set the global flag to True
    monkeypatch.setattr('src.crunch.REPLACE_ORIGINAL', True)

def test_crunch_imagefile_obj_finalize_replacement(monkeypatch):
    """Test that finalize_replacement replaces original with optimized file."""
    # Set the global flag to True
    monkeypatch.setattr('src.crunch.REPLACE_ORIGINAL', True)

    from src.crunch import ImageFile as ImageFileRebuilt

    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        original_file = os.path.join(tmpdir, "test.png")
        temp_file = os.path.join(tmpdir, "test-crunch.png")

        # Write some test data
        with open(original_file, 'wb') as f:
            f.write(b'original content')
        with open(temp_file, 'wb') as f:
            f.write(b'optimized content')

        imgfile = ImageFileRebuilt(original_file)
        # Manually set the post_filepath to our temp file
        imgfile.post_filepath = temp_file
        imgfile.post_size = len(b'optimized content')

        # Call finalize_replacement
        imgfile.finalize_replacement()

        # Check that original file is replaced with optimized content
        assert os.path.exists(original_file)
        assert not os.path.exists(temp_file)  # temp file should be removed
        with open(original_file, 'rb') as f:
            assert f.read() == b'optimized content'


def test_crunch_imagefile_obj_finalize_replacement_no_temp_file(monkeypatch):
    """Test that finalize_replacement handles missing temp file gracefully."""
    monkeypatch.setattr('src.crunch.REPLACE_ORIGINAL', True)

    from src.crunch import ImageFile as ImageFileRebuilt

    with tempfile.TemporaryDirectory() as tmpdir:
        original_file = os.path.join(tmpdir, "test.png")

        # Write original file only (no temp file)
        with open(original_file, 'wb') as f:
            f.write(b'original content')

        imgfile = ImageFileRebuilt(original_file)
        # post_filepath points to non-existent temp file
        imgfile.post_filepath = os.path.join(tmpdir, "nonexistent-crunch.png")

        # Should not raise, just should not do anything
        imgfile.finalize_replacement()

        # Original should still exist
        assert os.path.exists(original_file)
