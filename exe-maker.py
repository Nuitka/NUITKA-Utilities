import sys, os, subprocess, shutil, time

py2 = str is bytes

if py2:                      # last tk/tcl qualifyers depend on Python version
    tk_lq  = "tk8.5"
    tcl_lq = "tcl8.5"
else:
    tk_lq  = "tk8.6"
    tcl_lq = "tcl8.6"

import PySimpleGUI as sg

sys_tcl = os.path.join(os.path.dirname(sys.executable), "tcl")
tk  = os.path.join(sys_tcl, tk_lq)
tcl = os.path.join(sys_tcl, tcl_lq)
tkinter_available = os.path.exists(tk) and os.path.exists(tcl)
if not tkinter_available:
    try:
        tk = os.environ["TCL_LIBRARY"]
        tcl = os.environ["TCL_LIBRARY"]
        tkinter_available = os.path.exists(tk) and os.path.exists(tcl)
    except:
        pass


sep_line = "".ljust(80, "-")
message = sg.Text("", size=(60,1))
frm_input = sg.InputText("", key="py-file", do_not_clear=False)
frm_output = sg.InputText("", key="compile-to", do_not_clear=True)
frm_icon = sg.InputText("", key="icon-file", do_not_clear=True)
frm_follow = sg.InputText("", size=(60,2), key="follow", do_not_clear=True)
frm_no_follow = sg.InputText("", size=(60,2), key="no-follow", do_not_clear=True)
form = sg.FlexForm('Nuitka Standalone EXE Generation')

compile_to = pscript = icon_file = ""

layout = [
    [sg.Text("Python Script:", size=(12,1)),
     sg.InputText("", key="py-file", do_not_clear=True),
     sg.FileBrowse(button_text="...", file_types=(("Python Files","*.py*"),))],
    [sg.Text("Output Folder:", size=(12,1)),
     frm_output,
     sg.FolderBrowse(button_text="...")],
    [sg.Text("Icon File:", size=(12,1)),
     frm_icon,
     sg.FileBrowse(button_text="...")],
    [sg.Checkbox("Use Console", default=True, key="use-console"),
     sg.Checkbox("Tk Support", default=False, key="tk-support"),
     sg.Checkbox("Qt Support", default=False, key="qt-support"),],
    [sg.Text("Follow imports (comma-separated):")],
    [frm_follow],
    [sg.Text("Do NOT follow these:")],
    [frm_no_follow],
    [sg.Text("Other Nuitka args:")],
    [sg.InputText("", key="add-args", size=(60,2), do_not_clear=True)],
    [message],
    [sg.Submit(), sg.Cancel()]
]

form.Layout(layout)
while True:
    frm_input.Update(pscript)
    frm_output.Update(compile_to)
    frm_icon.Update(icon_file)
    btn, val = form.Read()

    if btn == "Cancel":
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
    if compile_to and not os.path.exists(compile_to):
        message.Update("Output foler '%s' does not exist." % compile_to)
        compile_to = ""
        continue

    if val["tk-support"] and not tkinter_available:
        message.Udate("Tkinter files are not available on this system!")
        continue

    if not compile_to and val["tk-support"]:
        message.Update("Need an 'Output Folder' for Tkinter support!")
        continue

    break


form.Close()
if btn == "Cancel":
    raise SystemExit()

if icon_file:
    icon_file = os.path.abspath(icon_file)

pscript_n, ext = os.path.splitext(pscript)
pscript_dist = pscript_n + ".dist"
pscript_build = pscript_n + ".build"

if compile_to:
    compile_to = os.path.abspath(compile_to)

if compile_to == pscript_dist:
    compile_to = None

if compile_to:
    compile_bin = os.path.join(compile_to, "bin")
    compile_lib = os.path.join(compile_to, "lib")
    if not os.path.exists(compile_to):
        print("Creating output folder ...")
        os.mkdir(compile_to)

    if not os.path.exists(compile_bin):
        print("Making 'bin' folder '%s'" % compile_bin)
        os.mkdir(compile_bin)

    if val["tk-support"]:
        if not os.path.exists(compile_lib):
            print("Making Tkinter 'lib' folder '%s' ... " % compile_lib, end="", flush=True)
            os.mkdir(compile_lib)
            tar_tk  = os.path.join(compile_lib, tk_lq)
            tar_tcl = os.path.join(compile_lib, tcl_lq)
            shutil.copytree(tk, tar_tk)
            shutil.copytree(tcl, tar_tcl)
            # TODO: Definitely do not need the demos! Anything else?
            shutil.rmtree(os.path.join(tar_tk, "demos"), ignore_errors=True)
            print("done.")

    print("Output folder is ready.")

