# Product

## Overview

Crunch is a lossy PNG image optimization tool that significantly reduces PNG file sizes while maintaining acceptable visual quality. It combines two industry-standard compression tools—pngquant and zopflipng—into a unified pipeline that achieves better compression than either tool alone.

## What is Crunch?

### Problem

PNG files, especially those generated from design tools or screen captures, often contain more data than necessary for web and application deployment. Lossless compression tools like OptiPNG or PNGCrush provide modest savings, but lossy approaches can achieve 50-75% size reductions.

### Solution

Crunch uses a two-stage optimization pipeline:

1. **pngquant** reduces colors and applies lossy compression
2. **zopflipng** applies aggressive zopfli DEFLATE compression

This combination consistently achieves 30-50% of original file sizes while maintaining perceptual quality (DSSIM scores typically below 0.01).

## Features

### Core Capabilities

| Feature                      | Description                                               |
| ---------------------------- | --------------------------------------------------------- |
| **Lossy Compression**        | Aggressive color reduction with quality threshold (80-98) |
| **Parallel Processing**      | Automatic multi-core utilization for batch processing     |
| **Smart Optimization**       | Skips optimization if result would be larger              |
| **Metadata Stripping**       | Removes unnecessary PNG chunks                            |
| **Cross-Platform CLI**       | Works on macOS, Linux, and Windows (WSL/Cygwin)           |
| **Native macOS Integration** | GUI app and Finder right-click service                    |

### User Interfaces

#### 1. Command Line Executable

```
$ crunch image1.png image2.png image3.png
[ 33.61% ] image1-crunch.png (196085 bytes)
[ 48.16% ] image2-crunch.png (66593 bytes)
[ 39.62% ] image3-crunch.png (77965 bytes)
```

**Options:**

- `-h, --help` - Display help message
- `--usage` - Show usage syntax
- `-v, --version` - Display version information

**Usage patterns:**

```bash
# Single file
$ crunch myimage.png

# Multiple files
$ crunch img1.png img2.png img3.png

# Wildcard (all PNGs in directory)
$ crunch *.png

# Recursive (with find)
$ find . -name "*.png" -exec crunch {} \;
```

#### 2. macOS GUI Application (Built with Platypus)

The native macOS GUI application is created using **Platypus**, a tool that packages scripts as native macOS applications. The application is configured using the `profile/Crunch.platypus` configuration file.

- **Platform**: macOS (built via Platypus)
- **Interface**: Drag-and-drop Web View interface
- **Configuration file**: `profile/Crunch.platypus`
- **Features**:
  - **Drag-and-drop** interface for one or more PNG files
  - **Visual progress** with animated GIF indicators
  - **Status display** showing compression results
  - **Auto-recovery** handles files with spaces in paths
  - **Menu bar status item** integration

**Workflow:**

1. Launch Crunch.app
2. Drag PNG files onto the window
3. View animation during processing
4. Check results in log file (`~/.crunch/crunch.log`)

#### 3. macOS Finder Service

- Right-click one or more PNG files in Finder
- Select **Services > Crunch Image(s)**
- Optimized files saved with `-crunch.png` suffix

## Performance

### Compression Results (Typical)

| Image Type    | Original Size | Optimized | Reduction | DSSIM Score |
| ------------- | ------------- | --------- | --------- | ----------- |
| Photography   | 583,398 B     | 196,085 B | 66.4%     | 0.001383    |
| Illustration  | 197,193 B     | 67,596 B  | 65.7%     | 0.003047    |
| Color Heavy   | 249,251 B     | 67,135 B  | 73.1%     | 0.002450    |
| UI/Screenshot | 440,126 B     | 196,962 B | 55.3%     | 0.001013    |

### Processing Speed

- Single file: ~1-2 seconds (varies by image size)
- Batch processing: Automatic parallelization using all available CPU cores

## Installation

### Command Line (macOS/Linux)

```bash
# Install Rust (required for pngquant v3)
$ curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

$ git clone https://github.com/chrissimpkins/Crunch.git
$ cd Crunch
$ make build-dependencies    # Compiles pngquant v3 (requires Rust) and zopflipng
$ make install-executable    # Installs to /usr/local/bin
```

