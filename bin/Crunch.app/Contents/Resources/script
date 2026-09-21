#!/bin/sh

# //////////////////////////////////////////////////////////
#
# crunch-gui.sh
#  A shell script that executes Crunch PNG optimization
#       for the Crunch macOS GUI application
#  Copyright 2018 Christopher Simpkins and contributors
#  MIT License
#
#  Source: https://github.com/chrissimpkins/Crunch
#
#  Note: this file is not intended for direct execution
#        on the command line
#
# ///////////////////////////////////////////////////////////

cd "$(dirname "$0")" || exit 1

# Platypus streams script stdout into the WebView. After a long-running
# crunch.py call, concatenated HTML documents are not reliably applied;
# force WebKit to load the next page from the app Resources directory.
show_page() {
    printf '%s\n' \
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\"><script>location.replace('$1');</script></head><body></body></html>"
}

# UNCOMMENT FOR TESTING ONLY
# python crunch.py --gui "$@"
# exit 0

# Message on application open (no arguments passed to script on initial open)
if [ $# -eq 0 ]; then
    cat waiting.html
    exit 0
fi

cat execution.html

if ./crunch.py --gui "$@" >>/dev/null 2>>"${HOME}/.local/state/crunch/crunch.log"; then
    show_page "complete-success.html"
    # Stay alive while success page plays and redirects to waiting.html
    sleep 3
    exit 0
else
    show_page "complete-error.html"
    sleep 3
    exit 1
fi
