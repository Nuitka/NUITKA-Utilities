#    Copyright 2019, Jorj McKie, mailto:jorj.x.mckie@outlook.de
#     Copyright 2019, Orsiris de Jong, mailto:ozy@netpower.fr
#
#     Part of "Nuitka", an optimizing Python compiler that is compatible and
#     integrates with CPython, but also works on its own.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
"""
This script creates an executable out of the "dist" folder of a Python program,
which has been compiled by Nuitka in standalone mode. This is also known as
"One-File-Distribution".

The executable contains the compressed dist folder and is named like the
script, i.e. "script.exe", and put in the same directory, where the dist
folder lives.

When the installation file is executed, the dist folder is

(1) decompressed in the user's temp directory (envireonment variable $TEMP)
(2) the original 'script.exe' is invoked, passing in any provided arguments
(3) after 'script.exe' has finished, the dist folder is removed again

The following handling option is also available:

Execute the distribution file with parameter '/D=...' by specifying a
directory. This folder will then be used to store 'dist', and the original
script will not be executed as part of the installation process.

Dependencies
------------
* PySimpleGUI
* The program **NSIS** is required to generate the installation file. It can be
  downloaded from here: https://nsis.sourceforge.io/Main_Page.

"""
import sys
import os
import time
import getopt
from fnmatch import fnmatch
import subprocess
import shutil

_GUI = True

try:
    import PySimpleGUI as psg
except ModuleNotFoundError:
    print(
        "Cannot find PySimleGUI. Running as non UI version. Try running [%s -h] for usage."
        % sys.argv[0]
    )
    _GUI = False


def glob_path_match(path, pattern_list):
    """
    Checks if path is in a list of glob style wildcard paths
    :param path: path of file / directory
    :param pattern_list: list of wildcard patterns to check for
    :return: Boolean
    """
    return any(fnmatch(path, pattern) for pattern in pattern_list)


def get_files_recursive(
    root,
    d_exclude_list=None,
    f_exclude_list=None,
    ext_exclude_list=None,
    primary_root=None,
):
    """
    Walk a path to recursively find files
    Modified version of https://stackoverflow.com/a/24771959/2635443 that includes exclusion lists
    and accepts glob style wildcards on files and directories
    :param root: path to explore
    :param d_exclude_list: list of root relative directories paths to exclude
    :param f_exclude_list: list of filenames without paths to exclude
    :param ext_exclude_list: list of file extensions to exclude, ex: ['.log', '.bak']
    :param primary_root: Only used for internal recursive exclusion lookup, don't pass an argument here
    :return: list of files found in path
    """

    if d_exclude_list is not None:
        # Make sure we use a valid os separator for exclusion lists, this is done recursively :(
        d_exclude_list = [os.path.normpath(d) for d in d_exclude_list]
    else:
        d_exclude_list = []
    if f_exclude_list is None:
        f_exclude_list = []
    if ext_exclude_list is None:
        ext_exclude_list = []

    files = [
        os.path.join(root, f)
        for f in os.listdir(root)
        if os.path.isfile(os.path.join(root, f))
        and not glob_path_match(f, f_exclude_list)
        and os.path.splitext(f)[1] not in ext_exclude_list
    ]
    dirs = [d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))]
    for d in dirs:
        p_root = os.path.join(primary_root, d) if primary_root is not None else d
        if not glob_path_match(p_root, d_exclude_list):
            files_in_d = get_files_recursive(
                os.path.join(root, d),
                d_exclude_list,
                f_exclude_list,
                ext_exclude_list,
                primary_root=p_root,
            )
            if files_in_d:
                for f in files_in_d:
                    files.append(os.path.join(root, f))
    return files


def get_lzma_dict_size(directory):
    # Returns lzma dict (in MB) size based on approx of files size

    # Get dist size (bytes to MB by shr 20)
    # Lets assume that dict should be 2 <= dist_size <= 128 MB
    total_dist_size = 0
    for file in get_files_recursive(directory):
        if not os.path.islink(file):
            total_dist_size += os.path.getsize(file) >> 20

    # Compute best dict size for compression
    factor = 2
    while (total_dist_size / factor > 1) and factor < 128:
        factor *= 2
    return "%i" % factor


