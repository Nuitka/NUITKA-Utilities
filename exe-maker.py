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

import sys
import os
import subprocess as sp
import shutil
import time

py2 = str is bytes

if py2:  # last tk/tcl qualifyers depend on Python version
    tk_lq = "tk8.5"
    tcl_lq = "tcl8.5"
    import PySimpleGUI27 as sg
else:
    tk_lq = "tk8.6"
    tcl_lq = "tcl8.6"
    import PySimpleGUI as sg

sep_line = "".ljust(80, "-")


def mini_skim(bin_dir, val):
    print("Scanning the 'dist' folder for removable items.")
    flist = os.listdir(bin_dir)
    candidates = [  # unnecessary in dist root folder
        "mkl_rt.dll",  # Intel MKL for numpy
        "tbb.dll",  # Intel MKL for numpy
    ]
    removed_files = []
    for f in flist:
        f = f.lower()  # prevent the awkward
        remove_fn = os.path.join(bin_dir, f)  # removal candidate

        # handle Tkinter
        if (
            (not val["tk-support"])
            and f.startswith(("tk", "tcl", "_tkinter"))
            and f.endswith((".dll", ".pyd"))
        ):
            os.remove(remove_fn)
            removed_files.append(f + " (Tk file)")
            continue

        # handle Qt libraries
        if not val["qt-support"]:
            if (
                os.path.isfile(remove_fn)
                and f.startswith("qt")
                and f.endswith((".dll", ".pyd"))
            ):
                os.remove(remove_fn)
                removed_files.append(f + " (Qt file)")
                continue

            if os.path.isdir(remove_fn) and f.startswith("pyqt"):
                shutil.rmtree(remove_fn, ignore_errors=True)
                removed_files.append(f + " (Qt folder)")
                continue

        if f in candidates:
            os.remove(remove_fn)
            removed_files.append(f + " (misplaced here)")

    if len(removed_files) == 0:
        print("No files or folders were removed.")
    else:
        print("Removed the following files or folders:")
        print(sep_line)
        for f in removed_files:
            print(os.path.join(bin_dir, f))
    print(sep_line)


def upx_compress(bin_dir):
    print("UPX Compression of binaries in folder '%s'" % bin_dir)
    try:
        print(sep_line)
        print("Checking availability of upx:\n", end="", flush=True)
        sp.call(("upx", "-qq"))  # test presence of upx
        print("OK: upx is available.")
        print(sep_line)
    except:
        return False
    tasks = []
    file_count = 0
    file_sizes = {}
    t0 = time.time()
    for root, _, files in os.walk(bin_dir):
        root = root.lower()
        for f in files:
            f = f.lower()
            fname = os.path.join(root, f)
            file_sizes[fname] = os.stat(fname).st_size
            if "qt-plugins" in root:
                continue
            if not f.endswith((".exe", ".dll", "pyd")):  # we only handle these
                continue
            if f.endswith(".dll"):
                if f.startswith("python"):
                    continue
                if f.startswith("vcruntime"):
                    continue
                if f.startswith("msvcp"):
                    continue
                if f.startswith("cldapi"):
                    continue
                if f.startswith("edp"):
                    continue

            # make the upx invocation command
            cmd = ("upx", "-9", fname)
            t = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.PIPE, shell=False)
            tasks.append(t)
            file_count += 1

    print(
        "Started %i compressions out of %i total files ..."
        % (file_count, len(file_sizes.keys())),
        flush=True,
    )

    for t in tasks:
        t.wait()

    t1 = int(round(time.time() - t0))
    print("Finished in %i seconds." % t1, flush=True)
    old_size = new_size = 0.0
    for f in file_sizes.keys():
        old_size += file_sizes[f]
        new_size += os.stat(f).st_size
    old_size *= 1.0 / 1024 / 1024
    new_size *= 1.0 / 1024 / 1024
    diff_size = old_size - new_size
    diff_percent = diff_size / old_size
    text = "\nFolder Compression Results (MB)\nbefore: {:.5}\nafter: {:.5}\nsavings: {:.5} ({:2.1%})"
    print(text.format(old_size, new_size, diff_size, diff_percent))
    print(sep_line)
    return True


