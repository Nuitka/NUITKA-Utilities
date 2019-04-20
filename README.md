# NUITKA-Utilities
A collection of scripts involving Python compilations with NUITKA.

-------
## exe-maker.py
This script shows a GUI (using tkinter / [PySimpleGUI](https://github.com/MikeTheWatchGuy/PySimpleGUI)) to ask for a Python script name and then invokes NUITKA to generate a **standalone EXE** file from it.

### Features
* sets a number of NUITKA default parameters
* several configuration options
* arbitrary additional Nuitka parameters
* optional invocation of UPX packer for the created binary output folder
* optional request to rebuild the dependency cache
* automatical use of the new dependency checker (based on [pefile](https://github.com/erocarrera/pefile)), which currently still is in experimental state. This feature uses a Python package to trace down binaries that are used by the script. Experience so far looks very promising - especially in terms of execution speed.
* will actively suppress scanning packages that are not checkmarked.

-----

## upx-packer.py
NUITKA binary output folders tend to have sizes in excess of 60 MB. While this is largely irrelevant if you continue to use the compiles on the original computer, it may become an issue when distributing stuff.

If you want to reduce your binaries' **distribution** size, the obvious way is to create a self-extracing archive. The compression results for NUITKA binaries are generally very good and yield sizes of 25% or less of the original by using e.g. 7zip. As a matter of course, the original size is re-created on the target computer.

This script in contrast aims to reduce the **current binary folder size** by UPX-compressing all eligible binaries ("exe", "pyd" and most of the "dll" files).

### Features
* Takes a folder and recursively compresses each eligible file by applying UPX to it. The compressions are started as sub-tasks -- so overall execution time depends on the number of available CPUs on your machine.
* It assumes that the ``upx.exe`` executable is contained on a path definition. Otherwise please change the script accordingly.
* Binaries are compressed *in-place*, so the **folder will have changed** after execution.
* Depending on the folder content, the resulting size should be significantly less than 50% of the original -- expect something like a 60% reduction.
* I am filtering out a number of binaries, which I found make the EXE files no longer executable. Among these are several PyQt binaries. Add more where you run into problems -- and please submit issues in these cases.

### Note
The resulting folder is still somewhat compressible e.g. when creating a self-extracting archive, but not as well as without applying the script.

Sample output:

```
D:\Jorj\Desktop\test-folder>python upx-packer.py bin
UPX Compression of binaries in folder 'D:\Jorj\Desktop\test-folder\bin'
Started 101 compressions out of 127 total files ...
Finished in 20 seconds.

Folder Compression Results (MB)
before: 108.45
after: 46.70
savings: 61.75 (56.94%)

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
Finished in 2 seconds.

Folder De-Compression Results (MB)
before: 46.70
after: 108.45
growth: 61.75 (132.24%)

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

-----
## onefile-maker-windows.py, onefile-maker-linux.py
Turns the ``dist`` folder of a standalone compiled script into an executable file, which can be distributed and handled like an installation file. Its name equals that of the script's EXE name (``script.py`` -->  ``script.exe``).

When executed on the target computer, the installation file will first decompress itself into the user's temporary folder and then invoke the **original** ``script.exe``, passing any arguments to it.

After the Python program finishes, the folder will be deleted again from temporary storage.

Alternatively, you can do the following:

Execute the file with parameter ``/D=<folder>`` specifying a directory of your choice. The ``dist`` folder will then be decompressed into ``<folder>`` and nothing else will happen.

## make-distribution.py
This script is a Nuitka **user plugin**. It is intended to **replace** ``exe-maker.py`` as it obsoletes the use of separate scripts to achieve the same results. In addition, it also works on Linux platforms (see comments below). This is how it is used:

```
python -m nuitka --standalone ... --user-plugin=make-distribution.py=options <yourscript.py>
```

The string ``"=options"`` following the script name is optional and can be used to pass options to the plugin. If used, it must consist of keyword strings separated by comma. The following are currently supported:

* **qt, tk, np**: Activate / enable the respective standard plugin ``"qt-plugins"``, ``"tk-inter"``, or ``"numpy"``. The option can be prefixed with ``"no"``. In this case, the corresponding plugin is **disabled** and recursing to certain modules / packages is suppressed. For example: ``"nonp"`` generates the options ``--recurse-not-to=numpy`` and ``--disable-plugin=numpy-plugin``.
* **onefile**: After successfully compiling the script, create a software distribution file in "OneFile" format from the script's ``".dist"`` folder. Depending on the platform, either ``onefile-maker- windows.py`` or ``onefile-maker-linux.py`` is invoked. See their descriptions above.
* **onedir**: Much like "OneFile", an executable file is created from the ``".dist"`` folder. But when executed on the target system, it decompresses its content into a specified folder and exits.
* **upx**: After successful compilation, invoke the binary compression program UPX to compress the ``".dist"`` folder.

Keywords ``onefile``, ``onedir`` and ``upx`` are mutually exclusive (other options can be combined). For each of these options, the plugin invokes the corresponding script for the platform.

> Please note that some downstream scripts (corresponding to onefile, onefile, upx) are still under development and not all of them are available on all platforms yet.

The following example command will create installation material in one-file format, deactivate tkinter and activate Qt support:

```
python -m nuitka --standalone ... --user-plugin=make-distribution.py=notk,qt,onefile <yourscript.py>
```

> Although it obviously is handy to put the plugin script in the same folder as ``<yourscript.py>``, this is not required -  just add enough information to locate it as a normal file. This also applies to any downstream scripts (like for onefile option, etc.).

> There is no general decision yet, how we want to distribute user plugins etc. with the main repository, if at all.


# Hinted Compilations
There is a new directory in this repository dealing with this topic specifically.

This feature has now reached a maturity level that can be recommended for general use with **standalone compilations**.

Please checkout the readme in that directory.