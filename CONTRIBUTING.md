# Contributing to Crunch

## Getting Started

Contributions are warmly welcomed! This guide outlines how to set up your development environment and submit changes.

### Prerequisites

- **Operating System**: macOS or Linux (for development)
- **Python**: 3.x (Python 2 support removed in v5.0.0)
- **Rust**: 1.63+ (for pngquant v3, see https://rustup.rs)
- **Build Tools**: make, git, standard C/C++ compiler (for zopfli)
- **Testing**: tox, flake8, shellcheck-py (installed via pip), pngcheck (installed via Homebrew)
- **Platypus** (for macOS GUI app development): https://sveinbjorn.org/platypus

### Development Setup

1. **Clone the repository**:

   ```bash
   $ git clone https://github.com/AkatQuas/Crunch.git
   $ cd Crunch
   ```

2. **Create a Python virtual environment** (recommended):

   ```bash
   $ python3 -m venv .venv
   $ source .venv/bin/activate
   ```

3. **Install Python testing dependencies**:

   ```bash
   $ pip install -r requirements.txt
   ```

4. **Install system dependencies**:

   ```bash
   $ brew install pngcheck
   ```

5. **Build project dependencies** (pngquant v3 and zopflipng):

   ```bash
   $ make build-dependencies
   ```

   This runs `src/install-dependencies.sh` which builds:
   - **pngquant v3** - built using Rust/Cargo (requires Rust 1.63+)
   - **zopflipng** - built using Make

6. **Verify installation**:
   ```bash
   $ crunch --version
   ```

### Building the macOS GUI Application

The macOS GUI application is built using **Platypus** with the `profile/Crunch.platypus` configuration file. To rebuild the app:

1. Install Platypus: `brew install platypus` or download from https://sveinbjorn.org/platypus
2. Load profile `profile/Crunch.platypus` into Platypus
3. Click "Create App" to generate `Crunch.app`

After `Crunch.app` is created, you can build the DMG installer:

```bash
$ make build-macos-icns      # Build macOS icon set (optional)
$ make build-macos-installer # Create DMG installer from Crunch.app
```

**Note**: The `create-dmg` tool is required to build the DMG installer.

- For local development (`make build-macos-installer`), use: https://github.com/sindresorhus/create-dmg
- For distribution builds (`make dist`), use: https://github.com/create-dmg/create-dmg

Install via:

```bash
$ npm install -g create-dmg
```

## Making Changes

### Code Style

- **Python**: Follow PEP 8, formatted with `black`

  ```bash
  $ black src/crunch.py
  ```

- **Shell**: Use shellcheck for validation
  ```bash
  $ make test-shell
  ```

### Testing

Run the full test suite:

```bash
$ make test
```

Individual test targets:

```bash
$ make test-python        # Python unit tests + flake8
$ make test-shell         # shellcheck validation
$ make test-valid-png-output  # Verify PNG output validity
```

### Benchmarking

Compare optimization results:

```bash
$ make benchmark
```

## Pull Request Guidelines

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/my-feature`
3. **Make** your changes with clear commit messages
4. **Test** your changes: `make test`
5. **Submit** a pull request against `master`

### PR Requirements

- [ ] All tests pass (`make test`)
- [ ] Code formatted with `black` (Python)
- [ ] Shell scripts pass `shellcheck`
- [ ] New features documented
- [ ] No regression in benchmark results (if applicable)

## Issue Reporting

Use the [GitHub issue tracker](https://github.com/AkatQuas/Crunch/issues/new/choose) to report bugs or request features. For bugs, include:

- Operating system and version
- Crunch version (`crunch --version`)
- Steps to reproduce
- Expected vs actual behavior
- Sample PNG file (if possible)

## Documentation

- Update `ARCHITECTURE.md` for structural changes
- Update `docs/*.md` for user-facing documentation

## License

By contributing to Crunch, you agree that your contributions will be licensed under the [MIT License](LICENSE.md).