sys_tcl = os.path.join(os.path.dirname(sys.executable), "tcl")
tk = os.path.join(sys_tcl, tk_lq)
tcl = os.path.join(sys_tcl, tcl_lq)
tkinter_available = os.path.exists(tk) and os.path.exists(tcl)
if not tkinter_available:
    try:
        tk = os.environ["TCL_LIBRARY"]
        tcl = os.environ["TCL_LIBRARY"]
        tkinter_available = os.path.exists(tk) and os.path.exists(tcl)
    except:
        pass


message = sg.Text("", size=(60, 1))
frm_input = sg.InputText("", key="py-file", do_not_clear=False)
frm_output = sg.InputText("", key="compile-to", do_not_clear=True)
frm_icon = sg.InputText("", key="icon-file", do_not_clear=True)
frm_follow = sg.InputText("", size=(60, 2), key="follow", do_not_clear=True)
frm_no_follow = sg.InputText("", size=(60, 2), key="no-follow", do_not_clear=True)
frm_packages = sg.InputText("", size=(60, 2), key="packages", do_not_clear=True)
frm_modules = sg.InputText("", size=(60, 2), key="modules", do_not_clear=True)
frm_plugins = sg.InputText("", size=(60, 2), key="plugin-dir", do_not_clear=True)
frm_more = sg.InputText("", key="add-args", size=(60, 2), do_not_clear=True)
form = sg.FlexForm("Nuitka Standalone EXE Generation")

compile_to = pscript = icon_file = ""

layout = [
    [
        sg.Text("Python Script:", size=(13, 1)),
        sg.InputText("", key="py-file", do_not_clear=True),
        sg.FileBrowse(button_text="...", file_types=(("Python Files", "*.py*"),)),
    ],
    [
        sg.Text("Output Folder:", size=(13, 1)),
        frm_output,
        sg.FolderBrowse(button_text="..."),
    ],
    [sg.Text("Icon File:", size=(13, 1)), frm_icon, sg.FileBrowse(button_text="...")],
    [
        sg.Text("App control:", size=(15, 1)),
        sg.Checkbox("Use Console", default=True, key="use-console"),
        sg.Checkbox("Tk Support", default=False, key="tk-support"),
        sg.Checkbox("Qt Support", default=False, key="qt-support"),
        sg.Checkbox("Numpy Support", default=False, key="np-support"),
    ],
    [
        sg.Text("Output control:", size=(15, 1)),
        sg.Checkbox("Remove <.build> folder", default=True, key="remove-build"),
        sg.Checkbox("Use UPX-Packer", default=False, key="compress"),
    ],
    [
        sg.Text("Dep. cache control:", size=(15, 1)),
        sg.Checkbox("Ignore", text_color="#FF0000", default=False, key="ignore-cache"),
        sg.Checkbox("Recurse", text_color="#FF0000", default=False, key="int-depend"),
        sg.Checkbox(
            "Rebuild", text_color="#FF0000", default=False, key="rebuild-cache"
        ),
    ],
    [sg.Text("No recurse into:", text_color="#FF0000", size=(13, 1)), frm_no_follow],
    [sg.Text("Recurse into:", size=(13, 1)), frm_follow],
    [sg.Text("Include packages:", size=(13, 1)), frm_packages],
    [sg.Text("Include modules:", size=(13, 1)), frm_modules],
    [sg.Text("Include plugin-dir:", size=(13, 1)), frm_plugins],
    [sg.Text("More Nuitka args:", size=(13, 1)), frm_more],
    [message],
    [sg.Submit(), sg.Cancel()],
]

form.Layout(layout)
while True:
    frm_input.Update(pscript)
    frm_output.Update(compile_to)
    frm_icon.Update(icon_file)
    btn, val = form.Read()
    if btn in (None, "Cancel"):
        break

    pscript = os.path.abspath(val["py-file"])
    if not os.path.exists(pscript):
        message.Update("Python script '%s' does not exist!" % pscript)
        pscript = ""
        continue

    icon_file = val["icon-file"]
    if icon_file and not os.path.exists(icon_file):
        message.Update("Icon file '%s' does not exist!" % icon_file)
        icon_file = ""
        continue

    compile_to = val["compile-to"]
    if compile_to:
        compile_to = os.path.abspath(compile_to)
        if not os.path.exists(compile_to):
            message.Update("Folder '%s' does not exist!" % compile_to)
            compile_to = ""
            continue

    if val["tk-support"] and not tkinter_available:
        message.Udate("Tkinter files are not available on this system!")
        continue

    break  # we have valid parameters and can start compile

