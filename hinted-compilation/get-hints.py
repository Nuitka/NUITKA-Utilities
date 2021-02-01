#! /usr/bin/env python
#  -*- coding: utf-8 -*-

#     Copyright 2019-2020, Jorj McKie, mailto:<jorj.x.mckie@outlook.de>
#     Copyright 2019-2020, Orsiris de Jong, mailto:<ozy@netpower.fr>
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
""" This script creates a log file of import statements that a program executes.

The log file (which is in JSON format) can be used as input for "profile guided
optimization" by the Nuitka compiler.
Currently, there is a user plugin which - based on this log file - controls the
inclusion of modules during Nuitka standalone compile mode.

The logfile creation is done within a separate process. The script to be traced
is wrapped by "hinter" logic (based on Kay Hayen's hints.py,
see https://github.com/Nuitka/Nuitka/blob/develop/lib/hints.py), which
logs every import statement issued by the script. After end of the subprocess,
the logfile is interpreted, reduced to unique entries and then stored as a dict
in JSON format.
"""
import os
import sys
import io
import json
import subprocess
from operator import itemgetter
from nuitka.utils.FileOperations import hasFilenameExtension
from nuitka.utils.Importing import getSharedLibrarySuffix

line_number = 0  # global variable for tracing purposes

# accept everything within these packages:
accept_always = ("importlib_metadata", "pytest", "_pytest")


def reader(f):
    """ Read and pre-process the output from hints.py.

    Args:
        f: the logfile created by hints.py

    Returns:
        A list with a layout which depends on the 3 record types:
        1: [level, "CALL", called-item, list]
        2: [level, "RESULT", module, module-file]
        3: [level, "EXCEPTION", exception]
    """
    global line_number

    text = f.readline()
    line_number += 1

    if text == "":  # end of file
        return []

    if text.endswith("\n"):
        text = text[:-1]  # remove line break char

    tt = text.split(";")
    if (
            len(tt) not in (3, 4)
            or not tt[0].isalnum()
            or tt[1] not in ("CALL", "RESULT", "EXCEPTION")
    ):
        print("invalid record %i %s" % (line_number, text))
        print("resulted in tt:", tt)
        sys.exit("cancelling")

    level = int(tt[0])  # nesting level
    type = tt[1]  # one of CALLED, RESULT or EXCEPTION

    if type == "RESULT":  # RESULT record
        olist = [level, type, tt[2], tt[3]]  # level, type, module, file descr
        return olist

    if type == "EXCEPTION":  # EXCEPTION record
        olist = [level, type, tt[2]]  # level, type, exception
        return olist

    # this is a CALL record
    CALLED = tt[2]  # the imported item
    implist = tt[3]  # any list following this, may be "None" or a "tuple"

    if implist == "None":
        implist = None
    else:  # turn tuple into a list, so JSON accepts it
        implist = (
            implist.replace("(", "[")  # make list left bracket
                .replace(",)", "]")  # make list right bracket
                .replace(")", "]")  # take care of singular item tuple
                .replace("'", '"')  # exchange quotes and apostrophies
        )
        try:
            implist = json.loads(implist)
        except (ValueError, TypeError):
            print("JSON problem:", implist)
            print("line:", line_number)
            print("tt:", tt)
            raise

    olist = [level, type, CALLED, implist]
    return olist


