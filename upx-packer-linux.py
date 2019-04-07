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
Linux UPX Packer and Unpacker

For Packing
Usage : python upx-packer-linux.py path/to/the/folder 

For Unpacking
Usage : python upx-packer-linux.py path/to/the/folder --decompress

This script requires the executable upx to be on your $PATH
"""

import os
import subprocess as sp
import argparse
import time
import sys

from nuitka.utils.Execution import getExecutablePath

parser = argparse.ArgumentParser(
    description="UPX-Packer of Nuitka for Linux")

parser.add_argument(
    "dir",
    metavar = "DIR",
    help = "The directory that is to be compressed")

parser.add_argument(
    "--decompress",
    action = "store_true",
    help = "decompress the UPX compresses directory")

args = parser.parse_args()
args.dir = os.path.abspath(args.dir)

sep_line = "".ljust(80, "-")
print(sep_line)
print("Checking for the availibility of UPX")
upx_path = getExecutablePath("upx")

if upx_path is None:
    sys.exit("UPX not availible or missing in PATH definition")
print("OK : UPX is availible")
print(sep_line)

if not os.path.exists(args.dir):
    sys.exit("The path '{}' does not exist".format(args.dir))

file_count = 0
file_sizes = {}
tasks = []
if not args.decompress:
    method = "Compression"
else:
    method = "Decompression"

print("{} is in progess...".format(method))
t0 = time.time()
for dirpath, dirnames, filenames in os.walk(args.dir):
    for f in filenames:
        fname = os.path.join(dirpath, f)
        file_sizes[fname] = os.stat(fname).st_size
        if not args.decompress:
            cmd = ["upx", "-9", fname]
        else:
            cmd = ["upx", "-d", fname]
        process = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.PIPE)
        out, err = process.communicate()
        err = err.decode("utf-8")
        tasks.append(process)
        file_count += 1

for t in tasks:
    t.wait()

t1 = int(time.time() - t0)
print("Finished in {} seconds.".format(t1), flush=True)

old_size = new_size = 0.0
for f in file_sizes.keys():
    old_size += file_sizes[f]
    new_size += os.stat(f).st_size

old_size *= 1./1024/1024
new_size *= 1./1024/1024
diff_size = old_size - new_size
diff_percent = diff_size / old_size * 100
text = "\nFolder %s Results (MB)\nbefore: %.2f\nafter: %.2f\nsavings: %.2f (%.1f%%)"
print(text % (method, old_size, new_size, diff_size, diff_percent))
