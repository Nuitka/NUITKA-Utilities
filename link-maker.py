import os, sys
import pythoncom
from win32com.shell import shell, shellcon
import PySimpleGUI as sg 

desktop_path = shell.SHGetFolderPath (0, shellcon.CSIDL_DESKTOP, 0, 0)

form = sg.FlexForm("Create Links to Nuitka Generated EXE Files")
layout = [
    [sg.Text("Program Folder:"), sg.InputText("", key="pgm-dir"),
     sg.FolderBrowse(button_text="...")],
    [sg.Text("Create in:"), sg.InputText(desktop_path, key="tar-folder"),
     sg.FolderBrowse(button_text="...")],
    [sg.Submit(), sg.Cancel()]
         ]

btn, val = form.Layout(layout).Read()
if btn != "Submit" or not val["pgm-dir"]:
    raise SystemExit()

input_dir = exe_filedir = os.path.abspath(val["pgm-dir"])
if not os.path.exists(exe_filedir):
    raise SystemExit("no such folder '%s'" % exe_filedir)

flist = os.listdir(exe_filedir)
exe_files = [f for f in flist if f.lower().endswith(".exe")]

if len(exe_files) == 0:
    exe_filedir = os.path.join(exe_filedir, "bin")
    flist = os.listdir(exe_filedir)
    exe_files = [f for f in flist if f.lower().endswith(".exe")]

if len(exe_files) == 0:
    raise SystemExit("no .exe files found")

if not val["tar-folder"]:
    tar_folder = desktop_path
else:
    tar_folder = os.path.abspath(val["tar-folder"])

for f in exe_files:
    exe_base = os.path.basename(f)
    exe_name, exe_ext = os.path.splitext(exe_base)
    exe_file = os.path.join(exe_filedir, f)
    shortcut = pythoncom.CoCreateInstance (
                    shell.CLSID_ShellLink,
                    None,
                    pythoncom.CLSCTX_INPROC_SERVER,
                    shell.IID_IShellLink,
                    )
    shortcut.SetPath(exe_file)
    shortcut.SetDescription ("Link to %s" % exe_file)
    shortcut.SetIconLocation (exe_file, 0)
    persist_file = shortcut.QueryInterface (pythoncom.IID_IPersistFile)
    persist_file.Save (os.path.join (tar_folder, "%s.lnk" % exe_name.title()), 0)
    shortcut = None
