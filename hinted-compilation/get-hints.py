#     Copyright 2019, Jorj McKie, mailto:<jorj.x.mckie@outlook.de>
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
is wrapped by "hinter" logic (based on Kay Hayen's hints.py, see ), which
logs every import statement issued by the script. After end of the subprocess,
the logfile is interpreted, reduced to unique entries and then stored as a list
in JSON format.
"""

import os
import sys
import io
import json
import subprocess


def reader(f):
    """ Read and pre-process the output from hints.py.

    Args:
        f: the logfile created by hints.py

    Returns:
        A list with layout depending on record type.
    """
    text = "\n"
    while text == "\n":  # multiprocessing scripts may create empty lines
        text = f.readline()

    if text == "":  # end of file
        return []

    text = text[:-1]  # remove line break char

    tt = text.split(";")

    level = int(tt[0])  # nesting level
    type = tt[1]  # one of CALLED, RESULT or EXCEPTION

    if type == "RESULT":  # RESULT record
        olist = [level, type, tt[2], tt[3]]  # level, type, module, file descr

    elif type == "EXCEPTION":  # EXCEPTION record
        olist = [level, type, tt[2]]  # level, type, exception

    else:  # this is a CALL record
        CALLED = tt[2]  # the imported item
        implist = tt[3]  # any list following this: "None" or a "tuple"

        if implist == "None":
            implist = None

        else:  # turn tuple into list, so JSON accepts it
            implist = (
                implist.replace("(", "[")  # make list left bracket
                .replace(",)", "]")  # make list right bracket
                .replace(")", "]")  # take care of singular items
                .replace("'", '"')  # exchange quotes and apostrophies
            )
            try:
                implist = json.loads(implist)
            except:
                print("JSON problem:", implist)
                raise

        olist = [level, type, CALLED, implist]

    return olist


def call_analyzer(f, call_list, call_file, trace_logic):
    """ Analyze the call hierarchy to determine valid called names.
    Notes:
        Recursive function calling itself for every level change. Each CALL
        will be followed by exactly one RESULT (or EXCEPTION), potentially with
        interspersed CALL / RESULT pairs at lower levels.

    Args:
        f: file to read from (created by hints.py)
        call_list: list representing a CALL record
        call_file: output file to receive computed import names
        trace_logic: bool switching on tracing of the logic
    Returns:
        No direct returns, the output will be written to call_file.
    """

    def write_mod(t):
        call_file.write(t + "\n")
        if trace_logic:
            print(t)
        return

    level = call_list[0]  # nesting level
    CALLED = call_list[2]  # the imported module
    implist = call_list[3]  # list eventually accompanying the import

    text = reader(f)  # read next record

    if not bool(text):  # EOF should not happen here!
        sys.exit("unexpected EOF at %s" % str(call_list))

    while text[1] == "CALL":  # any more CALL records will be recursed into
        call_analyzer(f, text, call_file, trace_logic)
        text = reader(f)

    if text[0] != level:  # this record must have our level!
        sys.exit("unexpected level after %s" % str(call_list))

    if text[1] == "EXCEPTION":  # no output if the import caused an exception
        return

    if text[1] != "RESULT":  # this must be a RESULT now
        sys.exit("expected RESULT after %s" % str(call_list))

    RESULT = text[2]  # resulting module name
    res_file = text[3]  # resulting file name

    if res_file == "built-in":  # skip output for built-in stuff
        return

    if trace_logic:
        print(str(call_list))
        print(str(text))

    write_mod(RESULT)  # this is for sure

    if not CALLED:  # case: CALL name is empty
        if not implist:  # should not happen, but let's ignore this
            return
        if implist == ["*"]:  # return RESULT.*
            write_mod(RESULT + ".*")
            return
        for item in implist:  # return RESULT.item for items in list
            write_mod(RESULT + "." + item)
        return

    if (
        CALLED.startswith(RESULT)
        or RESULT.startswith(CALLED)
        or RESULT.endswith(CALLED)
    ):
        # CALL and RESULT names contain each other in some way
        if not implist:
            if CALLED != RESULT:
                write_mod(CALLED)
            return
        if CALLED == RESULT:
            cmod = CALLED
        elif RESULT.endswith(CALLED):
            cmod = RESULT
        elif RESULT.startswith(CALLED):
            cmod = RESULT
        else:
            cmod = CALLED
        if implist == ["*"]:  # everything under the module is okay
            write_mod(cmod + ".*")
            return
        for item in implist:  # it is a list of items
            write_mod(cmod + "." + item)
        return

    """ Case:
    RESULT and CALL names neither contain each other, nor is CALLED empty.
    We then assume that the true call name should be RESULT.CALLED in output.
    """
    cmod = RESULT + "." + CALLED  # equals RESULT.CALLED
    write_mod(cmod)  # output it
    if not implist:  # no list thtere: finished
        return
    if implist == ["*"]:  # include everything underneath
        write_mod(cmod + ".*")
        return
    for item in implist:  # or again a list of items
        write_mod(cmod + "." + item)
    return


def myexit(lname, trace_logic):
    """ Called after the application script finishes.

    Read the log file produced by hints.py and produce an array all imports.
    Entries in this array are unique. It will be stored with the name of
    the application and the "json" extension.
    """

    ifile = open(lname, newline=None)  # open the script's logfile
    ofile = io.StringIO()  # intermediate storage for json output

    while 1:  # read the logfile
        text = reader(ifile)
        if not bool(text):
            break
        call_analyzer(ifile, text, ofile, trace_logic)

    ifile.close()

    call_string = ofile.getvalue()  # read intermediate storage
    all_calls = call_string.split("\n")  # and split to single items

    netto_calls = sorted(list(set(all_calls)))  # reduce to sorted unique names
    # and store everything as an array using a JSON file
    if netto_calls[0] == "":  # remove the pesky null string
        del netto_calls[0]
    jsonfile = open(jname, "w")
    jsonfile.write(json.dumps(netto_calls))
    jsonfile.close()

    os.remove(lname)  # remove the script's logfile


# -----------------------------------------------------------------------------
# Main program
# -----------------------------------------------------------------------------
ifname = sys.argv[1]  # read name of to-be-traced script
if not bool(ifname) or not os.path.exists(ifname):
    sys.exit("no valid Python script provided")

jname = ifname[:-2] + "json"  # store hinted modules here
lname = ifname[:-2] + "log"  # logfile name for the script

# This text is executed. It activates the hinting logic and excutes the
# script via exec(script).
invoker_text = """\
import sys, os
original_import = __import__

_indentation = 0
_output = sys.stdout


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
    except AttributeError:
        file_desc = "built-in"

    return (module.__name__, file_desc)


def enableImportTracing(normalize_paths=True, show_source=False):
    def _ourimport(
        name,
        globals=None,
        locals=None,
        fromlist=None,  # @ReservedAssignment
        level=-1 if sys.version_info[0] < 2 else 0,
    ):
        builtins.__import__ = original_import

        global _indentation
        try:
            _indentation += 1

            print("%i;CALL;%s;%s" % (_indentation, name, fromlist), file=_output)

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
                print("%i;EXCEPTION;%s" % (_indentation, e), file=_output)
                raise
            finally:
                builtins.__import__ = original_import

            m = _moduleRepr(result)
            print("%i;RESULT;%s;%s" % (_indentation, m[0], m[1]), file=_output)

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

module = "&module"
lname = "&lname"
logfile = open(lname, "a")  # open the script to trace
_output = logfile
source = open(module).read()
enableImportTracing()
exec(source)
""".replace(
    "&module", ifname
).replace(
    "&lname", lname
)

hinter_script = "hint-exec.py"
# save the invoker script and start it via subprocess
invoker_file = open(hinter_script, "w")
invoker_file.write(invoker_text)
invoker_file.close()

if os.path.exists(lname):  # remove any old logfile
    os.remove(lname)

new_argv = ["python", "hint-exec.py"] + sys.argv[2:]
rc = subprocess.call(new_argv)

myexit(lname, False)  # transform logfile to JSON file

os.remove(hinter_script)
