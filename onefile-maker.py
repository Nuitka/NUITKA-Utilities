#     Copyright 2019, Jorj McKie, mailto:jorj.x.mckie@outlook.de
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

(1) decompressed in the user's temp directory
(2) the original 'script.exe' is invoked, passing in any provided arguments
(3) after 'script.exe' has finished, the dist folder is removed again

The following alternative handling options are also available:

* execute the distribution file with parameter '/D=...' by specifying a directory,
  which will then be used instead of the temp directory

* use an unzipping utility (like 7zip, WinZip) on the distribution file to extract its
  contents to some place. The resulting folder can then be used like any
  installed application.

Dependencies
------------
* PySimpleGUI
* The program **NSIS** is required to generate the installation file. It can be
  downloaded from here: https://nsis.sourceforge.io/Main_Page.

"""
import sys
import os
import time
import subprocess as sp
import PySimpleGUI as sg

form = sg.FlexForm('OneFile Installer Creation')
message = sg.Text("", size=(60,1))
frm_dist = sg.InputText("", key="dist", do_not_clear=True)
layout = [
            [sg.Text("'dist' Folder:", size=(13,1)),
             frm_dist,
             sg.FolderBrowse(button_text="...")
            ],
            [sg.Text("OneFile name:", size=(13,1)),
             sg.InputText("", key="1-file", do_not_clear=True),
            ],
            [message],
            [sg.Submit(), sg.Cancel()]
         ]

nsi = """
Name "%s"
OutFile "%s"
InstallDir $TEMP
RequestExecutionLevel user
SilentInstall silent
SetCompressor LZMA
Section ""
  SetOutPath $INSTDIR
  File /r "%s"
SectionEnd
Function .onInstSuccess
  ExecWait '"$OUTDIR\\%s" $CMDLINE'
  RMDir /r "$OUTDIR\\%s"
FunctionEnd
"""
sep_line = "-" * 80
# NSIS script compiler (standard installation location)
makensis = r'"C:\Program Files (x86)\NSIS\makensis.exe"'

form.Layout(layout)
while 1:
    btn, val = form.Show()
    if btn in (None, "Cancel"):
        raise SystemExit()
    message.Update("")
    dist = os.path.abspath(val["dist"])
    if (not os.path.exists(dist) or
        not os.path.isdir(dist)):
        message.Update("'dist' does not exist / is no folder")
        continue
    l = os.listdir(dist)               # find the exe file in dist
    for exe in l:
        if exe.endswith(".exe"):
            break
    if not exe.endswith(".exe"):
        message.Update("'dist' folder has no '.exe' file")
        continue
    if not val["1-file"]:
        one_file = exe
    else:
        one_file = val["1-file"]
    break

form.Close()

dist_base = os.path.basename(dist)     # basename of dist folder
dist_dir = os.path.dirname(dist)       # directory part of dist

# finalize installation script
nsi_final = nsi % (dist_base, os.path.join(dist_dir, one_file), dist, os.path.join(dist_base, exe), dist_base)

# put NSIS installation script next to dist folder
nsi_filename = os.path.join(dist_dir, "file.nsi")
nsi_file = open(nsi_filename, "w")
nsi_file.write(nsi_final)
nsi_file.close()

# now compile the installation script using NSIS
cmd = (makensis, '"%s"' % nsi_filename)

t0 = time.time()
rc = sp.Popen(" ".join(cmd), shell=True)
print("\nNow executing", cmd[0],
      "\nPlease wait, this may take some time.\n", sep_line)
return_code = rc.wait()

t1 = time.time()
print(sep_line,
      "\nOneFile generation return code:", return_code,
      "\nDuration: %i sec." % int(round(t1-t0))
     )