def call_analyzer(f, call_list, import_calls, import_files, trace_logic):
    """ Analyze the call hierarchy to determine valid called names.

    Notes:
        Always called with a CALL record type.
        Recursive function calling itself for every level change. Each CALL on
        each level will be followed by exactly one RESULT (or EXCEPTION),
        potentially with interspersed CALL / RESULT pairs at lower levels.

    Args:
        f: file to read from (created by the script wrapped in hinting logic)
        call_list: list representing a CALL record
        import_calls: list to receive computed import names
        import_files: list to receive imported files
        trace_logic: bool to switch on tracing the logic
    Returns:
        No direct returns, output will be written to call_file.
    """
    global line_number

    def normalize_file(t):
        # step 1: remove any platform tags from shared libraries
        folder = os.path.dirname(t)  # folder part
        datei = os.path.basename(t)  # filename
        _, ext = os.path.splitext(datei)  # extension
        if ext in (".pyd", ".so"):  # shared library?
            datei_arr = datei.split(".")  # split
            if len(datei_arr) > 2:  # platform tag present?
                datei = ".".join(datei_arr[:-2])  # yes, omit
            else:
                datei = ".".join(datei_arr[:-1])  # just omit ext

        t = os.path.join(folder, datei)  # rebuild filename for step 2

        # step 2: turn slashes into '.', remove __init__.py and extensions
        t = t.replace("\\", ".").replace("/", ".").replace("$PYTHONPATH.", "")
        if t.endswith(".__init__.py"):
            t = t[:-12]
            return t

        if t.endswith(".py"):
            t = t[:-3]
            return t

        if ext not in (".pyd", ".so"):
            sys.exit("found unknown Python module type '%s'" % t)

        return t

    def write_mod(t, f):  # write a call entry
        import_calls.append((t, f))
        if trace_logic:
            print(line_number, "call:", t)
        return

    def write_file(t):  # write a file entry
        import_files.append(t)
        if trace_logic:
            print(line_number, "file:", t)
        return

    level = call_list[0]  # nesting level
    CALLED = call_list[2]  # the imported module
    implist = call_list[3]  # list accompanying the import statement

    text = reader(f)  # read the next record

    if not bool(text):  # EOF should not happen here!
        print("unexpected EOF at %s" % str(call_list))
        sys.exit("line number %i" % line_number)

    if len(text) < 3:
        print("unexpected record format", text)
        sys.exit("at line number %i" % line_number)

    while "CALL" in text:  # any CALL records will be recursed into
        call_analyzer(f, text, import_calls, import_files, trace_logic)
        text = reader(f)

    if len(text) < 3:
        return

    if text[0] != level:  # this record should have our level!
        matching = False
    else:
        matching = True

    if text[1] == "EXCEPTION":  # no output if an exception resulted
        return

    if text[1] != "RESULT":  # this must be a RESULT now
        sys.exit("%i: expected RESULT after %s" % (line_number, str(call_list)))

    RESULT = text[2]  # resulting module name
    if RESULT == "__main__":  # skip current script
        return

    res_file = text[3]  # resulting file name
    if res_file == "built-in":  # skip output for built-in stuff
        return

    if res_file.endswith(".dll"):  # special handling for pythoncom and friends
        res_file = RESULT + ".py"

    if RESULT.startswith("win32com"):  # special handling for win32com
        res_file = "$PYTHONPATH\\win32com\\__init__.py"

    if trace_logic:
        print(line_number, ":", str(call_list))
        print(line_number, ":", str(text))

    normalized_file = normalize_file(res_file)
    write_file(normalized_file)

    if not matching:
        print("No result matches %i, %s, %s" % (level, CALLED, str(implist)))
    write_mod(RESULT, normalized_file)  # this is a sure output

    # members of shared modules cannot be filtered out, so allow them all
    # TODO: This should consider all possible suffixes, should it not.
    if (
            hasFilenameExtension(res_file, getSharedLibrarySuffix(preferred=True))  # a shared module!
            or normalized_file in accept_always
    ):
        write_mod(RESULT + ".*", normalized_file)
        return

    if not CALLED:  # case: the CALL name is empty
        if not implist:  # should not happen, but let's ignore this
            return
        for item in implist:  # return RESULT.item for items in list
            write_mod(RESULT + "." + item, normalized_file)
        return

    if (
            CALLED.startswith(RESULT)
            or RESULT.startswith(CALLED)
            or RESULT.endswith(CALLED)
    ):
        # CALL and RESULT names contain each other in some way
        if not implist:
            if CALLED != RESULT:
                write_mod(CALLED, normalized_file)
            return
        if CALLED == RESULT:
            cmod = CALLED
        elif RESULT.endswith(CALLED):
            cmod = RESULT
        elif RESULT.startswith(CALLED):
            cmod = RESULT
        else:
            cmod = CALLED
        for item in implist:  # this is a list of items
            write_mod(cmod + "." + item, normalized_file)
        return

    """ Case:
    RESULT and CALL names neither contain each other, nor is CALLED empty.
    We then assume that the true call name should be RESULT.CALLED in output.
    """
    cmod = RESULT + "." + CALLED  # equals RESULT.CALLED
    write_mod(cmod, normalized_file)  # output it
    if not implist:  # no list there: done
        return
    for item in implist:  # or again a list of items
        write_mod(cmod + "." + item, normalized_file)
    return


