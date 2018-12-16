import sys, os, subprocess, shutil

py2 = str is bytes

if py2:                      # last tk/tcl qualifyers depend on Python version
    tk_lq  = "tk8.5"
    tcl_lq = "tcl8.5"
    import PySimpleGUI27 as sg
else:
    tk_lq  = "tk8.6"
    tcl_lq = "tcl8.6"
    import PySimpleGUI as sg

sep_line = "".ljust(80, "-")

form = sg.FlexForm('Nuitka Standalone EXE Generation')

layout = [
    [sg.Text("Python Script:", size=(10,1)),
     sg.InputText("", key="py-file"),
     sg.FileBrowse(button_text="...", file_types=(("Python Files","*.py*"),))],
    [sg.Text("Output Folder:", size=(10,1)),
     sg.InputText("", key="compile-to"),
     sg.FolderBrowse(button_text="...")],
    [sg.Text("Icon File:", size=(10,1)),
     sg.InputText("", key="icon-file"),
     sg.FileBrowse(button_text="...")],
    [sg.Checkbox("Use Console Window", default=True, key="use-console"),
     sg.Checkbox("Include Tkinter Support", default=True, key="tk-support")],
    [sg.Text("Any additional nuitka args:")],
    [sg.InputText("", key="add-args", size=(60,2))],
    [sg.Submit(), sg.Cancel()]
]

btn, val = form.Layout(layout).Read()

if btn != "Submit":
    raise SystemExit("Cancel requested.")

form.Close()

if val["tk-support"]:
    sys_tcl = os.path.join(os.path.dirname(sys.executable), "tcl")
    tk  = os.path.join(sys_tcl, tk_lq)
    tcl = os.path.join(sys_tcl, tcl_lq)
    if not os.path.exists(tk):
        raise SystemExit("Unexpected: '%s' does not exist!" % tk)
    if not os.path.exists(tcl):
        raise SystemExit("Unexpected: '%s' does not exist!" % tcl)

icon_file = val["icon-file"]
if icon_file:
    if not os.path.exists(icon_file):
        raise SystemExit("Icon file '%s' does not exist!" % icon_file)

pscript = os.path.abspath(val["py-file"])
if not os.path.exists(pscript):
    raise SystemExit("Python script '%s' does not exist!" % pscript)

pscript_n, ext = os.path.splitext(pscript)
pscript_dist = pscript_n + ".dist"

compile_to = val["compile-to"]
if compile_to:
    compile_to = os.path.abspath(compile_to)

if compile_to == pscript_dist:
    compile_to = None

if not compile_to and val["tk-support"]:
    raise SystemExit("Need 'Output Folder' for Tkinter support!")

if compile_to:
    compile_bin = os.path.join(compile_to, "bin")
    compile_lib = os.path.join(compile_to, "lib")
    if not os.path.exists(compile_to):
        print("Creating output folder ...")
        os.mkdir(compile_to)

    if not os.path.exists(compile_bin):
        os.mkdir(compile_bin)

    if val["tk-support"]:
        if not os.path.exists(compile_lib):
            print("Making Tkinter 'lib' folder ... ", end="", flush=True)
            os.mkdir(compile_lib)
            tar_tk  = os.path.join(compile_lib, tk_lq)
            tar_tcl = os.path.join(compile_lib, tcl_lq)
            shutil.copytree(tk, tar_tk)
            shutil.copytree(tcl, tar_tcl)
            # TODO: Definitely do not need the demos! What else?
            shutil.rmtree(os.path.join(tar_tk, "demos"), ignore_errors=True)
            print("done.")

    print("Output folder is ready.")

if compile_to:
    pscript_dist = os.path.join(compile_to, os.path.basename(pscript_dist))

if os.path.exists(pscript_dist):
    print("Removing old binaries ... ", end="", flush=True)
    shutil.rmtree(pscript_dist, ignore_errors=True)
    print("done.")

if not val["use-console"] or ext.lower() == ".pyw":
    win_no_con = "--windows-disable-console"
else:
    win_no_con = ""

win_icon = '--windows-icon="%s"' % icon_file if icon_file else ""

if compile_to:                    # create inside output folder
    output = '--output-dir="%s"' % compile_to
else:                             # create inside script folder
    dname = os.path.dirname(os.path.abspath(pscript))
    output = '--output-dir="%s"' % dname

cmd = 'python -m nuitka --standalone --remove-output %s %s %s %s "%s"'
cmd = cmd % (val["add-args"], output, win_no_con, win_icon, pscript)

while "  " in cmd:
    cmd = cmd.replace("  ", " ")

print(sep_line)
print("Now executing:\n")
print(cmd)
print("\nNext messages are from nuitka compilation - please be patient.")
print(sep_line)

subprocess.call(cmd)

if not os.path.exists(pscript_dist):
    print("Output folder '%s' does not exist." % pscript_dist)
    raise SystemExit("Nuitka compile failed - exiting.")

print(sep_line)
print("Nuitka compile successful.")
print(sep_line)

if not compile_to:                     # finished if no special output folder
    raise SystemExit()

#------------------------------------------------------------------------------
# merge new binaries
#------------------------------------------------------------------------------
print("Now merging binary files.")
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
        x = open(os.path.join(root, f), "rb").read()
        y = open(bin_fn, "rb").read()
        if x != y:
            print("Cannot merge: incompatible binary file")
            print(bin_fn)
            print("Nuitka folder '%s' still exists and is usable." % pscript_dist)
            print(sep_line)
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
