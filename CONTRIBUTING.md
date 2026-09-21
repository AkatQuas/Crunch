# Contributing to Crunch

## Getting Started

Contributions are warmly welcomed! This guide outlines how to set up your development environment and submit changes.

### Prerequisites

- **Operating System**: macOS or Linux (for development)
- **Python**: 3.12+ (see `tox.ini`)
- **[uv](https://docs.astral.sh/uv/)**: creates `.venv` and installs Python dependencies via the Makefile
- **Rust**: 1.63+ (for pngquant v3, see https://rustup.rs)
- **Build Tools**: make, git, standard C/C++ compiler (for zopfli)
- **pngcheck** (macOS): `brew install pngcheck`

### Development Setup

1. **Clone the repository**:

   ```bash
   git clone https://github.com/AkatQuas/Crunch.git
   cd Crunch
   ```

2. **Install Python dependencies** (creates `.venv` if needed):

   ```bash
   make install-python-deps
   ```

3. **Install Git pre-commit hooks** (recommended):

   ```bash
   make install-hooks
   ```

   This configures Git to run `.githooks/pre-commit` before each commit. The hook runs:

   - `make lint-python` — `black --check` on `src/crunch.py`
   - `make lint-shell` — shellcheck on `src/*.sh`

   Hooks are per-clone (`git config core.hooksPath .githooks`). Run `make install-hooks` once after cloning. Full tests (`make test`) are not run on commit; run them before opening a PR.

4. **Install system dependencies** (macOS):

   ```bash
   brew install pngcheck
   ```

5. **Build pngquant and zopflipng** (required for integration tests and local `crunch` usage):

   ```bash
   make build-dependencies
   make install-executable
   ```

   `build-dependencies` runs `src/install-dependencies.sh` and installs binaries to `~/.local/bin/`.

6. **Verify installation**:

   ```bash
   crunch --version
   make test-python
   ```

### macOS GUI app and releases

The GUI app bundle lives in `bin/Crunch.app`. Source changes go in `src/`; sync into the bundle before packaging:

```bash
make sync-app
```

**Local DMG** (development):

```bash
brew install create-dmg   # or: npx create-dmg
make build-macos-installer
```

**Published releases** (maintainers): bump `VERSION` in `src/crunch.py`, add a `CHANGELOG.md` section, push to `main`, then run the **Release macOS GUI** workflow in GitHub Actions. The workflow runs tests, `make sync-app`, builds the DMG, creates tag `v{VERSION}`, and uploads `Crunch-Installer.dmg` to GitHub Releases.

Platypus is no longer required for day-to-day development; the app shell in `bin/Crunch.app` is updated in-repo and via `make sync-app`.

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
make test
```

Individual test targets:

```bash
make lint                    # black --check + shellcheck (same as pre-commit)
make lint-python             # black --check only
make lint-shell              # shellcheck only
make test-python             # tox (pytest) + black --check
make test-shell              # shellcheck on src/*.sh
make test-valid-png-output   # verify PNG output with pngcheck
```

With `make install-hooks`, `lint-python` and `lint-shell` run automatically on every `git commit`. To commit without hooks (emergency only):

```bash
git commit --no-verify
```

### Benchmarking

Compare optimization results:

```bash
$ make benchmark
```

## Pull Request Guidelines

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/my-feature`
3. **Run** `make install-hooks` and `make install-python-deps` if you have not already
4. **Make** your changes with clear commit messages (pre-commit runs `lint-python` and `lint-shell`)
5. **Test** your changes: `make test`
6. **Submit** a pull request against `main`

### PR Requirements

- [ ] `make lint` passes (also enforced by pre-commit when hooks are installed)
- [ ] `make test` passes before merge when changes affect runtime behavior
- [ ] Full suite passes (`make test`) when integration tests are relevant
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