def clean_json(netto_calls):
    """ Remove tautological entries in the hinted imports list.

    Notes:
        The input list must sorted. Whenever an entry ending with ".*" is
        found, subsequent entries starting with the same string (excluding the
        asterisk) are skipped. Also cross-check against imported files to
        filter out items that are not callable.
        This approach leads to a much shorter array of accepted imports,
        and thus faster checks.
    """

    # step 1: remove items already covered via a *-import
    list_out = []  # intermediate list
    last_item = None  # store 'a.b.c.' here, if 'a.b.c.*' is found

    for x in netto_calls:
        if last_item and x.startswith(last_item):  # included in a "*" import?
            continue  # skip it
        list_out.append(x)  # else keep it
        if x.endswith(".*"):  # another *-import?
            last_item = x[:-1]  # refresh pattern
    temp_list = [x for x in list_out if x + ".*" in list_out]
    for x in temp_list:
        list_out.remove(x)
    print("Call cleaning has removed %i items." % (len(netto_calls) - len(list_out)))
    return list_out


def myexit(lname, jname, trace_logic):
    """ Called after the application script finishes.

    Read the log file produced by hints.py and produce an array all imports.
    Entries in this array are unique. It will be stored with the name of
    the application and the "json" extension.
    """

    ifile = open(lname)  # open the script's (accumulated) logfile
    import_calls = []  # intermediate storage for json output
    import_files = []  # intermediate storage for json output 2

    while 1:  # read the logfile
        text = reader(ifile)
        if not bool(text):
            break
        call_analyzer(ifile, text, import_calls, import_files, trace_logic)

    ifile.close()

    # make a list of all files that were referenced by an import
    netto_files = sorted(list(set(import_files)))

    # remove unnecessary reference to main module
    hinter_name, _ = os.path.splitext(os.path.basename(lname))
    hinter_name = "hinted-" + hinter_name
    if hinter_name in netto_files:
        netto_files.remove(hinter_name)

    # make a list of all items that were referenced by an import
    netto_calls = [x[0] for x in import_calls if x[1] != hinter_name]
    netto_calls = sorted(list(set(netto_calls)))

    # remove items which do not increase the compiled material
    cleaned_list = clean_json(netto_calls)
    js_dict = {"calls": cleaned_list, "files": netto_files}

    jsonfile = open(jname, "w")
    jsonfile.write(json.dumps(js_dict))
    jsonfile.close()


# -----------------------------------------------------------------------------
# Main program
# -----------------------------------------------------------------------------
timeout = 5 * 60 # default timeout 5 minutes
if sys.argv[1] == "--timeout":
    try:
        timeout = int(sys.argv[2])
        if timeout <= 0: timeout = None
        else: timeout *= 60
        del sys.argv[1:3]
    except:
        sys.exit("Invalid timeout value (specify positive integer for timeout in minutes, use 0 to turn off timeout)")
if timeout and timeout > 0: print("Process run will timeout in %d minutes" % (timeout/60))

try:
    ifname = sys.argv[1]  # read name of to-be-traced script
except:
    ifname = None
if not os.path.exists(ifname):
    sys.exit("no valid Python script provided")
else:
    ifname = os.path.abspath(ifname)

ifpath = os.path.dirname(os.path.abspath(ifname))
ifbasename = os.path.basename(os.path.abspath(ifname))

scriptname, extname = os.path.splitext(ifname)
scriptname = scriptname.replace('\\', '/')
jname = "%s-%i%i-%s-%i.json" % (
    scriptname,
    sys.version_info.major,
    sys.version_info.minor,
    sys.platform,
    64 if sys.maxsize > 2 ** 32 else 32,
)  # store hinted modules here

lname = scriptname + ".log"  # logfile name for the script

hinter_pid = str(os.getpid())

