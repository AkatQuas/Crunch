#!/usr/bin/env python3

# ==================================================================
#  crunch
#    A PNG file optimization tool built on pngquant and zopflipng
#
#   Copyright 2026 AkatQuas
#   MIT License
#   Source Repository: https://github.com/AkatQuas/Crunch
#
#   Copyright 2019 Christopher Simpkins
#   MIT License
#
#   Source Repository: https://github.com/chrissimpkins/Crunch
# ==================================================================

import os
import shutil
import signal
import struct
import subprocess
import sys
import time
from dataclasses import dataclass
from enum import Enum
from multiprocessing import Lock, Pool, cpu_count
from subprocess import CalledProcessError
from typing import Dict, List, Optional

# Global lock declarations (initialized via lock_init for worker processes)
stdstream_lock = None
logging_lock = None

# Active execution context (set in main / worker initializer)
_ctx = None

# Global pool reference kept for tests; owned by ProcessRunner during batch runs
pool = None

_process_runner = None


class ExecutionMode(Enum):
    CLI = "cli"
    GUI = "gui"
    SERVICE = "service"

    @classmethod
    def from_argv(cls, arglist):
        if "--gui" in arglist:
            return cls.GUI
        if "--service" in arglist:
            return cls.SERVICE
        return cls.CLI

    @property
    def is_gui(self):
        return self in (ExecutionMode.GUI, ExecutionMode.SERVICE)


@dataclass
class ExecutionContext:
    mode: ExecutionMode
    output_paths: Dict[str, Optional[str]]
    pngquant_path: str
    zopflipng_path: str
    stdstream_lock: object = None
    logging_lock: object = None

    @property
    def is_gui_mode(self):
        return self.mode.is_gui

    def error_string(self):
        if not self.is_gui_mode:
            return "[ " + format_ansi_red("!") + " ]"
        return "[ ! ]"

    def get_output_path(self, input_path):
        return self.output_paths.get(input_path)


@dataclass
class RunRequest:
    """Parsed CLI/GUI request ready for the optimization engine."""

    mode: ExecutionMode
    png_paths: List[str]
    output_paths: Dict[str, Optional[str]]
    error_string: str


# Application Constants
VERSION = "6.3.1"
VERSION_STRING = "crunch v" + VERSION

# Processor Constant
#  - Modify this to an integer value if you want to fix the number of
#    processes spawned during execution.  The process number is
#    automatically defined during source execution when this is defined
#    as a value of 0
PROCESSES = 0

# Output path mapping for CLI mode: input path -> output path (None = replace original)
OUTPUT_PATHS = {}

# Execution mode set during main() for use in worker processes
GUI_MODE = False

# Dependency Path Constants for Command Line Executable
#  - Redefine these path strings to use system-installed versions of
#    pngquant and zopflipng (e.g. to "~/.local/bin/[executable]")
PNGQUANT_CLI_PATH = os.path.join(os.path.expanduser("~"), ".local", "bin", "pngquant")
ZOPFLIPNG_CLI_PATH = os.path.join(os.path.expanduser("~"), ".local", "bin", "zopflipng")

# Crunch Directory
CRUNCH_DOT_DIRECTORY = os.path.join(
    os.path.expanduser("~"), ".local", "state", "crunch"
)

# Log File Path
LOGFILE_PATH = os.path.join(CRUNCH_DOT_DIRECTORY, "crunch.log")


def resolve_dependency_paths(mode):
    if mode == ExecutionMode.GUI:
        return "./pngquant", "./zopflipng"
    return PNGQUANT_CLI_PATH, ZOPFLIPNG_CLI_PATH


def get_dependency_paths(mode=None):
    """Single seam for pngquant/zopflipng path resolution by execution mode."""
    if mode is not None:
        return resolve_dependency_paths(mode)
    if _ctx is not None:
        return _ctx.pngquant_path, _ctx.zopflipng_path
    return resolve_dependency_paths(_infer_mode_without_context())


def _infer_mode_without_context():
    if GUI_MODE:
        if "--service" in sys.argv:
            return ExecutionMode.SERVICE
        return ExecutionMode.GUI
    return ExecutionMode.from_argv(sys.argv[1:])