### macOS GUI Application

1. **Homebrew** (recommended):

   ```bash
   $ brew install --cask crunch
   ```

2. **Manual**:
   - Download `Crunch-Installer.dmg` from [Releases](https://github.com/chrissimpkins/Crunch/releases)
   - Drag `Crunch.app` to Applications

### macOS Finder Service

```bash
$ make install-macos-service
```

## Testing

To run the test suite, you'll need to set up a Python virtual environment and install the testing dependencies:

```bash
# Create and activate virtual environment
$ python3 -m venv .venv
$ source .venv/bin/activate

# Install Python testing dependencies
$ pip install -r requirements.txt

# Install system dependencies (macOS)
$ brew install pngcheck

# Run all tests
$ make test

# Or run individual test suites
$ make test-python        # Python unit tests + flake8
$ make test-shell         # shellcheck validation
$ make test-valid-png-output  # Verify PNG output validity
```

## Output

### File Naming

Optimized files are saved alongside originals with the `-crunch` suffix:

```
original.png    → original-crunch.png
```

### Quality Threshold

- **Minimum quality**: 80 (images below this are rejected)
- **Target quality**: 98 (maximum quality for optimization)
- **Skip if larger**: Files are not modified if optimization increases size

## Use Cases

| Use Case              | Recommendation                                       |
| --------------------- | ---------------------------------------------------- |
| **Web assets**        | Ideal for websites, significantly reduces load times |
| **Mobile apps**       | Reduces APK/IPA sizes                                |
| **Game assets**       | Smaller asset bundles                                |
| **Email attachments** | More manageable file sizes                           |
| **Archival**          | Not recommended (lossy)                              |

## Limitations

- **Lossy compression** - Original image data is discarded
- **PNG only** - Does not support JPEG, WebP, or other formats
- **Quality degradation** - Some images show visible artifacts
- **Non-reversible** - Original files must be preserved separately

## Integration with Platypus

The macOS GUI application is built using **Platypus**, a tool that creates macOS applications from shell scripts. The application configuration is defined in `profile/Crunch.platypus`, which specifies:

**Application Metadata:**

- **Application Name**: Crunch
- **Bundle Identifier**: `com.akatquas.Crunch`
- **Author**: AkatQuas

**Build Configuration:**

- **Interface Type**: Web View (HTML-based UI)
- **Script Path**: `src/crunch-gui.sh`
- **Interpreter**: `/bin/sh`
- **Icon**: `img/CrunchIcon.icns`

**Runtime Behavior:**

- **Remains Running**: Yes (waits for dropped files)
- **Droppable**: Yes (accepts dragged files)
- **Accepts Files**: Yes (public.item, public.folder)
- **Authentication**: Not required

**Bundled Resources** (as defined in `BundledFiles`):

- `src/crunch.py` - Core Python engine
- `src/include/pngquant` - Lossy compression binary
- `src/include/zopflipng` - Compression binary
- `html/*.html` - GUI templates
- `img/animations/*.gif` - Loading animations

To rebuild the macOS application:

1. **Create Crunch.app**: Use Platypus to load `profile/Crunch.platypus` and generate the app
2. **Build icon set** (optional): `make build-macos-icns`
3. **Create DMG installer**: `make build-macos-installer` (requires `Crunch.app` in `bin/` directory)

```bash
# Step 1: Create Crunch.app using Platypus (see https://sveinbjorn.org/platypus)
# Step 2: Place Crunch.app in bin/ directory
$ make build-macos-icns      # Build macOS icon set
$ make build-macos-installer # Create DMG installer from Crunch.app
$ make dist                  # Create distribution DMG (requires different create-dmg)
```

**Note**: The `create-dmg` tool is required:

- For local development (`make build-macos-installer`): https://github.com/sindresorhus/create-dmg
- For distribution builds (`make dist`): https://github.com/create-dmg/create-dmg

## License

- **Crunch core**: MIT License
- **pngquant**: GPL v3
- **zopflipng**: Apache License 2.0

See [LICENSE.md](LICENSE.md) for full details.
