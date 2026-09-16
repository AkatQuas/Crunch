#!/usr/bin/env python3

# ----------------------------------------
#
# Copyright (c) 2019 Christopher Simpkins
# MIT license
#
# ---------------------------------------


import glob
import os

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(SCRIPT_DIR, "img")
ORIGINALS_DIR = os.path.join(IMG_DIR, ".originals")

# Glob PNG files in the img subdirectory
paths = sorted(glob.glob(os.path.join(IMG_DIR, "*.png")))

percent_list = []
pre_size_list = []
post_size_list = []

for post_path in paths:
    basename = os.path.basename(post_path)
    pre_path = os.path.join(ORIGINALS_DIR, basename)

    assert os.path.exists(pre_path), (
        f"Missing original backup for {basename}. "
        f"Run benchmarks via `make benchmark` so originals are saved first."
    )

    pre_size = os.path.getsize(pre_path)
    post_size = os.path.getsize(post_path)
    percent_size = (post_size / pre_size) * 100

    percent_list.append(percent_size)
    pre_size_list.append(pre_size)
    post_size_list.append(post_size)

    print(f"{post_path}: {percent_size:.2f}%")

mean = sum(percent_list) / len(percent_list)
total_initial_size = sum(pre_size_list)
total_final_size = sum(post_size_list)
delta = total_initial_size - total_final_size

print(f"\nInitial:\t{total_initial_size:>8} B")
print(f"Final:  \t{total_final_size:>8} B")
print(f"Delta: -{delta} B")
print(f"Mean: {mean:.2f}%")
try:
    import numpy as np

    a = np.array(percent_list)
    stdev = np.std(a, dtype=np.float64)
    print(f"SD: {stdev:.2f}%")
except Exception:
    pass
