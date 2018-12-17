# NUITKA-Utilities
A collection of scripts involving Python compilations with NUITKA

## make-exe.py (currently tested on Windows)
This script shows a GUI (using tkinter / [PySimpleGUI](https://github.com/MikeTheWatchGuy/PySimpleGUI)) to ask for a Python script name and then invokes NUITKA to generate a standalone EXE file from it.

### Features
* sets a number of NUITKA default parameters (e.g. "remove output")
* includes TK/TCL files upon request
* includes Qt plugin upon request
* allows specification / suppression of a script console window. Automatically unsets for script extension `*.pyw`.
* supports specification of an icon file
* allows entering arbitrary additional NUITKA parameters
* supports a **central folder** to automatically collect binaries from multiple compilations

### Note 1
If a central folder for the binaries is requested, this folder is either automatically created or extended with the new binary file(s). An existing folder will first be checked for compatibility (to prevent things like different Python versions or different versions of the same imported package).

After a successful check, only new files will be included in that folder. After creation, this will tend to be just the new or changed EXE file, and maybe a handful more.

In this way, you can build up a folder with your compiled standalone Python binaries over time.

### Note 2
If your program uses tkinter, you must request TK/TCL file inclusion. This is however only supported if you **also specify an output folder** for the binaries. It is possible to **use the script's folder** for this, but you must specify it. The folder will afterwards contain two new sub-folders named `bin` and `lib` respectively. You must include both of these sub-folders if you later want to distribute your binaries.

## upx-packer.py
NUITKA binary output folders tend to have sizes in excess of 60 MB. While this is largely irrelevant if you continue to use the compiles on the original computer, it may become an issue when distributing stuff.

If you want to reduce your binaries' **distribution** size, the obvious way is to create a self-extracing archive. The compression results for NUITKA binaries are generally very good and yield sizes of 25% or less of the original by using e.g. 7zip. As a matter of course, the original folder size is re-created on the target computer.

This script in contrast aims to reduce the current binary folder size by UPX-compressing of all eligible binaries ("exe", "pyd" and most of the "dll" files).

### Features
* Takes a folder and recursively compresses each eligible file by applying UPX to it. The compressions are started as sub-tasks -- so overall execution time depends on the number of available CPUs on your machine.
* It assumes that the ``upx.exe`` executable is contained on a path definition. Otherwise please change the script accordingly.
* Binaries are compressed *in-place*, so the folder will have changed after execution. It can no longer be used to incorporate new compilation outputs -- i.e. via `make-exe.py`.
* Depending on the folder content, the resulting size should be significantly less than 50% of the original -- expect something like a 60% reduction.
* I am filtering out a number of binaries, which I found make the EXE files no longer executable. Among these are several PyQt binaries. Add more where you run into problems -- and please submit issues in these cases.

### Note
You can still distribute your binaries using self-extracting archives after execution of this script. The archive will also still be smaller than the original -- but not as small as without applying the script.

Sample output:

```
D:\Jorj\Desktop\test-folder>python upx-packer.py bin
UPX Compression of binaries in folder 'D:\Jorj\Desktop\test-folder\bin'
Started 101 compressions out of 127 total files ...
Finished in 19.7697 seconds.

Folder Compression Results (MB)
before: 108.45
after: 46.696
savings: 61.751 (56.94%)

D:\Jorj\Desktop\test-folder>
```
The self-extracting archive of the resulting **packed** `bin` folder (7zip) has a size of 34.8 MB.

## upx-unpacker.py
Does the opposite of `upx-packer.py`.

Use it to undo a upx-compression -- for example if you encounter problems.
Please note that - at least under Windows - decompression **does not restore** binary identity to the original. Therefore, merging new compiles into the folder will fail using `make-exe.py`.

```
D:\Jorj\Desktop\rest-folder>python upx-unpacker.py bin
UPX De-Compression of binaries in folder 'D:\Jorj\Desktop\test-folder\bin'
Started 119 de-compressions out of 127 total files ...
Finished in 1.71768 seconds.

Folder De-Compression Results (MB)
before: 46.696
after: 108.45
growth: 61.751 (132.24%)

D:\Jorj\Desktop\test-folder>
```
The self-extracting archive of the **unpacked** `bin` folder has a size of 28.7 MB.

### Note
The binaries which the script tries to de-compress are more than during compression, because a less restrictive selection is applied.

This can be safely ignored, because UPX will ignore all files that were not previously compressed by it.

De-compression runtime is very short anyway.
