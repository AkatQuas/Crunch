#!/bin/sh

. .venv/bin/activate && \
coverage run --include="src/crunch.py" -m pytest src && \
coverage report -m
