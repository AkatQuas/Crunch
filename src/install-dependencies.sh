#!/bin/sh

set -e

# ==================================================================
#  install-dependencies-v3.sh
#    Install Crunch optimization binary dependencies
#    Uses pngquant v3 (Cargo-based build)
#
#   Copyright 2018 Christopher Simpkins
#   MIT License
#
#   Source Repository: https://github.com/AkatQuas/Crunch
# ==================================================================

PNGQUANT_BUILD_DIR="/tmp/pngquant"
PNGQUANT_EXE="$HOME/.local/bin/pngquant"
ZOPFLIPNG_BUILD_DIR="/tmp/zopfli"
ZOPFLIPNG_EXE="$HOME/.local/bin/zopflipng"
# SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

# https://github.com/kornelski/pngquant/tags
PNGQUANT_VERSION_TAG="3.0.3"
# https://github.com/chrissimpkins/zopfli/tags
ZOPFLIPNG_VERSION_TAG="v2.3.0"

mkdir -p "$HOME/.local/bin"

# ////////////////////
#
#  BUILD pngquant (v3 using Cargo)
#
# ////////////////////

# Check for Rust installation (required for pngquant v3)
if ! command -v rustc > /dev/null 2>&1; then
    printf "[ERROR]: Rust is required to build pngquant v3.\n"
    printf "Please install from https://rustup.rs\n"
    exit 1
fi

# Clone pngquant source (shallow clone with specific tag)
if [ -d "$PNGQUANT_BUILD_DIR" ]; then
    rm -rf "$PNGQUANT_BUILD_DIR"
fi

git clone --depth=1 --branch=$PNGQUANT_VERSION_TAG --recursive https://github.com/kornelski/pngquant.git "$PNGQUANT_BUILD_DIR"
cd "$PNGQUANT_BUILD_DIR" || exit 1
git submodule update --depth=1

# Build pngquant using Cargo (dependencies are handled automatically by Cargo)
# LCMS2_STATIC=1 forces static linking of Little CMS library
LCMS2_STATIC=1 cargo build --release

mv target/release/pngquant "$PNGQUANT_EXE"

# /////////////////
#
# BUILD zopflipng
#
# /////////////////

# Clone zopfli source (shallow clone with specific tag)
if [ -d "$ZOPFLIPNG_BUILD_DIR" ]; then
    rm -rf "$ZOPFLIPNG_BUILD_DIR"
fi

git clone --depth=1 --branch="$ZOPFLIPNG_VERSION_TAG" https://github.com/chrissimpkins/zopfli.git "$ZOPFLIPNG_BUILD_DIR"
cd "$ZOPFLIPNG_BUILD_DIR" || exit 1

make zopflipng
mv zopflipng "$ZOPFLIPNG_EXE"

# ///////////////////////
#
# Tests and user reports
#
# ///////////////////////

# Test for expected install file paths and report outcome to user

printf "\n\n------------------------------\nTesting Builds...\n------------------------------\n"

printf "[?] %s test...\n\n" "$PNGQUANT_EXE"
if [ -f "$PNGQUANT_EXE" ]; then
    "$PNGQUANT_EXE" --version
else
    printf "[ERROR]: pngquant executable was not found on the expected path: %s\n" "$PNGQUANT_EXE"
    printf "The install attempt did not complete successfully.  Please report this error.\n"
    exit 1
fi

printf "\n[?] %s test...\n\n" "$ZOPFLIPNG_EXE"
if [ -f "$ZOPFLIPNG_EXE" ]; then
    "$ZOPFLIPNG_EXE" --version
else
    printf "[ERROR]: zopflipng executable was not found on the expected path: %s\n" "$PNGQUANT_EXE"
    printf "The install attempt did not complete successfully.  Please report this error."
    exit 1
fi

printf "\n\n------------------------------\nEnd Tests\n------------------------------\n"

printf "\n---------- BUILD PATHS ----------\n"
printf "[*] pngquant path: %s\n" "$PNGQUANT_EXE"
printf "[*] zopflipng path: %s\n" "$ZOPFLIPNG_EXE"
printf "\n\n[OK] Dependency installs complete.\n"
exit 0
