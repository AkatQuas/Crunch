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
import struct
import subprocess
import sys
import time
from multiprocessing import Lock, Pool, cpu_count
from subprocess import CalledProcessError

# Global lock declarations (initialized via lock_init for worker processes)
stdstream_lock = None
logging_lock = None

# Application Constants
VERSION = "6.2.0"
VERSION_STRING = "crunch v" + VERSION

# Processor Constant
#  - Modify this to an integer value if you want to fix the number of
#    processes spawned during execution.  The process number is
#    automatically defined during source execution when this is defined
#    as a value of 0
PROCESSES = 0

# Replace flag - when True, replace original file with optimized version
REPLACE_ORIGINAL = False

# Dependency Path Constants for Command Line Executable
#  - Redefine these path strings to use system-installed versions of
#    pngquant and zopflipng (e.g. to "~/.local/bin/[executable]")
PNGQUANT_CLI_PATH = os.path.join(os.path.expanduser("~"), ".local", "bin", "pngquant")
ZOPFLIPNG_CLI_PATH = os.path.join(os.path.expanduser("~"), ".local", "bin", "zopflipng")

# Crunch Directory (dot directory in $HOME)
CRUNCH_DOT_DIRECTORY = os.path.join(
    os.path.expanduser("~"), ".local", "state", "crunch"
)

# Log File Path Constants
LOGFILE_PATH = os.path.join(CRUNCH_DOT_DIRECTORY, "crunch.log")

HELP_STRING = """
==================================================
 crunch
  Copyright 2026 AkatQuas
  MIT License

  Source: https://github.com/AkatQuas/Crunch

  Copyright 2019 Christopher Simpkins
  MIT License

  Source: https://github.com/chrissimpkins/Crunch
==================================================

crunch is a command line executable that performs lossy optimization of one
or more png image files with pngquant and zopflipng.

Usage:
    $ crunch [options] [image path 1]...[image path n]

Options:
    --help, -h      application help
    --usage         application usage
    --version, -v   application version
    --log, -l       output log content (use -l N to specify number of lines, default: 200)
    --replace, -r   replace original file with optimized version (CLI only)

Notes:
    - --replace / -r is only available in command line mode
    - Not supported in --gui or --service modes
    - Without --replace, a new file with "-crunch" suffix is created
"""

USAGE = """$ crunch [options] [image path 1]...[image path n]

Options:
    -r, --replace   replace original file with optimized version
    --gui           GUI mode (macOS)
    --service       service mode (macOS)
"""


