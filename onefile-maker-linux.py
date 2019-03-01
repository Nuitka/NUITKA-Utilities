#     Copyright 2019
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

The executable contains the compressed dist folder and is named 
sciptname-onefile.sh and it is put in the same directory where 
the this script lives.

The executable is a small shell script made so that it is portable
on most UNIX systems

When the installation file is executed, the dist folder is

(1) decompressed in the user's temp directory (envireonment variable $TEMP)
(2) the executable specified in the uncompresses directory is invoked
(3) after execution has finished, the dist folder is removed again

This scipt can be run with a -h flag to get the availible options. Here is
an example to create a executable of test.dist folder and then execute the test file in it

python onefile-linux.py /home/myname/test.dist /home/myname/makeself test "A test for checking"

Dependencies
------------
* The makeself repository is required to run this script. It can be downloaded at 
  https://github.com/megastep/makeself

"""
import os
import argparse

parser = argparse.ArgumentParser()

parser.add_argument(
    "directory",
    help = "Dist directory path")

parser.add_argument(
    "makeself", 
    help = "The path to Makeself directory")

parser.add_argument(
    "executable",
    help = "The file to be executed after the extraction")

parser.add_argument(
    "label",
    help = "The desciption for the executable created")

args = parser.parse_args()
cwd = os.getcwd()
dist = os.path.abspath(args.directory)

if args.makeself is None or not os.path.isdir(args.makeself):
    raise SystemExit("The Makeself directory path does not exist")
else:
    os.chdir(args.makeself)

if not os.path.isdir(dist) or not dist.endswith(".dist"):
    raise SystemExit("'%s' is not a Nuitka dist folder" % dist)

filename = os.path.basename(dist).split('.')[0] + '-onefile.sh'

command = "./makeself.sh {} {} '{}' ./{}".format(dist,filename,args.label,args.executable)
move_command = "mv {} {}".format(os.path.join(os.getcwd(), filename), os.path.join(cwd, filename))

os.system(command)
os.system(move_command)