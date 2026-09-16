# Architecture

## Overview

Crunch is a lossy PNG image optimization tool that combines two compression techniques: pngquant (lossy color reduction) and zopflipng (zopfli DEFLATE compression). The project provides three user interfaces: a command-line executable, a native macOS GUI application, and a macOS Finder right-click service.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Crunch Project                           │
├─────────────────────────────────────────────────────────────────┤
│  User Interfaces                                                │
│  ┌─────────────────┐  ┌──────────────────┐  ┌───────────────┐  │
│  │  CLI Executable │  │  macOS GUI App   │  │ macOS Service │  │
│  │   (crunch)      │  │  (Platypus)      │  │ (Workflow)    │  │
│  └────────┬────────┘  └────────┬─────────┘  └───────┬───────┘  │
│           │                    │                     │          │
│           ▼                    ▼                     ▼          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              crunch.py (Core Optimization Engine)        │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌────────────────┐   │   │
│  │  │ ImageFile   │  │ optimize_   │  │ multiprocessing│   │   │
│  │  │ Class       │  │ png()       │  │ Pool           │   │   │
│  │  └─────────────┘  └─────────────┘  └────────────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│           ┌────────────────┴────────────────┐                  │
│           ▼                                 ▼                  │
│  ┌─────────────────┐              ┌─────────────────┐          │
│  │    pngquant     │              │    zopflipng    │          │
│  │  (Lossy Stage)  │──────────────│ (Compression)   │          │
│  └─────────────────┘              └─────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Core Engine (Python)

**crunch.py** - The central Python module that handles:

- **Argument parsing and validation** - CLI option handling (`-o` / `--output`), PNG file validation, folder expansion
- **Output file handling** - In-place replacement in CLI mode; `-crunch` suffix files in GUI/service modes
- **Image processing pipeline** - Two-stage optimization (pngquant → zopflipng)
- **Parallel processing** - Uses Python's `multiprocessing.Pool` for batch optimization
- **Logging** - File-based logging for GUI and service modes

Key classes and functions:

- `ImageFile` - Represents a PNG file with pre/post optimization paths and sizes; `finalize_output()` writes the result in CLI mode
- `optimize_png()` - Main optimization function that chains pngquant and zopflipng
- `parse_cli_options()` / `build_output_paths()` - Parse `-o` and map input files to output destinations
- `is_valid_png()` - Validates PNG file signatures
- `get_pngquant_path()` / `get_zopflipng_path()` - Resolves dependency paths based on execution context

Global state used across worker processes:

- `GUI_MODE` - Set from `main()` argv; distinguishes CLI from `--gui` / `--service` execution
- `OUTPUT_PATHS` - Maps each input path to an output path (`None` means replace original in CLI mode)

### 2. Optimization Pipeline

```
Original PNG → pngquant (lossy) → zopflipng (deflate) → Optimized PNG
                              │
                              ▼
                    Quality: 80-98
                    --skip-if-larger
                    --force --strip
                    --speed 1
```

**pngquant stage:**

- Reduces color palette to 256 colors max
- Quality range: 80-98 (min-max)
- Skips if result is larger than original
- Strips metadata
- Uses speed level 1 (best compression)

**zopflipng stage:**

- Applies zopfli DEFLATE compression
- Uses filter=0 for quantized files
- Uses lossy_transparent for non-quantized files

### 3. User Interfaces

#### Command-Line Executable

- Python script installed to `~/.local/bin/crunch`
- Dependencies: pngquant at `~/.local/bin/pngquant`, zopflipng at `~/.local/bin/zopflipng`
- Supports parallel processing with automatic CPU core detection
- **Default output**: replaces each input PNG in place
- **Optional output**: `-o` / `--output` writes a single input file elsewhere (original preserved)
- **Folder input**: a single directory argument expands to all PNG files under it (each replaced in place)

#### macOS GUI Application (Platypus)

The Crunch macOS GUI application is created using **Platypus**, a macOS app wrapper that creates native applications from scripts. The application is configured via the `Crunch.platypus` profile file located in the `profile/` directory.

**Platypus Configuration:**