def _execution_context_for_mode(mode, output_paths=None):
    pngquant_path, zopflipng_path = get_dependency_paths(mode)
    return ExecutionContext(
        mode=mode,
        output_paths=output_paths if output_paths is not None else OUTPUT_PATHS,
        pngquant_path=pngquant_path,
        zopflipng_path=zopflipng_path,
        stdstream_lock=stdstream_lock,
        logging_lock=logging_lock,
    )


def _resolve_context():
    if _ctx is not None:
        return _ctx
    return _execution_context_for_mode(_infer_mode_without_context())


HELP_STRING = """
==================================================
crunch
  Copyright 2019 Christopher Simpkins
  MIT License

  Source: https://github.com/chrissimpkins/Crunch

  Copyright 2026 AkatQuas
  MIT License

  Source: https://github.com/AkatQuas/Crunch
==================================================

crunch is a command line executable that performs lossy optimization of one
or more png image files with pngquant and zopflipng.

Usage:
    $ crunch [options] [image path 1]...[image path n]
    $ crunch [options] path_to_folder

Options:
    --help, -h          application help
    --usage             application usage
    --version, -v       application version
    --log, -l           output log content (use -l N to specify number of lines, default: 200)
    --output, -o PATH   write optimized image to PATH (CLI only)

Notes:
    - By default, the original file is replaced after optimization (CLI only)
    - Use --output / -o with a single input file to write elsewhere
    - --output is not supported with multiple input files (each file is replaced in place)
    - --output is not supported in --gui or --service modes
    - GUI and service modes create a new file with "-crunch" suffix
"""

USAGE = """$ crunch [options] [image path 1]...[image path n]

Options:
    -o, --output PATH   write optimized image to PATH (single input file only)
    --gui               GUI mode (macOS)
    --service           service mode (macOS)
"""


def _parse_run_request(argv):
    """CLI adapter: parse argv into a RunRequest, or exit for meta commands."""
    argv = argv if len(argv) > 0 else ["-h"]
    mode = ExecutionMode.from_argv(argv)
    error_string = _execution_context_for_mode(mode, output_paths={}).error_string()

    if argv[0] in ("-v", "--version"):
        print(VERSION_STRING)
        sys.exit(0)
    if argv[0] in ("-h", "--help"):
        print(HELP_STRING)
        sys.exit(0)
    if argv[0] == "--usage":
        print(USAGE)
        sys.exit(0)
    if argv[0] in ("-l", "--log"):
        num_lines = 200
        if len(argv) > 1:
            try:
                num_lines = int(argv[1])
            except ValueError:
                sys.stderr.write(
                    f"{error_string} Invalid argument '{argv[1]}' for --log. "
                    f"Please provide a valid integer for number of lines.{os.linesep}"
                )
                sys.exit(1)
        print_log(num_lines)
        sys.exit(0)

    output_option, argv = parse_cli_options(argv, error_string)
    if output_option and mode.is_gui:
        sys.stderr.write(
            f"{error_string} --output / -o flag is not supported in GUI or Service "
            f"mode.{os.linesep}"
        )
        sys.exit(1)

    if mode.is_gui:
        png_path_list = argv[1:]
        if len(png_path_list) == 0:
            sys.stderr.write(
                f"{error_string} Please include one or more paths to PNG image files as "
                f"arguments to the script.{os.linesep}"
            )
            sys.exit(1)
    else:
        png_path_list = argv
        if len(png_path_list) == 1 and os.path.isdir(png_path_list[0]):
            folder_path = png_path_list[0]
            png_path_list = []
            for root, _dirs, files in os.walk(folder_path):
                for filename in files:
                    if filename.lower().endswith(".png"):
                        png_path_list.append(os.path.join(root, filename))
            if not png_path_list:
                sys.stderr.write(
                    f"{error_string} No PNG files found in folder '{folder_path}'."
                    f"{os.linesep}"
                )
                sys.exit(1)

    valid_png_paths = []
    for png_path in png_path_list:
        if not os.path.isfile(png_path):
            sys.stderr.write(
                f"{error_string} '{png_path}' does not appear to be a "
                f"valid path to a PNG file. Skipping...{os.linesep}"
            )
            continue
        if not is_valid_png(png_path):
            sys.stderr.write(
                f"{error_string} '{png_path}' is not a valid PNG file. Skipping..."
                f"{os.linesep}"
            )
            if mode.is_gui:
                log_error(f"{png_path} is not a valid PNG file. Skipping...")
            continue
        valid_png_paths.append(png_path)

    if not valid_png_paths:
        sys.stderr.write(
            f"No valid PNG files found. Please try again "
            f"with one or more valid PNG files.{os.linesep}"
        )
        if mode.is_gui:
            log_error("No valid PNG files found.")
        sys.exit(1)

    output_paths = build_output_paths(valid_png_paths, output_option, error_string)
    return RunRequest(
        mode=mode,
        png_paths=valid_png_paths,
        output_paths=output_paths,
        error_string=error_string,
    )