def main(argv):

    # Create the Crunch dot directory in $HOME if it does not exist
    # Only used for macOS GUI and macOS right-click menu service execution
    if len(argv) > 0 and argv[0] in ("--gui", "--service"):
        if not os.path.isdir(CRUNCH_DOT_DIRECTORY):
            os.makedirs(CRUNCH_DOT_DIRECTORY)
        # Log entries are appended to the file on every script execution
        # (see log_error and log_info functions below)

    # ////////////////////////
    # ANSI COLOR DEFINITIONS
    # ////////////////////////
    if not is_gui(sys.argv):
        ERROR_STRING = "[ " + format_ansi_red("!") + " ]"
    else:
        ERROR_STRING = "[ ! ]"

    # //////////////////////////////////
    # CONFIRM ARGUMENT PRESENT
    # //////////////////////////////////

    if len(argv) == 0:
        sys.stderr.write(
            f"{ERROR_STRING} Please include one or more paths to PNG image files as "
            "arguments to the script.{os.linesep}"
        )
        sys.exit(1)

    # //////////////////////////////////////
    # HELP, USAGE, VERSION option handling
    # //////////////////////////////////////

    if argv[0] in ("-v", "--version"):
        print(VERSION_STRING)
        sys.exit(0)
    elif argv[0] in ("-h", "--help"):
        print(HELP_STRING)
        sys.exit(0)
    elif argv[0] == "--usage":
        print(USAGE)
        sys.exit(0)
    elif argv[0] in ("-l", "--log"):
        # Handle log output with optional line count
        num_lines = 200  # default
        if len(argv) > 1:
            try:
                num_lines = int(argv[1])
            except ValueError:
                sys.stderr.write(
                    f"{ERROR_STRING} Invalid argument '{argv[1]}' for --log. "
                    f"Please provide a valid integer for number of lines.{os.linesep}"
                )
                sys.exit(1)
        print_log(num_lines)
        sys.exit(0)

    # Handle --replace / -r flag (only allowed in non-GUI mode)
    global REPLACE_ORIGINAL
    if argv[0] in ("-r", "--replace"):
        if is_gui(argv):
            sys.stderr.write(
                f"{ERROR_STRING} --replace / -r flag is not supported in GUI or Service "
                f"mode.{os.linesep}"
            )
            sys.exit(1)
        REPLACE_ORIGINAL = True
        # Remove the flag from the argument list so it doesn't get treated as a file path
        argv = argv[1:]

    # ////////////////////////
    # DEFINE DEPENDENCY PATHS
    # ////////////////////////
    PNGQUANT_EXE_PATH = get_pngquant_path()
    ZOPFLIPNG_EXE_PATH = get_zopflipng_path()

    # ////////////////////
    # PARSE PNG_PATH_LIST
    # ////////////////////

    if is_gui(argv):
        png_path_list = argv[1:]
    else:
        png_path_list = argv

    # //////////////////////////////////
    # COMMAND LINE ERROR HANDLING
    # //////////////////////////////////

    NOTPNG_ERROR_FOUND = False
    for png_path in png_path_list:
        # Not a file test
        if not os.path.isfile(png_path):  # is not an existing file
            sys.stderr.write(
                f"{ERROR_STRING} '{png_path}' does not appear to be a "
                f"valid path to a PNG file{os.linesep}"
            )
            sys.exit(1)  # not a file, abort immediately
        # PNG validity test
        if not is_valid_png(png_path):
            sys.stderr.write(
                f"{ERROR_STRING} '{png_path}' is not a valid PNG file.{os.linesep}"
            )
            if is_gui(argv):
                log_error(f"{png_path} is not a valid PNG file.")
            NOTPNG_ERROR_FOUND = True

    # Exit after checking all file requests and reporting on all invalid
    # file paths (above)
    if NOTPNG_ERROR_FOUND is True:
        sys.stderr.write(
            f"The request was not executed successfully. Please try again "
            f"with one or more valid PNG files.{os.linesep}"
        )
        if is_gui(argv):
            log_error(
                "The request was not executed successfully. Please try "
                "again with one or more valid PNG files."
            )
        sys.exit(1)

    # Dependency error handling
    if not os.path.exists(PNGQUANT_EXE_PATH):
        sys.stderr.write(
            f"{ERROR_STRING} pngquant executable was not identified on path "
            f"'{PNGQUANT_EXE_PATH}'{os.linesep}"
        )
        if is_gui(argv):
            log_error(f"pngquant was not found on the expected path {PNGQUANT_EXE_PATH}")
        sys.exit(1)
    elif not os.path.exists(ZOPFLIPNG_EXE_PATH):
        sys.stderr.write(
            f"{ERROR_STRING} zopflipng executable was not identified on path "
            f"'{ZOPFLIPNG_EXE_PATH}'{os.linesep}"
        )
        if is_gui(argv):
            log_error(
                f"zopflipng was not found on the expected path {ZOPFLIPNG_EXE_PATH}"
            )
        sys.exit(1)

    # ////////////////////////////////////
    # OPTIMIZATION PROCESSING
    # ////////////////////////////////////
    print("Crunching ...")

    # create locks
    ss_lock = Lock()
    log_lock = Lock()

    if len(png_path_list) == 1:
        # the global locks are not necessary for single file processing
        # but must be instantiated because the logging functions are
        # used for single and multi-process execution
        lock_init(ss_lock, log_lock, REPLACE_ORIGINAL)
        # there is only one PNG file, skip spawning of processes and just optimize it
        optimize_png(png_path_list[0])
    else:
        processes = PROCESSES
        # if not defined by user, start by defining spawned processes as number
        # of available cores
        if processes == 0:
            processes = cpu_count()

        # if total cores available is greater than number of files requested,
        # limit to the latter number
        if processes > len(png_path_list):
            processes = len(png_path_list)

        print(
            f"Spawning {processes} processes to optimize {len(png_path_list)} "
            f"image files..."
        )

        # create multiprocessing pool with global locks
        # based on approach described in https://stackoverflow.com/a/25558333/2848172
        # to address shared memory leak described in
        # https://github.com/chrissimpkins/Crunch/issues/100
        p = Pool(
            processes,
            initializer=lock_init,
            initargs=(ss_lock, log_lock, REPLACE_ORIGINAL)
        )

        try:
            p.map(optimize_png, png_path_list)
        except Exception as e:
            if stdstream_lock:
                stdstream_lock.release()
            sys.stderr.write(f"-----{os.linesep}")
            sys.stderr.write(
                f"{ERROR_STRING} Error detected during execution of the request."
                f"{os.linesep}"
            )
            sys.stderr.write(f"{e}{os.linesep}")
            if stdstream_lock:
                stdstream_lock.release()
            if is_gui(argv):
                log_error(str(e))
            sys.exit(1)
        finally:
            p.close()
            p.join()

    # end of successful processing, exit code 0
    if is_gui(argv):
        log_info("Crunch execution ended.")
    sys.exit(0)


