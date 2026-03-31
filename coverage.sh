#!/bin/sh

[ -f .venv/bin/activate ] && . .venv/bin/activate
coverage run --include="src/crunch.py" -m pytest src && \
coverage report -m
