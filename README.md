# NUITKA-Utilities
A collection of scripts involving Python compilations with NUITKA

## make-exe.py (currently tested on Windows)
This script shows a GUI (using tkinter / [PySimpleGUI](https://github.com/MikeTheWatchGuy/PySimpleGUI)) to ask for a Python script name and then invokes NUITKA to generate a standalone EXE file from it.

### Features
* sets a number of NUITKA default parameters (e.g. "remove output")
* includes TK/TCL files upon request
* allows specification / suppression of a script console window
* supports specification of an icon file
* allows entering arbitrary additional NUITKA parameters
* supports a **central folder** to automatically collect binaries from multiple compilations

### Note 1
If a central folder for the binaries is requested, this folder is either automatically created or extended with the new binary file(s). An existing folder will first be checked for compatibility (to prevent things like different Python versions or different versions of the same imported package).

After a successful check, only new files will be included in that folder. Apart from initial setup, this will tend to be just the new or changed EXE file.

In this way, a folder with compiled standalone Python programs can be built up over time.

### Note 2
If your program uses tkinter, you must request TK/TCL file inclusion. This is however only supported if you **also specify an output folder** for the binaries. If you do want to use the script's folder, you must specify it. The folder will afterwards contain two new sub-folders named `bin`, `lib` respectively. You must include both of these sub-folders if you later want to distribute your binaries.

## upx-packer.py
NUITKA binary output folders tend to have sizes in excess of 60 MB. While this is largely irrelevant if you continue to use compiles on the original computer, it may become an issue when distributing stuff.

If you want to reduce your binaries' distribution size, the obvious way is to create a self-extracing archive. The compression results for NUITKA binaries are generally very good and yield sizes of 25% or less of the original. As a matter of course, the original folder size is re-created on the target computer.

This script in contrast aims to reduce the binary folder size by UPX-compression of all eligible binaries ("exe", "pyd" and most of the "dll" files).

### Features
* Takes a folder and recursively compresses each eligible file by applying UPX to it. The compressions are started as sub-tasks -- so overall execution time depends on the number of available CPUs on your machine.
* It assumes that the UPX executable is contained on a path definition. Otherwise please change the script accordingly.
* Binaries are compressed *in-place*, so the folder will have changed after execution. It can no longer be used to incorporate new compilation outputs.
* Depending on the folder content, the resulting size should be significantly less than 50% of the original -- expect something like a 60% reduction.

### Note
You can still distribute your binaries using self-extracting archives after execution of this script. The archive will also still be smaller than the original -- but not as small as without applying the script to it.