if compile_to:
    pscript_dist = os.path.join(compile_to, os.path.basename(pscript_dist))
    pscript_build = os.path.join(compile_to, os.path.basename(pscript_build))

if os.path.exists(pscript_dist):
    print("Removing old Nuitka output ... ", end="", flush=True)
    shutil.rmtree(pscript_dist, ignore_errors=True)
    shutil.rmtree(pscript_build, ignore_errors=True)
    print("done.")

cmd = ["python", "-m", "nuitka", "--standalone", "--remove-output"]

if not val["use-console"] or ext.lower() == ".pyw":
    cmd.append("--windows-disable-console")

if icon_file:
    cmd.append('--windows-icon="%s"' % icon_file)

if compile_to:                    # create inside output folder
    output = '--output-dir="%s"' % compile_to
else:                             # create inside script folder
    dname = os.path.dirname(os.path.abspath(pscript))
    output = '--output-dir="%s"' % dname

cmd.append(output)

if val["qt-support"]:
    cmd.append("--plugin-enable=qt-plugins")

if val["tk-support"]:
    val["follow"] = "tkinter," + val["follow"]

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

if val["add-args"]:
    cmd.append(val["add-args"])

cmd.append('"' + pscript + '"')
cmd = " ".join(cmd)
message = ["Now executing Nuitka. Please be patient and let it finish!", cmd]
print(sep_line)
print("\n".join(message))
print(sep_line)

rc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                      stderr=subprocess.PIPE,
                      shell=True)

sg.Popup(message[0], message[1], "This window will auto-close soon.",
         auto_close=True, auto_close_duration=10,
         non_blocking=False)

return_code = rc.wait()

if not os.path.exists(pscript_dist) or os.path.exists(pscript_build) or return_code != 0:
    rc_output  = rc.stdout.read().decode(encoding="utf-8", errors="replace")
    rc_output += rc.stderr.read().decode(encoding="utf-8", errors="replace")
    message = ["Nuitka compile failed!", "Messages:", rc_output]
    print("\n".join(message))
    sg.Popup(message[0], message[1], rc_output)
    raise SystemExit()

print(sep_line)

message = "Nuitka compile successful ..."

if not compile_to:                     # finished if no special output folder
    sg.Popup(message, "The EXE file is in '%s'" % pscript_dist)
    raise SystemExit()

#------------------------------------------------------------------------------
# merge new binaries
#------------------------------------------------------------------------------
import filecmp
message = [message, "Now merging binary files."]
print("\n".join(message))
print(sep_line)
copy_this = []                              # collect to-be-merged files here

# collect new files and check binary compatibility of existing ones
for root, _, files in os.walk(pscript_dist):
    for f in files:
        item = [root.replace(pscript_dist, ""), f]
        if f.endswith(".exe"):              # always merge (re)compiled EXE
            copy_this.append(item)
            continue
        bin_fn = os.path.join(compile_bin + root.replace(pscript_dist, ""), f)
        if not os.path.exists(bin_fn):      # always merge any *new* binary
            copy_this.append(item)
            continue
        # duplicate binaries must be identical on bit level
        if not filecmp.cmp(os.path.join(root, f), bin_fn, shallow=False):
            m = "Cannot merge incompatible binary file '%s'," % f
            message.append(m)
            print(m)
            m = "but folder '%s' still exists and is usable." % pscript_dist
            message.append(m)
            print(m)
            print(sep_line)
            message.append("Consider using script 'exe-merger.py'.")
            sg.Popup(message[0], "\n".join(message[1:]))
            raise SystemExit()

# we are good, now copy new stuff
for f in copy_this:
    f1 = pscript_dist + f[0]
    f1 = os.path.join(f1, f[1])
    f2 = compile_bin + f[0]
    if not os.path.exists(f2):
        os.makedirs(f2)
    print("\nCopying '%s' to:\n'%s'" % (f1, f2))
    shutil.copy2(f1, f2)

shutil.rmtree(pscript_dist, ignore_errors=True)
sg.Popup("Successful execution",
          "Merged %i binaries to '%s'." % (len(copy_this), compile_bin),
          auto_close = True, auto_close_duration = 5)