def main(argv):
    global GUI_MODE, _ctx, OUTPUT_PATHS, _process_runner

    _ctx = None
    ProcessRunner.register_handlers()

    if not os.path.isdir(CRUNCH_DOT_DIRECTORY):
        os.makedirs(CRUNCH_DOT_DIRECTORY)

    request = _parse_run_request(argv)
    GUI_MODE = request.mode.is_gui
    OUTPUT_PATHS = request.output_paths

    execution_context = _execution_context_for_mode(
        request.mode, output_paths=request.output_paths
    )
    _ctx = execution_context

    try:
        _run_optimization(execution_context, request.png_paths, request.error_string)
    finally:
        _ctx = None

    if GUI_MODE:
        log_info("Crunch execution ended.")
    sys.exit(0)


def _run_optimization(execution_context, png_path_list, error_string):
    pngquant_exe_path = execution_context.pngquant_path
    zopflipng_exe_path = execution_context.zopflipng_path

    # Dependency check
    if not os.path.exists(pngquant_exe_path):
        sys.stderr.write(
            f"{error_string} pngquant executable was not identified on path "
            f"'{pngquant_exe_path}'{os.linesep}"
        )
        if execution_context.is_gui_mode:
            log_error(
                f"pngquant was not found on the expected path {pngquant_exe_path}"
            )
        sys.exit(1)
    elif not os.path.exists(zopflipng_exe_path):
        sys.stderr.write(
            f"{error_string} zopflipng executable was not identified on path "
            f"'{zopflipng_exe_path}'{os.linesep}"
        )
        if execution_context.is_gui_mode:
            log_error(
                f"zopflipng was not found on the expected path {zopflipng_exe_path}"
            )
        sys.exit(1)

    # ////////////////////////////////////
    # OPTIMIZATION PROCESSING
    # ////////////////////////////////////
    print("Crunching ...")

    ProcessRunner.active().run(
        execution_context, error_string, optimize_png, png_path_list
    )


# ///////////////////////
# FUNCTION DEFINITIONS
# ///////////////////////


def optimize_png(png_path):
    # pool.map must not receive return values that reference process locks
    _optimizer.optimize(png_path)


def run_subprocess(command):
    """Run a subprocess command in a new process group.

    Uses start_new_session=True so child processes are in their own
    process group and can be terminated together with the parent.
    Output is suppressed by redirecting DEVNULL.
    """
    process = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        shell=True,
        start_new_session=True,
    )
    returncode = process.wait()

    if returncode != 0:
        raise CalledProcessError(returncode, command)

    return None


def parse_cli_options(argv, error_string):
    """Parse CLI options from argv. Returns (output_path, remaining_args)."""
    output_path = None
    remaining = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("-o", "--output"):
            if i + 1 >= len(argv):
                sys.stderr.write(
                    f"{error_string} Missing argument for {arg}.{os.linesep}"
                )
                sys.exit(1)
            output_path = argv[i + 1]
            i += 2
        elif arg in ("-r", "--replace"):
            sys.stderr.write(
                f"{error_string} --replace / -r has been removed. "
                f"Original files are replaced by default in CLI mode. "
                f"Use --output / -o to write to a different path.{os.linesep}"
            )
            sys.exit(1)
        else:
            remaining.append(arg)
            i += 1
    return output_path, remaining


def build_output_paths(png_path_list, output_option, error_string):
    """Build input -> output path mapping for CLI execution."""
    output_paths = {}
    if not output_option:
        for png_path in png_path_list:
            output_paths[png_path] = None
        return output_paths

    if len(png_path_list) != 1:
        sys.stderr.write(
            f"{error_string} --output / -o can only be used with a single "
            f"input file. Multiple files are always optimized in place.{os.linesep}"
        )
        sys.exit(1)

    output_paths[png_path_list[0]] = resolve_output_path(
        output_option, png_path_list[0]
    )
    return output_paths


