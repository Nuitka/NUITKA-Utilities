import os, sys
import pythoncom
from win32com.shell import shell, shellcon
import PySimpleGUI as sg

desktop_path = shell.SHGetFolderPath (0, shellcon.CSIDL_DESKTOP, 0, 0)

form = sg.FlexForm("Create Links to EXE Files in a Folder")
message = sg.Text("", size=(60,1))
layout = [
    [sg.Text("Program Folder:", size=(12,1)),
     sg.InputText("", key="pgm-dir", do_not_clear=True),
     sg.FolderBrowse(button_text="...")],
    [sg.Text("Create in:", size=(12,1)),
     sg.InputText(desktop_path, key="tar-folder", do_not_clear=True),
     sg.FolderBrowse(button_text="...")],
    [message],
    [sg.Submit(), sg.Cancel()]
         ]

while True:
    btn, val = form.Layout(layout).Read()

    if btn != "Submit" or not val["pgm-dir"]:
        break

    input_dir = exe_filedir = os.path.abspath(val["pgm-dir"])
    if not os.path.exists(exe_filedir):
        message.Update("No such folder: '%s'" % val["pgm-dir"])
        continue

    flist = os.listdir(exe_filedir)
    exe_files = [f for f in flist if f.lower().endswith(".exe")]

    if len(exe_files) == 0:
        exe_filedir = os.path.join(exe_filedir, "bin")
        try:
            flist = os.listdir(exe_filedir)
            exe_files = [f for f in flist if f.lower().endswith(".exe")]
        except:
            pass

    if len(exe_files) == 0:
        message.Update("No '.exe' files found")
        continue

    if not val["tar-folder"]:
        tar_folder = desktop_path
    else:
        tar_folder = os.path.abspath(val["tar-folder"])

    if not os.path.exists(tar_folder):
        message.Update("Output folder does not exist: '%s'" % tar_folder)
        continue

    # We are all set. Now create a link for each of the EXE files.
    for exe_base in exe_files:
        exe_file = os.path.join(exe_filedir, exe_base) # full EXE name
        exe_name, exe_ext = os.path.splitext(exe_base) # split off extension
        shortcut = pythoncom.CoCreateInstance(         # create link instance
                        shell.CLSID_ShellLink,
                        None,
                        pythoncom.CLSCTX_INPROC_SERVER,
                        shell.IID_IShellLink,
                        )
        shortcut.SetPath(exe_file)                         # set file path
        shortcut.SetDescription ("Link to %s" % exe_file)  # set description
        shortcut.SetIconLocation (exe_file, 0)             # set the icon
        persist_file = shortcut.QueryInterface(pythoncom.IID_IPersistFile)
        persist_file.Save(os.path.join(tar_folder, "%s.lnk" % exe_name.title()), 0)
        shortcut = None
    break