form.Close()
if btn in (None, "Cancel"):
    raise SystemExit()

# ------------------------------------------------------------------------------
# start the compile
# ------------------------------------------------------------------------------

if icon_file:
    icon_file = os.path.abspath(icon_file)

pscript_n, ext = os.path.splitext(pscript)
pscript_dist = pscript_n + ".dist"
pscript_build = pscript_n + ".build"

cmd = ["python", "-m", "nuitka", "--standalone", "--python-flag=nosite"]

if not val["use-console"] or ext.lower() == ".pyw":
    cmd.append("--windows-disable-console")

if val["rebuild-cache"]:
    cmd.append("--force-dll-dependency-cache-update")

if val["ignore-cache"]:
    cmd.append("--disable-dll-dependency-cache")

if val["remove-build"]:
    cmd.append("--remove-output")

if icon_file:
    cmd.append('--windows-icon="%s"' % icon_file)

if compile_to:
    compile_to = os.path.abspath(compile_to)
else:
    compile_to = os.path.dirname(pscript)

pscript_dist = os.path.join(compile_to, os.path.basename(pscript_dist))
pscript_build = os.path.join(compile_to, os.path.basename(pscript_build))
output = '--output-dir="%s"' % compile_to
cmd.append(output)

if val["qt-support"]:
    cmd.append("--plugin-enable=qt-plugins")
else:
    cmd.append("--recurse-not-to=PIL.ImageQt")

if val["tk-support"]:
    cmd.append("--plugin-enable=tk-inter")
else:
    cmd.append("--recurse-not-to=PIL.ImageTk")

if val["np-support"]:
    cmd.append("--plugin-enable=numpy")
else:
    cmd.append("--recurse-not-to=numpy")

if val["follow"]:
    tab = val["follow"].split(",")
    for t in tab:
        if t:
            cmd.append("--recurse-to=" + t.strip())

if val["no-follow"]:
    tab = val["no-follow"].split(",")
    for t in tab:
        if t:
            cmd.append("--recurse-not-to=" + t.strip())

if val["packages"]:
    tab = val["packages"].split(",")
    for t in tab:
        if t:
            cmd.append("--include-package=" + t.strip())

if val["modules"]:
    tab = val["modules"].split(",")
    for t in tab:
        if t:
            cmd.append("--include-module=" + t.strip())

if val["plugin-dir"]:
    tab = val["plugin-dir"].split(",")
    for t in tab:
        if t:
            cmd.append("--include-plugin-directory=" + t.strip())

cmd.append("--experimental=use_pefile")

if val["int-depend"]:
    cmd.append("--experimental=use_pefile_recurse")
    cmd.append("--experimental=use_pefile_fullrecurse")

if val["add-args"]:
    cmd.append(val["add-args"])

cmd.append('"' + pscript + '"')
cmd = " ".join(cmd)

print(sep_line)
message = [
    "Now executing Nuitka as follows. Please be patient and let it finish!\n",
    cmd,
]
print("\n".join(message))
print(sep_line)

compile_start = time.time()  # start stop watch for the compile

rc = sp.Popen(cmd, shell=True)

sg.Popup(
    message[0],
    message[1],
    "Auto-closing this window ...",
    auto_close=True,
    auto_close_duration=5,
    non_blocking=False,
)

return_code = rc.wait()

compile_stop = time.time()  # start stop watch for the compile

if return_code != 0:
    message = ["Nuitka compile failed!", "Check its output!"]
    print("\n".join(message))
    sg.Popup(message[0], message[1])
    raise SystemExit()

print(sep_line)
compile_time = int(round(compile_stop - compile_start))
message = "Nuitka compile successful (%i sec) ..." % compile_time

mini_skim(pscript_dist, val)

if val["compress"]:
    rc = upx_compress(pscript_dist)
    if not rc:
        message += "\nUPX is not available on any path of this system!"

print(message)

sg.Popup(
    message,
    "The EXE file is in '%s'" % pscript_dist,
    auto_close=True,
    auto_close_duration=5,
)

