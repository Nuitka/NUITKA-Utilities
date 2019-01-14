# NUITKA-Utilities
A collection of scripts involving Python compilations with NUITKA

-------
## exe-maker.py (currently tested on Windows)
This script shows a GUI (using tkinter / [PySimpleGUI](https://github.com/MikeTheWatchGuy/PySimpleGUI)) to ask for a Python script name and then invokes NUITKA to generate a **standalone EXE** file from it.

### Features
* sets a number of NUITKA default parameters
* several configuration options
* arbitrary additional NUITKA parameters
* optional invocation of UPX packer for binary output
* optional request to rebuild the dependency cache
* experimental: button to remove unneeded binaries (**"skimming"**)

### Note 1
A central folder to merge several binary `.dist` folders is no longer supported by this script. Use `exe-merger.py` for this purpose - it contains all the required functiuonality.

### Note 2
If your program uses Tkinter, you **must check** the respective button. We will include the required Tkinter libraries as subfolders and **automatically redirect** Tkinter requests of your script to them. This is done by temporarily replacing your script with a slightly modified version.

There currently exists the following limitation: if your program imports the `__future__` module, we are not able to correctly make this modification. In this case, you **need to modify** your script and insert the following statement after all `__future__` imports (and any other compiler directives, encoding, etc.). It formally is a Python comment line and thus will not interfere with normal script execution:

```python
#redirect tkinter
```

### Note 3
The "Skim" button is an experimental functionality to reduce the size of the `dist` folder. It removes lots of binaries - most of them unnecessary indeed. As per this writing, this feature is still under development. It currently takes the following precautions

* do not remove `pythonxy.dll` and Windows runtime DLLs, `vcruntimexxx.dll`and `msvcrt.dll`.
* do not remove Tkinter components if TK-Support button clicked
* do not remove wxPython binaries
* only inspect the `dist` root folder
* do removals **before** eventually invoking UPX

TODO: do not remove Qt, numpy, scipy, ... components.

-----
## upx-packer.py
NUITKA binary output folders tend to have sizes in excess of 60 MB. While this is largely irrelevant if you continue to use the compiles on the original computer, it may become an issue when distributing stuff.

If you want to reduce your binaries' **distribution** size, the obvious way is to create a self-extracing archive. The compression results for NUITKA binaries are generally very good and yield sizes of 25% or less of the original by using e.g. 7zip. As a matter of course, the original size is re-created on the target computer.

This script in contrast aims to reduce the **current binary folder size** by UPX-compressing all eligible binaries ("exe", "pyd" and most of the "dll" files).

### Features
* Takes a folder and recursively compresses each eligible file by applying UPX to it. The compressions are started as sub-tasks -- so overall execution time depends on the number of available CPUs on your machine.
* It assumes that the ``upx.exe`` executable is contained on a path definition. Otherwise please change the script accordingly.
* Binaries are compressed *in-place*, so the **folder will have changed** after execution. It can no longer be used to incorporate new compilation outputs -- i.e. via `exe-maker.py`.
* Depending on the folder content, the resulting size should be significantly less than 50% of the original -- expect something like a 60% reduction.
* I am filtering out a number of binaries, which I found make the EXE files no longer executable. Among these are several PyQt binaries. Add more where you run into problems -- and please submit issues in these cases.

### Note
The resulting folder is still somewhat compressible e.g. when creating a self-extracting archive, but not as well as without applying the script.

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
The self-extracting archive of the resulting **packed** `bin` folder (7zip) has a size of **34.8 MB**.

-----
## upx-unpacker.py
Does the opposite of `upx-packer.py`.

Use it to undo a upx-compression -- for example if you encounter problems.

> Please note that - at least under Windows - UPX decompression **does not restore** binary identity with the original. Therefore, merging new compiles into a packed or unpacked folder ***will always fail*** when using `exe-maker.py`. But look at script ``exe-merger.py`` for ways out of this stumble block.

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
The self-extracting archive of the **unpacked** `bin` folder has a size of **28.7 MB**, i.e. notably smaller than a UPX-compressed folder.

### Note
The binaries which the script tries to decompress are more than during compression, because a less restrictive selection is applied.

This is no problem: UPX ignores files that it didn't compress previously.

Decompression runtime is very short anyway.

-----
## exe-merger.py
Yet another script to merge two folders with binaries. Can be used if `exe-maker.py` refuses to merge compilation output because of "incompatible" binaries.

This script can resolve all "incompatibility" situations via a "force-mode" merge. In this case source files overwrite same-named files in the target.

> If you want to exercise greater care, you can first try to compress or decompress both, source and target folders repeatedly and then use this script again:
>
> * after first decompression, UPX will **not re-instate** binary equality with the original file. But after another round of compression / decompression, results will remain stable and you should be able to successfully merge them.

You will finally have a merged target folder, which you then again can (de-) compress as required.

-----
## link-maker.py
Scan a folder for ``.exe`` files and create a ``.lnk`` (link) file for each of them. If the specified folder has no ``.exe`` files, its ``bin`` sub-folder will be checked (if present).

Output folder default is the user desktop.

Script runs under Windows only and requires packages ``pythoncom`` and ``win32com`` to be installed.