# This text is executed. It activates the hinting logic and then excutes the
# script via exec(script).
invoker_text = """#! /usr/bin/env python
#  -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import
import sys, os
original_import = __import__

_indentation = 0


def _normalizePath(path):
    path = os.path.abspath(path)

    best = None

    for path_entry in sys.path:
        if path.startswith(path_entry):
            if best is None or len(path_entry) > len(best):
                best = path_entry

    if best is not None:
        path = path.replace(best, "$PYTHONPATH")

    return path


def _moduleRepr(module):
    try:
        module_file = module.__file__
        module_file = module_file.replace(".pyc", ".py")

        if module_file.endswith(".so"):
            module_file = os.path.join(
                os.path.dirname(module_file),
                os.path.basename(module_file).split(".")[0] + ".so",
            )

        file_desc = _normalizePath(module_file).replace(".pyc", ".py")
    except AttributeError as exc:
        file_desc = "built-in"
    return (module.__name__, file_desc)


def enableImportTracing(normalize_paths=True, show_source=False):
    def _ourimport(
        name,
        globals=None,
        locals=None,
        fromlist=None,  # @ReservedAssignment
        level=-1 if sys.version_info[0] < 3 else 0,
    ):
        builtins.__import__ = original_import

        global logfile
        global _indentation
        try:
            _indentation += 1

            logfile.write("%i;CALL;%s;%s\\n" % (_indentation, name, fromlist))

            for entry in traceback.extract_stack()[:-1]:
                if entry[2] == "_ourimport":
                    continue
                else:
                    entry = list(entry)

                    if not show_source:
                        del entry[-1]
                        del entry[-1]

                    if normalize_paths:
                        entry[0] = _normalizePath(entry[0])

            builtins.__import__ = _ourimport
            try:
                result = original_import(name, globals, locals, fromlist, level)
            except ImportError as e:
                logfile.write("%i;EXCEPTION;%s\\n" % (_indentation, e))
                result = None
                raise

            if result is not None:
                m = _moduleRepr(result)
                logfile.write("%i;RESULT;%s;%s\\n" % (_indentation, m[0], m[1]))

            builtins.__import__ = _ourimport

            return result
        finally:
            _indentation -= 1

    try:
        import __builtin__ as builtins
    except ImportError:
        import builtins

    import traceback

    builtins.__import__ = _ourimport

scriptname = r"&scriptname"
extname = "&extname"
hinter_pid = "&hinter_pid"
lname = "%s-%s-%s.log" % (scriptname, hinter_pid, os.getpid())  # each process has its logfile
logfile = open(lname, "w", buffering=1)
hints_logfile = logfile
source_file = open(scriptname + extname, encoding='utf-8')
source = source_file.read()
source_file.close()
enableImportTracing()
exec(source)
""".replace(
    "&scriptname", scriptname
).replace(
    "&extname", extname
).replace(
    "&hinter_pid", hinter_pid
)

hinter_script = os.path.join(ifpath, "hinted-" + os.path.basename(scriptname) + extname)

# save the invoker script and start it via subprocess
invoker_file = open(hinter_script, "w")
invoker_file.write(invoker_text)
invoker_file.close()

if os.path.exists(lname):  # remove any old logfile
    os.remove(lname)

python_exe = sys.executable  # use the Python we are running under
if extname == ".pyw":  # but respect a different extension
    python_exe = python_exe.replace("python.exe", "pythonw.exe")

new_argv = [python_exe, hinter_script] + sys.argv[2:]

try:
    proc = subprocess.Popen(new_argv)
    proc.wait(timeout=timeout)
except Exception as e:
    print("exception '%s' for subprocess '%s'!" % (str(e), hinter_script))
    print("processing output nonetheless ...")

# multiple logfiles may have been created - we join them into a single one
log_files = [f for f in os.listdir(ifpath) if os.path.isfile(os.path.join(ifpath, f)) and f.endswith('.log') and
             '%s-%s' % (os.path.basename(scriptname), hinter_pid) in f]

with open(lname, "w")  as logfile:  # the final logfile
    for logname in log_files:
        full_logname = os.path.join(ifpath, logname)
        with open(full_logname) as lfile:
            for line in lfile.readlines():
                if any(("CALL" in line, "RESULT" in line, "EXCEPTION" in line)):
                    logfile.writelines(line)
        os.remove(full_logname)


myexit(lname, jname, False)  # transform logfile to JSON file

os.remove(lname)  # remove the script's logfile
os.remove(hinter_script)  # remove stub file