def resolve_output_path(output_option, input_path):
    """Resolve --output path for a single input file."""
    if os.path.isdir(output_option):
        return os.path.join(output_option, os.path.basename(input_path))

    output_dir = os.path.dirname(output_option)
    if output_dir and not os.path.isdir(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    return output_option


def get_output_path(input_path):
    return OUTPUT_PATHS.get(input_path)


def fix_filepath_args(args):
    arg_list = []
    parsed_filepath = ""
    for arg in args:
        if arg[0] == "-":
            arg_list.append(arg)
        elif len(arg) > 2 and "." in arg[1:]:
            # if format is `\w+\.\w+`, then this is a filename, not directory
            # this is the end of a filepath string that may have had
            # spaces in directories prior to this level.  Let's recreate
            # the entire original path
            filepath = parsed_filepath + arg
            arg_list.append(filepath)
            # reset the temp string that is used to reconstruct the filepaths
            parsed_filepath = ""
        else:
            # if the argument does not end with a .png, then there must have
            # been a space in the directory paths, let's add it back
            parsed_filepath = parsed_filepath + arg + " "
    # return new argument list with fixed filepaths to calling code
    return arg_list


def get_pngquant_path():
    return get_dependency_paths()[0]


def get_zopflipng_path():
    return get_dependency_paths()[1]


def is_gui(arglist):
    return ExecutionMode.from_argv(arglist).is_gui


def is_valid_png(filepath):
    # The PNG byte signature (https://www.w3.org/TR/PNG/#5PNG-file-signature)
    expected_signature = struct.pack("8B", 137, 80, 78, 71, 13, 10, 26, 10)
    # open the file and read first 8 bytes
    with open(filepath, "rb") as filer:
        signature = filer.read(8)
    # return boolean test result for first eight bytes == expected PNG byte signature
    return signature == expected_signature


def lock_init(ss_lock, log_lock, context):
    # Based on approach described in
    # https://stackoverflow.com/a/25558333/2848172
    global stdstream_lock
    global logging_lock
    global OUTPUT_PATHS
    global GUI_MODE
    global _ctx

    context.stdstream_lock = ss_lock
    context.logging_lock = log_lock
    _ctx = context
    stdstream_lock = ss_lock
    logging_lock = log_lock
    OUTPUT_PATHS = context.output_paths
    GUI_MODE = context.is_gui_mode


def log_error(errmsg):
    current_time = time.strftime("%m-%d-%y %H:%M:%S")
    if logging_lock:
        logging_lock.acquire()
    with open(LOGFILE_PATH, "a") as filewriter:
        filewriter.write(f"{current_time}\tERROR\t{errmsg}{os.linesep}")
        filewriter.flush()
        os.fsync(filewriter.fileno())
    if logging_lock:
        logging_lock.release()


def log_info(infomsg):
    current_time = time.strftime("%m-%d-%y %H:%M:%S")
    if logging_lock:
        logging_lock.acquire()
    with open(LOGFILE_PATH, "a") as filewriter:
        filewriter.write(f"{current_time}\tINFO\t{infomsg}{os.linesep}")
        filewriter.flush()
        os.fsync(filewriter.fileno())
    if logging_lock:
        logging_lock.release()
    return None


def print_log(num_lines=200):
    """Output the last N lines of the crunch log file."""
    if not os.path.isfile(LOGFILE_PATH):
        print(f"Log file not found: {LOGFILE_PATH}")
        return

    with open(LOGFILE_PATH, "r") as f:
        lines = f.readlines()

    if not lines:
        print("Log file is empty.")
        return

    tail_lines = lines[-num_lines:] if len(lines) > num_lines else lines
    print(f"--- Last {len(tail_lines)} lines of {LOGFILE_PATH} ---")
    for line in tail_lines:
        print(line.rstrip())


def shellquote(filepath):
    return "'" + filepath.replace("'", "'\\''") + "'"


def format_ansi_red(text):
    if sys.stdout.isatty():
        return "\033[0;31m" + text + "\033[0m"
    return text


def format_ansi_green(text):
    if sys.stdout.isatty():
        return "\033[0;32m" + text + "\033[0m"
    return text


# ///////////////////////
# OBJECT DEFINITIONS
# ///////////////////////


class ProcessRunner(object):
    """Owns signal handling, pool lifecycle, and worker context initialization."""

    def __init__(self):
        self._pool = None

    @classmethod
    def register_handlers(cls):
        global _process_runner
        _process_runner = cls()
        signal.signal(signal.SIGINT, _process_runner._handle_signal)
        signal.signal(signal.SIGTERM, _process_runner._handle_signal)
        return _process_runner

    @classmethod
    def active(cls):
        if _process_runner is None:
            return cls.register_handlers()
        return _process_runner

    def _handle_signal(self, signum, frame):
        signal.signal(signum, signal.SIG_IGN)
        sys.stderr.write("\nReceived interrupt signal. Terminating all processes...\n")
        sys.stderr.flush()
        self._terminate_pool()
        self._kill_process_group()
        os._exit(128 + signum)

    def _terminate_pool(self):
        global pool
        if self._pool is not None:
            try:
                self._pool.terminate()
                self._pool.join()
                self._pool.close()
            except Exception:
                pass
            finally:
                self._pool = None
                pool = None

    @staticmethod
    def _kill_process_group():
        try:
            my_pid = os.getpid()
            pgid = os.getpgid(my_pid)
            if pgid == my_pid:
                os.killpg(pgid, signal.SIGTERM)
        except (OSError, ProcessLookupError):
            pass

    def run(self, execution_context, error_string, work_fn, png_path_list):
        ss_lock = Lock()
        log_lock = Lock()

        if len(png_path_list) == 1:
            lock_init(ss_lock, log_lock, execution_context)
            work_fn(png_path_list[0])
            return

        processes = PROCESSES or cpu_count()
        if processes > len(png_path_list):
            processes = len(png_path_list)

        print(
            f"Spawning {processes} processes to optimize {len(png_path_list)} "
            f"image files..."
        )

        global pool
        try:
            self._pool = Pool(
                processes,
                initializer=lock_init,
                initargs=(ss_lock, log_lock, execution_context),
            )
            pool = self._pool
            self._pool.map(work_fn, png_path_list)
        except Exception as e:
            if stdstream_lock and stdstream_lock.acquire(block=False):
                stdstream_lock.release()
            sys.stderr.write(f"-----{os.linesep}")
            sys.stderr.write(
                f"{error_string} Error detected during execution.{os.linesep}"
            )
            sys.stderr.write(f"{e}{os.linesep}")
            if execution_context.is_gui_mode:
                log_error(str(e))
            sys.exit(1)
        finally:
            if self._pool is not None:
                self._pool.close()
                self._pool.join()
                self._pool = None
                pool = None


def signal_handler(signum, frame):
    """Backward-compatible delegate to ProcessRunner signal handling."""
    ProcessRunner.active()._handle_signal(signum, frame)


class PngOptimizer(object):
    """Deep module: pngquant → zopflipng pipeline with injectable subprocess seam."""

    PNGQUANT_IGNORE_CODES = (98, 99)

    def __init__(self, subprocess_runner=None):
        self._run_subprocess = subprocess_runner or run_subprocess

    def optimize(self, png_path):
        ctx = _resolve_context()
        img = ImageFile(png_path, ctx)

        if not self._run_pngquant_stage(img, ctx):
            return None
        if not self._run_zopflipng_stage(img, ctx):
            return None

        img.get_post_filesize()
        percent = img.get_compression_percent()

        if not ctx.is_gui_mode:
            img.finalize_output()

        self._report_result(img, ctx, percent)
        return img

    def _build_pngquant_command(self, img, ctx):
        options = (
            f" --quality=80-98 --skip-if-larger --force --strip --speed 1 "
            f"--ext {img.post_suffix} "
        )
        return ctx.pngquant_path + options + shellquote(img.pre_filepath)

    def _build_zopflipng_command(self, img, ctx):
        # use --filters=0 by default for quantized PNG files (based upon testing by CS)
        options = " -y --filters=0 "
        if not os.path.exists(img.post_filepath):
            shutil.copy(img.pre_filepath, img.post_filepath)
            # If pngquant did not quantize the file, permit zopflipng to attempt compression
            # with mulitple filters.  This achieves better compression than the default
            # approach for non-quantized PNG files, but takes significantly longer
            # (based upon testing by CS)
            options = " -y --lossy_transparent "
        return (
            ctx.zopflipng_path
            + options
            + shellquote(img.post_filepath)
            + " "
            + shellquote(img.post_filepath)
        )

    def _run_pngquant_stage(self, img, ctx):
        try:
            self._run_subprocess(self._build_pngquant_command(img, ctx))
        except CalledProcessError as cpe:
            if cpe.returncode in self.PNGQUANT_IGNORE_CODES:
                return True
            return self._handle_stage_failure(ctx, img, "pngquant", cpe)
        except Exception as exc:
            return self._handle_stage_failure(ctx, img, "pngquant", exc)
        return True

    def _run_zopflipng_stage(self, img, ctx):
        try:
            self._run_subprocess(self._build_zopflipng_command(img, ctx))
        except CalledProcessError as cpe:
            return self._handle_stage_failure(ctx, img, "zopflipng", cpe)
        except Exception as exc:
            return self._handle_stage_failure(ctx, img, "zopflipng", exc)
        return True

    def _handle_stage_failure(self, ctx, img, stage, exc):
        error_string = ctx.error_string()
        self._write_stage_error(ctx, error_string, img, stage)
        if ctx.is_gui_mode:
            log_error(
                f"{img.pre_filepath} processing failed at {stage} stage."
                f"{os.linesep}{exc}"
            )
            return False
        raise exc

    def _write_stage_error(self, ctx, error_string, img, stage):
        if ctx.stdstream_lock:
            ctx.stdstream_lock.acquire()
        sys.stderr.write(
            f"{error_string} {img.pre_filepath} processing failed at "
            f"{stage} stage.{os.linesep}"
        )
        if ctx.stdstream_lock:
            ctx.stdstream_lock.release()

    def _report_result(self, img, ctx, percent):
        percent_string = "{0:.2f}%".format(percent)
        if not ctx.is_gui_mode and percent < 100:
            percent_string = format_ansi_green(percent_string)

        if ctx.stdstream_lock:
            ctx.stdstream_lock.acquire()
        print(f"[ {percent_string} ] {img.post_filepath} ({img.post_size} bytes)")
        if ctx.stdstream_lock:
            ctx.stdstream_lock.release()

        if ctx.is_gui_mode:
            log_info(
                f"[ {percent_string} ] {img.post_filepath} ({img.post_size} bytes)"
            )


_optimizer = PngOptimizer()


class ImageFile(object):
    def __init__(self, filepath, context=None):
        self._context = context
        self.pre_filepath = filepath
        self.post_filepath = self._get_post_filepath()
        self.post_suffix = self._get_post_suffix()
        self.pre_size = self._get_filesize(self.pre_filepath)
        self.post_size = 0

    def _get_filesize(self, file_path):
        return os.path.getsize(file_path)

    def _get_post_suffix(self):
        _, extension = os.path.splitext(self.pre_filepath)
        return "-crunch" + extension

    def _get_post_filepath(self):
        path, extension = os.path.splitext(self.pre_filepath)
        return path + "-crunch" + extension

    def finalize_output(self):
        """Write optimized file to final destination (replace original or --output path)."""
        if not os.path.exists(self.post_filepath):
            return

        if self._context is not None:
            output_path = self._context.get_output_path(self.pre_filepath)
        else:
            output_path = get_output_path(self.pre_filepath)
        if output_path is None:
            os.remove(self.pre_filepath)
            os.rename(self.post_filepath, self.pre_filepath)
            self.post_filepath = self.pre_filepath
        elif os.path.abspath(output_path) != os.path.abspath(self.post_filepath):
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.isdir(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            if os.path.exists(output_path):
                os.remove(output_path)
            shutil.move(self.post_filepath, output_path)
            self.post_filepath = output_path

        self.post_size = self._get_filesize(self.post_filepath)

    def get_post_filesize(self):
        self.post_size = self._get_filesize(self.post_filepath)

    def get_compression_percent(self):
        ratio = float(self.post_size) / float(self.pre_size)
        return ratio * 100


if __name__ == "__main__":
    # bugfix for macOS GUI / right-click service filepath issue
    # when spaces are included in the absolute path to the image
    # file.  https://github.com/chrissimpkins/Crunch/issues/30
    # This workaround reconstructs the original filepaths
    # that are split by the shell script into separate arguments
    # when there are spaces in the macOS file path
    if len(sys.argv) > 1 and sys.argv[1] in ("--gui", "--service"):
        arg_list = fix_filepath_args(sys.argv[1:])
        main(arg_list)
    else:
        # the command line executable assumes that users will appropriately quote
        # or escape special characters (including spaces) on the command line,
        # no need for the special parsing treatment above
        main(sys.argv[1:])