def command_runner(
    command, valid_exit_codes=None, timeout=30, shell=False, decoder="utf-8"
):
    """
    command_runner 2019011001
    Whenever we can, we need to avoid shell=True in order to preseve better security
    Runs system command, returns exit code and stdout/stderr output, and logs output on error
    valid_exit_codes is a list of codes that don't trigger an error
    """

    try:
        # universal_newlines=True makes netstat command fail under windows
        # timeout may not work on linux
        # decoder may be unicode_escape for dos commands or utf-8 for powershell
        output = subprocess.check_output(
            command,
            stderr=subprocess.STDOUT,
            shell=shell,
            timeout=timeout,
            universal_newlines=False,
        )
        output = output.decode(decoder, errors="ignore")
    except subprocess.CalledProcessError as exc:
        exit_code = exc.returncode
        try:
            output = exc.output
            try:
                output = output.decode(decoder, errors="ignore")
            except Exception as subexc:
                print(subexc)
        except Exception:
            output = "command_runner: Could not obtain output from command."
        if exit_code in valid_exit_codes if valid_exit_codes is not None else [0]:
            print(
                "Command [%s] returned with exit code [%s]. Command output was:"
                % (command, exit_code)
            )
            if output:
                print(output)
            return exc.returncode, output
        else:
            print(
                "Command [%s] failed with exit code [%s]. Command output was:"
                % (command, exc.returncode)
            )
            print(output)
            return exc.returncode, output
    # OSError if not a valid executable
    except OSError as exc:
        print("Command [%s] returned:\n%s." % (command, exc))
        return None, exc
    except subprocess.TimeoutExpired:
        print(
            "Timeout [%s seconds] expired for command [%s] execution."
            % (timeout, command)
        )
        return None, "Timeout of %s seconds expired." % timeout
    else:
        print("Command [%s] returned with exit code [0]. Command output was:" % command)
        if output:
            print(output)
        return 0, output


def reduce_nuitka_dist(source_dir, dest_dir):
    NUITKA_EXCLUDE_FILES = [
        "_asyncio.pyd",
        "_contextvars.pyd",
        "_decimal.pyd",
        "_elementtree.pyd",
        "_msi.pyd",
        "_multiprocessing.pyd",
        "_overlapped.pyd",
        "_sqlite3.pyd",
        "sqlite3.dll",
        "api-ms-win*",
    ]

    NUITKA_EXCLUDE_DIRS = [
        "tk/demos",
        "tk/images",
        "tk/msgs",
        "tcl/encoding",
        "tcl/msgs",
        "tcl/tzdata",
    ]

    dist_files = get_files_recursive(
        source_dir, NUITKA_EXCLUDE_DIRS, NUITKA_EXCLUDE_FILES
    )
    for file in dist_files:
        absolute_dest_filepath = file.replace(source_dir, dest_dir)

        if not os.path.isdir(os.path.dirname(absolute_dest_filepath)):
            os.makedirs(os.path.dirname(absolute_dest_filepath))
        shutil.copyfile(file, absolute_dest_filepath)


def help():
    print(
        "\nNuitka utilities one file SFX creator",
        "\nWritten in 2019 by Jorj McKie, <jorj.x.mckie@outlook.de> and Orsiris de Jong, <ozy@netpower.fr>\n"
        "\nUsage:\n",
        "%s [OPTIONS] --dist=c:\\path\\to\\nuitka\\dist\\directory\n" % sys.argv[0],
        "\n",
        "OPTIONS:\n",
        "--icon=           Path to SFX icon file (.ico)\n",
        "--uac=            Uac level (may be admin or user)\n",
    )


nsi = """!verbose 1 ; Need to stay verbose on file creation
!define SFX_VERSION 2.0.0.1

Unicode True
SilentInstall silent

; One may pass and /DICON=iconfile.ico to makensis
!ifdef ICON
  Icon ${ICON}
!endif

!ifdef UAC
  RequestExecutionLevel ${UAC}
!else
  RequestExecutionLevel user
!endif

Name ${NAME}
OutFile "${SFXOUTPUT}"

VIProductVersion ${SFX_VERSION}
VIFileVersion ${SFX_VERSION}

VIAddVersionKey ProductName "${PRODUCT}"
;VIAddVersionKey Comments ""
VIAddVersionKey CompanyName "Nuitka"
VIAddVersionKey LegalTrademarks "${PRODUCT} is a trademark of NetPOWER IC"
VIAddVersionKey FileDescription "This is the ${PRODUCT} installer program"
VIAddVersionKey LegalCopyRight "(C) 2017-2019 Orsiris de Jong / NetPOWER.fr"
VIAddVersionKey FIleVersion "2.0.2.0"
VIAddVersionKey InternalName "${PRODUCT}-$[IMFVERSION}"
VIAddVersionKey OriginalFileName "${NAME}"

SetCompress force
SetCompress force
; /SOLID gives better compression results, /FINAL overrides any other compression calls
SetCompressor /SOLID /FINAL lzma
!ifndef DICTSIZE
  !define DICTSIZE 4
!endif
SetCompressorDictSize ${DICTSIZE}
SetDatablockOptimize on



Section ""
  ; $PluginsDir is a temp directory that gets deleted once execution is finished
  InitPluginsDir

  SetOutPath $PluginsDir
  File /r "${SOURCEDIR}\"
  
  ExecWait '"$PluginsDir\${SFXEXECUTABLE}"'
  
SectionEnd
"""
sep_line = "-" * 80
# NSIS script compiler (standard installation location)

