import sys, os, subprocess, shutil

py2 = str is bytes

if py2:                      # last tk/tcl qualifyers depend on Python version
    tk_lq  = "tk8.5"
    tcl_lq = "tcl8.5"
else:
    tk_lq  = "tk8.6"
    tcl_lq = "tcl8.6"

sep_line = "".ljust(80, "-")

prepend = """
import os, sys
os.environ["TCL_LIBRARY"] = os.path.join(sys.path[0], "%s")
os.environ["TK_LIBRARY"] = os.path.join(sys.path[0], "%s")

""" % (tcl_lq, tk_lq)

def rename_script(fname):
    print(sep_line)
    print("Tk-modifying '%s' for Nuitka." % fname)
    text = open(fname).read()
    dirname, basename = os.path.split(fname)
    os.rename(fname, os.path.join(dirname, "exe-maker-" + basename))
    text = prepend + text
    fout = open(fname, "w")
    fout.write(text)
    fout.close()



def restore_script(fname):
    dirname, basename = os.path.split(fname)
    os.remove(fname)
    os.rename(os.path.join(dirname, "exe-maker-" + basename), fname)
    print(sep_line)
    print("Restored original version of '%s'." % fname)

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


message = sg.Text("", size=(60,1))
frm_input = sg.InputText("", key="py-file", do_not_clear=False)
frm_output = sg.InputText("", key="compile-to", do_not_clear=True)
frm_icon = sg.InputText("", key="icon-file", do_not_clear=True)
frm_follow = sg.InputText("", size=(60,2), key="follow", do_not_clear=True)
frm_no_follow = sg.InputText("", size=(60,2), key="no-follow", do_not_clear=True)
frm_packages = sg.InputText("", size=(60,2), key="packages", do_not_clear=True)
frm_modules = sg.InputText("", size=(60,2), key="modules", do_not_clear=True)
frm_plugins = sg.InputText("", size=(60,2), key="plugin-dir", do_not_clear=True)
frm_more = sg.InputText("", key="add-args", size=(60,2), do_not_clear=True)
form = sg.FlexForm('Nuitka Standalone EXE Generation')

compile_to = pscript = icon_file = ""

layout = [
    [sg.Text("Python Script:", size=(13,1)),
     sg.InputText("", key="py-file", do_not_clear=True),
     sg.FileBrowse(button_text="...", file_types=(("Python Files","*.py*"),))],
    [sg.Text("Output Folder:", size=(13,1)),
     frm_output,
     sg.FolderBrowse(button_text="...")],
    [sg.Text("Icon File:", size=(13,1)),
     frm_icon,
     sg.FileBrowse(button_text="...")],
    [sg.Checkbox("Remove Output", default=True, key="remove-build"),
     sg.Checkbox("Use Console", default=True, key="use-console"),
     sg.Checkbox("Tk Support", default=False, key="tk-support"),
     sg.Checkbox("Qt Support", default=False, key="qt-support"),],
    [sg.Text("Recurse into:", size=(13,1)), frm_follow],
    [sg.Text("No recurse into:", size=(13,1)), frm_no_follow],
    [sg.Text("Include packages:", size=(13,1)), frm_packages],
    [sg.Text("Include modules:", size=(13,1)), frm_modules],
    [sg.Text("Include plugin-dir:", size=(13,1)), frm_plugins],
    [sg.Text("More Nuitka args:", size=(13,1)), frm_more],
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
    if compile_to:
        compile_to = os.path.abspath(compile_to)
        if not os.path.exists(compile_to):
            message.Update("Folder '%s' does not exist!" % compile_to)
            compile_to = ""
            continue

    if val["tk-support"] and not tkinter_available:
        message.Udate("Tkinter files are not available on this system!")
        continue

    break # we have valid parameters and can start compile

form.Close()
if btn == "Cancel":
    raise SystemExit()

#------------------------------------------------------------------------------
# start the compile
#------------------------------------------------------------------------------

if icon_file:
    icon_file = os.path.abspath(icon_file)

pscript_n, ext = os.path.splitext(pscript)
pscript_dist = pscript_n + ".dist"
pscript_build = pscript_n + ".build"

cmd = ["python", "-m", "nuitka", "--standalone", "--python-flag=nosite",]

if not val["use-console"] or ext.lower() == ".pyw":
    cmd.append("--windows-disable-console")

if val["remove-build"]:
    cmd.append("--remove-output")

if icon_file:
    cmd.append('--windows-icon="%s"' % icon_file)

if compile_to:
    compile_to = os.path.abspath(compile_to)
    pscript_dist = os.path.join(compile_to, os.path.basename(pscript_dist))
    pscript_build = os.path.join(compile_to, os.path.basename(pscript_build))
    output = '--output-dir="%s"' % compile_to
    cmd.append(output)

if val["qt-support"]:
    cmd.append("--plugin-enable=qt-plugins")

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

if val["add-args"]:
    cmd.append(val["add-args"])

if val["tk-support"]:
    rename_script(pscript)

cmd.append('"' + pscript + '"')
cmd = " ".join(cmd)

print(sep_line)
message = ["Now executing Nuitka. Please be patient and let it finish!", cmd]
print("\n".join(message))

rc = subprocess.Popen(cmd, shell=True)

sg.Popup(message[0], message[1], "This window will auto-close soon.",
         auto_close=True, auto_close_duration=10,
         non_blocking=False)

return_code = rc.wait()

if val["tk-support"]:
    restore_script(pscript)

if return_code != 0:
    message = ["Nuitka compile failed!", "Check its output!"]
    print("\n".join(message))
    sg.Popup(message[0], message[1])
    raise SystemExit()

print(sep_line)

message = "Nuitka compile successful ..."
print(message)
if val["tk-support"]:
    print("Making Tkinter library folders ...", end="", flush=True)
    tar_tk  = os.path.join(pscript_dist, tk_lq)
    tar_tcl = os.path.join(pscript_dist, tcl_lq)
    shutil.copytree(tk, tar_tk)
    shutil.copytree(tcl, tar_tcl)
    # TODO: Definitely do not need the demos! Anything else?
    shutil.rmtree(os.path.join(tar_tk, "demos"), ignore_errors=True)
    print("done.")

sg.Popup(message, "The EXE file is in '%s'" % pscript_dist)

raise SystemExit()