- **Bundle Identifier**: `com.akatquas.Crunch`
- **Interface Type**: Web View (HTML-based UI)
- **Script Path**: `src/crunch-gui.sh` (executed via `/bin/sh`)
- **Icon**: `img/CrunchIcon.icns`
- **Remains Running**: Yes (waits for dropped files)
- **Droppable**: Yes (accepts dropped PNG files)
- **Accepts Files**: Yes
- **Output**: writes `[original filename]-crunch.png` alongside each original (original preserved)

#### macOS Finder Service

- Right-click "Crunch Image(s)" service
- Processes selected PNG files from Finder
- Installed as `~/Library/Services/Crunch Image(s).workflow`
- **Output**: writes `[original filename]-crunch.png` alongside each original (original preserved)

### 4. Build System

**Makefile targets:**

- `build-dependencies` - Compiles pngquant and zopflipng from source
- `install-executable` - Installs CLI to `/usr/local/bin`
- `install-macos-service` - Installs Finder service
- `build-macos-icns` - Builds macOS icon set
- `build-macos-installer` - Creates DMG installer from existing `Crunch.app` (requires `create-dmg`)
- `test-valid-png-output` - Validates optimized PNG output with pngcheck (uses a temp directory to avoid modifying fixtures)

**Build Workflow:**

1. **Create Crunch.app**: Use Platypus to load `profile/Crunch.platypus` and generate the app
2. **Build icon set** (optional): `make build-macos-icns`
3. **Create DMG installer**: `make build-macos-installer` (requires `Crunch.app` in `bin/` directory)

> **Note**: The `create-dmg` tool is required to build the DMG installer:
>
> - For local development (`make build-macos-installer`): use https://github.com/sindresorhus/create-dmg
> - For distribution builds (`make dist`): use https://github.com/create-dmg/create-dmg

### 5. macOS Application Bundle Structure (Platypus)

The Crunch.platypus profile defines how Platypus packages the application. When built, it creates:

```
Crunch.app/
├── Contents/
│   ├── Info.plist              # Generated from Platypus profile
│   ├── MacOS/
│   │   └── ScriptExec          # Platypus executable (/usr/local/share/platypus/ScriptExec)
│   ├── Resources/
│   │   ├── crunch-gui.sh       # Main script (defined in ScriptPath)
│   │   ├── crunch.py           # Python engine
│   │   ├── pngquant            # Bundled binary dependency
│   │   ├── zopflipng           # Bundled binary dependency
│   │   ├── *.html              # GUI templates
│   │   ├── animations/         # GIF animations
│   │   └── Credits.html
│   └── PkgInfo
```

The `Crunch.platypus` profile file is the configuration source that defines this structure, including:

- All bundled files (pngquant, zopflipng, HTML, icons, animations)
- Interpreter path (`/bin/sh`) for script execution
- Droppable file types (`public.item`, `public.folder`)
- Status item configuration for menu bar integration

## Execution Contexts

The application detects execution context to resolve dependency paths:

| Context | pngquant Path                                          | zopflipng Path           | Output behavior                                      |
| ------- | ------------------------------------------------------ | ------------------------ | ---------------------------------------------------- |
| CLI     | `~/.local/bin/pngquant`                                | `~/.local/bin/zopflipng` | Replace original in place; `-o` for single-file path |
| GUI     | `./pngquant` (relative)                                | `./zopflipng` (relative) | Write `[name]-crunch.png` alongside original         |
| Service | `/Applications/Crunch.app/Contents/Resources/pngquant` | Full path to app bundle  | Write `[name]-crunch.png` alongside original         |

## Optimization Pipeline Detail

Processing always uses a temporary `-crunch` suffix path for pngquant/zopflipng. Final placement depends on context:

```
CLI (default):   temp → finalize_output() → replace original
CLI (-o path):   temp → finalize_output() → move to output path
GUI / Service:   temp → leave as [name]-crunch.png
```

## Quality Assurance

- **Continuous Integration** - GitHub Actions for Linux and macOS
- **Testing** - Python unit tests with error and execution scenarios (via tox)
- **Linting** - black for Python, shellcheck for shell scripts
- **Validation** - pngcheck for PNG output validation
- **Benchmarking** - Automated comparison against reference images using DSSIM