# ///////////////////////
# FUNCTION DEFINITIONS
# ///////////////////////


def optimize_png(png_path):
    img = ImageFile(png_path)

    # define pngquant and zopflipng paths
    PNGQUANT_EXE_PATH = get_pngquant_path()
    ZOPFLIPNG_EXE_PATH = get_zopflipng_path()

    # ////////////////////////
    # ANSI COLOR DEFINITIONS
    # ////////////////////////
    if not is_gui(sys.argv):
        ERROR_STRING = "[ " + format_ansi_red("!") + " ]"
    else:
        ERROR_STRING = "[ ! ]"

    # --------------
    # pngquant stage
    # --------------
    pngquant_options = (
        " --quality=80-98 --skip-if-larger --force --strip --speed 1 --ext -crunch.png "
    )
    pngquant_command = PNGQUANT_EXE_PATH + pngquant_options + shellquote(img.pre_filepath)
    try:
        subprocess.check_output(pngquant_command, stderr=subprocess.STDOUT, shell=True)
    except CalledProcessError as cpe:
        if cpe.returncode == 98:
            # this is the status code when file size increases with execution of pngquant.
            # ignore at this stage, original file copied at beginning of zopflipng
            # processing below if it is not present due to these errors
            pass
        elif cpe.returncode == 99:
            # this is the status code when the image quality falls below the set min value
            # ignore at this stage, original lfile copied at beginning of zopflipng
            # processing below if it is not present to these errors
            pass
        else:
            if stdstream_lock:
                stdstream_lock.acquire()
            sys.stderr.write(
                f"{ERROR_STRING} {img.pre_filepath} processing failed at the pngquant "
                f"stage.{os.linesep}"
            )
            if stdstream_lock:
                stdstream_lock.release()
            if is_gui(sys.argv):
                log_error(
                    f"{img.pre_filepath} processing failed at the pngquant stage."
                    f"{os.linesep}{cpe}"
                )
                return None
            else:
                raise cpe
    except Exception as e:
        if is_gui(sys.argv):
            log_error(
                f"{img.pre_filepath} processing failed at the pngquant stage."
                f"{os.linesep}{e}"
            )
            return None
        else:
            raise e

    # ---------------
    # zopflipng stage
    # ---------------
    # use --filters=0 by default for quantized PNG files (based upon testing by CS)
    zopflipng_options = " -y --filters=0 "
    # confirm that a file with proper path was generated by pngquant
    # pngquant does not write expected file path if the file was larger after processing
    if not os.path.exists(img.post_filepath):
        shutil.copy(img.pre_filepath, img.post_filepath)
        # If pngquant did not quantize the file, permit zopflipng to attempt compression
        # with mulitple filters.  This achieves better compression than the default
        # approach for non-quantized PNG files, but takes significantly longer
        # (based upon testing by CS)
        zopflipng_options = " -y --lossy_transparent "
    zopflipng_command = (
        ZOPFLIPNG_EXE_PATH
        + zopflipng_options
        + shellquote(img.post_filepath)
        + " "
        + shellquote(img.post_filepath)
    )
    try:
        subprocess.check_output(zopflipng_command, stderr=subprocess.STDOUT, shell=True)
    except CalledProcessError as cpe:
        if stdstream_lock:
            stdstream_lock.acquire()
        sys.stderr.write(
            f"{ERROR_STRING} {img.pre_filepath} processing failed at the zopflipng "
            f"stage.{os.linesep}"
        )
        if stdstream_lock:
            stdstream_lock.release()
        if is_gui(sys.argv):
            log_error(
                f"{img.pre_filepath} processing failed at the zopflipng stage."
                f"{os.linesep}{cpe}"
            )
            return None
        else:
            raise cpe
    except Exception as e:
        if is_gui(sys.argv):
            log_error(
                f"{img.pre_filepath} processing failed at the zopflipng stage."
                f"{os.linesep}{e}"
            )
            return None
        else:
            raise e

    # Check file size post-optimization and report comparison with pre-optimization file
    img.get_post_filesize()
    percent = img.get_compression_percent()

    # Replace original file with optimized version if --replace flag is set
    if REPLACE_ORIGINAL:
        img.finalize_replacement()

    percent_string = "{0:.2f}%".format(percent)
    # if compression occurred, color the percent string green
    # otherwise, leave it default text color
    if not is_gui(sys.argv) and percent < 100:
        percent_string = format_ansi_green(percent_string)

    # report percent original file size / post file path / size (bytes) to
    # stdout (command line executable)
    if stdstream_lock:
        stdstream_lock.acquire()
    print(
        "[ "
        + percent_string
        + " ] "
        + img.post_filepath
        + " ("
        + str(img.post_size)
        + " bytes)"
    )
    if stdstream_lock:
        stdstream_lock.release()

    # report percent original file size / post file path / size (bytes) to log file
    # (macOS GUI + right-click service)
    if is_gui(sys.argv):
        log_info(
            "[ "
            + percent_string
            + " ] "
            + img.post_filepath
            + " ("
            + str(img.post_size)
            + " bytes)"
        )


