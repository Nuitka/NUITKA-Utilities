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

import sys, os, subprocess, shutil
import PySimpleGUI as sg

sep_line = "".ljust(80, "-")

form = sg.FlexForm('Merge Binary Folders')

layout = [
    [sg.Text("Input Folder:", size=(10,1)),
     sg.InputText("", key="from"),
     sg.FolderBrowse(button_text="...")],
    [sg.Text("Output Folder:", size=(10,1)),
     sg.InputText("", key="to"),
     sg.FolderBrowse(button_text="...")],
    [sg.Checkbox("Force Merge - only check if you are sure.", default=False, key="force"),] ,
    [sg.Submit(), sg.Cancel()]
]

btn, val = form.Layout(layout).Read()

if btn != "Submit":
    raise SystemExit("Cancel requested.")

form.Close()

print(sep_line)

i_dir = val["from"]
if i_dir:
    i_dir = os.path.abspath(i_dir)
    if not os.path.exists(i_dir):
        raise SystemExit("Input folder '%s' does not exist." % i_dir)
else:
    raise SystemExit("Input folder must be given.")

o_dir = val["to"]
if o_dir:
    o_dir = os.path.abspath(o_dir)
    if not os.path.exists(o_dir):
        raise SystemExit("Output folder '%s' does not exist." % o_dir)
else:
    raise SystemExit("Output folder must be given.")

if i_dir == o_dir:
    raise SystemExit("Input and output folders cannot be equal.")
#------------------------------------------------------------------------------
# merge new binaries
#------------------------------------------------------------------------------
print("Now merging binary files.")
print("Input Folder: '%s'" % i_dir)
print("Output Folder: '%s'" % o_dir)
print(sep_line)

copy_this = []                              # collect to-be-merged files here

# collect new files and check binary compatibility of existing ones
for root, _, files in os.walk(i_dir):
    for f in files:
        item = [root.replace(i_dir, ""), f]
        if f.endswith(".exe"):              # always merge (re)compiled EXE
            copy_this.append(item)
            continue
        bin_fn = os.path.join(o_dir + root.replace(i_dir, ""), f)
        if not os.path.exists(bin_fn):      # always merge any *new* binary
            copy_this.append(item)
            continue
        # duplicate files must be identical on bit level
        x = open(os.path.join(root, f), "rb").read()
        y = open(bin_fn, "rb").read()
        if x != y:
            if val["force"] == False:
                print("Cannot merge: incompatible binary file")
                print(bin_fn)
                print("Consider compressing both folders, then re-run this script.")
                print("Or re-run this script with force option.")
                print(sep_line)
                raise SystemExit()
            else:
                print("Warning: force-merging", bin_fn)
                copy_this.append(item)
                continue


# we are good, now copy new stuff
for f in copy_this:
    f1 = i_dir + f[0]
    f1 = os.path.join(f1, f[1])
    f2 = o_dir + f[0]
    if not os.path.exists(f2):
        os.makedirs(f2)
    print("\nCopying '%s' to:\n'%s'" % (f1, f2))
    shutil.copy2(f1, f2)