makensis = r"C:\Program Files (x86)\NSIS\makensis.exe"
if not os.path.isfile(makensis):
    # or just this if on path:
    makensis = "makensis.exe"
if not os.path.isfile(makensis):
    raise SystemExit("Makensis is not available in [%s]. Please install it." % makensis)

try:
    opts, args = getopt.getopt(
        sys.argv[1:], "h?", ["dist=", "icon=", "filename=", "uac="]
    )
except getopt.GetoptError as e:
    raise SystemExit("Bogus arguments given. [%s]" % e)

dist_given = False

for opt, arg in opts:
    if opt == "-h":
        help()
        sys.exit(0)
    if opt == "--dist":
        if os.path.isdir(arg):
            dist = arg
            dist_given = True
        else:
            raise SystemExit("Dist directory [%s] not found." % arg)
    elif opt == "--uac":
        if arg != "admin" and arg != "user":
            raise SystemExit("Bogus uac [%s] given." % arg)
        else:
            uac = arg
    elif opt == "--icon":
        if os.path.isfile(arg):
            icon = arg
        else:
            raise SystemExit("Icon file [%s] not found." % arg)

if not dist_given and _GUI is True:
    layout = [
        [
            psg.Text("Dist directory"),
            psg.InputText(
                key="dist", do_not_clear=True, enable_events=True, size=(50, 1)
            ),
            psg.FolderBrowse(target="dist"),
        ],
        [
            psg.Text("Optional Icon "),
            psg.InputText(
                key="icon", do_not_clear=True, enable_events=True, size=(50, 1)
            ),
            psg.FileBrowse(target="icon"),
        ],
        [psg.Text("UAC level     "), psg.InputCombo(["user", "admin"], key="uac")],
        [psg.Button("OK"), psg.Button("Exit")],
    ]

    window = psg.Window("One file maker Nuitka").Layout(layout)
    window.Finalize()

    while True:
        event, values = window.Read(timeout=1000)
        if event is "OK":
            dist = values["dist"]
            if not os.path.isdir(dist):
                psg.Popup("Directory [%s] does not exist" % dist)
            else:
                dist_given = True
                icon = values["icon"]
                uac = values["uac"]
                break
        elif event is "Exit":
            break
elif not dist_given:
    raise SystemExit("Cannot make one-file executable.")

if not dist_given:
    raise SystemExit("No dist directory given.")

try:
    if not os.path.isdir(dist) or not dist.endswith(".dist"):
        raise SystemExit("[%s] is not a Nuitka dist folder." % dist)
except TypeError:
    raise SystemExit("[%s] is not a Nuitka dist folder (bogus value given)." % dist)

dist = os.path.abspath(dist)
# Reduce nuitka distribution by removing non necessary TK and dll files
reduce_nuitka_dist(dist, dist + ".reduced")
dist = dist + ".reduced"

# Get distribution size in multiple of 2 megabytes
lzma_dict_size = get_lzma_dict_size(dist)

executable_file = (
    os.path.basename(dist).split(".")[0] + ".exe"
)  # basename of dist folder
executable_path = os.path.dirname(dist)  # directory part of dist
nsi_source_dir = os.path.join(dist, "*")
sfx_outputfile = os.path.join(executable_path, executable_file)

# put NSIS installation script to a file
nsi_filename = dist + ".nsi"
nsi_file = open(nsi_filename, "w")
nsi_file.write(nsi)
nsi_file.close()

optional_args = ""
try:
    if icon is not None and icon != "":
        optional_args = "/DICON=%s" % icon
except (NameError, ValueError, TypeError):
    pass

try:
    if uac is not None and uac != "":
        optional_args = "%s /DUAC=%s" % (optional_args, uac)
except (NameError, ValueError, TypeError):
    pass

nsis_command = (
    '"%s" /DNAME="%s" /DSFXOUTPUT="%s" /DSOURCEDIR="%s" /DSFXEXECUTABLE="%s" /DDICTSIZE="%s" %s "%s"'
    % (
        makensis,
        executable_file,
        sfx_outputfile,
        nsi_source_dir,
        executable_file,
        lzma_dict_size,
        optional_args,
        nsi_filename,
    )
)


t0 = time.time()
print("Running command [%s]. Please wait, this may take some time.\n" % nsis_command)
exit_code, output = command_runner(nsis_command, timeout=900)

t1 = time.time()
print(
    sep_line,
    "\nOneFile generation return code:",
    exit_code,
    "\nDuration: %i sec." % int(round(t1 - t0)),
)

# Cleanup temporary nsi file and reduced dist directory
if os.path.isfile(nsi_filename):
    os.remove(nsi_filename)
if os.path.isdir(dist) and dist.endswith(".reduced"):
    shutil.rmtree(dist)