# -----------
# Utilities
# -----------


def fix_filepath_args(args):
    arg_list = []
    parsed_filepath = ""
    for arg in args:
        if arg[0] == "-":
            # add command line options
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
    if sys.argv[1] == "--gui":
        return "./pngquant"
    elif sys.argv[1] == "--service":
        return "/Applications/Crunch.app/Contents/Resources/pngquant"
    else:
        return PNGQUANT_CLI_PATH


def get_zopflipng_path():
    if sys.argv[1] == "--gui":
        return "./zopflipng"
    elif sys.argv[1] == "--service":
        return "/Applications/Crunch.app/Contents/Resources/zopflipng"
    else:
        return ZOPFLIPNG_CLI_PATH


def is_gui(arglist):
    return "--gui" in arglist or "--service" in arglist


def is_valid_png(filepath):
    # The PNG byte signature (https://www.w3.org/TR/PNG/#5PNG-file-signature)
    expected_signature = struct.pack("8B", 137, 80, 78, 71, 13, 10, 26, 10)
    # open the file and read first 8 bytes
    with open(filepath, "rb") as filer:
        signature = filer.read(8)
    # return boolean test result for first eight bytes == expected PNG byte signature
    return signature == expected_signature


def lock_init(ss_lock, log_lock, replace_original=False):
    # Based on approach described in
    # https://stackoverflow.com/a/25558333/2848172
    global stdstream_lock
    global logging_lock
    global REPLACE_ORIGINAL

    stdstream_lock = ss_lock
    logging_lock = log_lock
    REPLACE_ORIGINAL = replace_original


def log_error(errmsg):
    current_time = time.strftime("%m-%d-%y %H:%M:%S")
    if logging_lock:
        logging_lock.acquire()
    with open(LOGFILE_PATH, "a") as filewriter:
        filewriter.write(current_time + "\tERROR\t" + errmsg + os.linesep)
        filewriter.flush()
        os.fsync(filewriter.fileno())
    if logging_lock:
        logging_lock.release()


def log_info(infomsg):
    current_time = time.strftime("%m-%d-%y %H:%M:%S")
    if logging_lock:
        logging_lock.acquire()
    with open(LOGFILE_PATH, "a") as filewriter:
        filewriter.write(current_time + "\tINFO\t" + infomsg + os.linesep)
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

    # Get the last N lines
    tail_lines = lines[-num_lines:] if len(lines) > num_lines else lines
    print(f"--- Last {len(tail_lines)} lines of {LOGFILE_PATH} ---")
    for line in tail_lines:
        print(line.rstrip())


def shellquote(filepath):
    return "'" + filepath.replace("'", "'\\''") + "'"


def format_ansi_red(text):
    if sys.stdout.isatty():
        return "\033[0;31m" + text + "\033[0m"
    else:
        return text


def format_ansi_green(text):
    if sys.stdout.isatty():
        return "\033[0;32m" + text + "\033[0m"
    else:
        return text


# ///////////////////////
# OBJECT DEFINITIONS
# ///////////////////////


class ImageFile(object):
    def __init__(self, filepath):
        self.pre_filepath = filepath
        self.post_filepath = self._get_post_filepath()
        self.pre_size = self._get_filesize(self.pre_filepath)
        self.post_size = 0

    def _get_filesize(self, file_path):
        return os.path.getsize(file_path)

    def _get_post_filepath(self):
        path, extension = os.path.splitext(self.pre_filepath)
        return path + "-crunch" + extension

    def finalize_replacement(self):
        """Replace original file with optimized version."""
        if REPLACE_ORIGINAL and os.path.exists(self.post_filepath):
            # Remove the original file and rename the optimized file to take its place
            os.remove(self.pre_filepath)
            os.rename(self.post_filepath, self.pre_filepath)
            # Update post_size to reflect the replaced file
            self.post_size = self._get_filesize(self.pre_filepath)
            self.post_filepath = self.pre_filepath

    def get_post_filesize(self):
        self.post_size = self._get_filesize(self.post_filepath)

    def get_compression_percent(self):
        ratio = float(self.post_size) / float(self.pre_size)
        percent = ratio * 100
        return percent


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
