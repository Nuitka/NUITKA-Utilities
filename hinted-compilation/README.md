# How to compile scripts in standalone profile-guided mode with Nuitka
This is a description focussing on things that must be done - without providing much detail of **why** things must be done in exactly this way.

All steps explained in the following must be done **exactly** as described.

These scripts have been tested on Windows and Linux (Ubuntu). Other platforms should work as well.

------
## Prerequisites

* Your script must work in interpreted mode. Syntax errors will cause exceptions during the compile. And of course any required packages must have been installed.

* Nuitka must have been installed. Use the version 0.6.3 or later. We will need several support aspects, that are not part of earlier releases, like:
    - availability of experimental feature ``pefile``
    - numpy plugin must be available under its new name ``numpy``
    - Tkinter plugin must be available under its new name ``tk-inter``

------
## Preparation
Before you can compile your script, you must execute it in a way that traces and records all Python ``import`` statements.

You need **all** of the following files in the **same folder**:
* ``yourscript.py`` - script created by you
* ``get-hints.py`` - script in this directory

In order to do this tracing, now execute the following command in that folder:

``python get-hints.py yourscript.py arg1 arg2 ...``

This will run your script in the normal way, interpreted by Python. You can pass arguments to it as usual, and you will see its output like normal, any GUI windows will appear, etc.

When your script finishes, the service script ``get-hints.py`` will collect and process the import trace(s) that your script has produced while executing. The final result will be a JSON file of name ``yourscript-<...>.json`` in the same directory.

> The string ``<...>`` is a "platform tag", containing information on platform, Python version and bitness this file has been created under. If you eg. want to compile the same script for different operating systems, you will need to run ``get-hints.py`` in each of those cases.

Each time you change your script, please also re-execute the above command before compiling it again. This ensures, that any changes to imported modules are correctly reflected in the JSON file.

See [here](https://github.com/Nuitka/NUITKA-Utilities/edit/master/hinted-compilation/get-hints.jpg) for a graphical overview of this process.

------
## Compilation
For compilation, you need **all** of the following files -  again in the **same folder**:
* ``yourscript.py`` - script created by you
* ``yourscript-<...>.json`` - file created in previous step
* ``nuitka-hints.py`` - file in this directory
* ``hinted-mods.py`` - file in this directory

Execute the following command to compile your **_pytorch_** script:

``python nuitka-hints.py --user-plugin=torch-plugin.py yourscript.py``

Execute this command for other scripts (imit the torch plugin):

``python nuitka-hints.py yourscript.py``

``nuitka-hints.py`` will invoke the Nuitka compiler with all required parameters generated automatically.

You may see a number of information messages about ignored modules (which you can ignore). There may also be some warnings which you can ignore, too (hopefully).

The duration of the compile will obviously vary with the size of your script and with the number of packages it uses. Using complex packages like ``pytorch``, ``sklearn``, ``numpy``, ``scipy`` and similar will cause compile times go up to several minutes.

See [here](https://github.com/Nuitka/NUITKA-Utilities/edit/master/hinted-compilation/hinted-compile.jpg) for a graphical overview of this process.

------
## Testing the result
Enter the folder ``yourscript.dist`` and execute the command

``yourscript.exe args1 arg2 ...``

You should get the same result as in interpreted mode.

------
## Remarks
We recommend using this feature to do all your standalone compiles. The benefits are:

* **shorter compile times**: because it is known which parts of which packages your program actually uses, the compiler will only process those (and not all it finds somewhere in the code).
* **smaller** ``dist`` **folder**, because unused code will not become part of it.
* **shorter command line**: the invoker script ``nuitka-hints.py`` has a list of options which it passes to the Nuitka compiler. It also automatically turns off the console window, if your script ends with ``.pyw``. It enables user plugin ``hinted-mods.py`` which in turn **dynamically enables** required standard plugins.
* If you need different standard compile options for your installation, just edit ``nuitka-hints.py`` and make change to its options list.
* You can also specify any of nuitka's command line options when needed.

------
## Example
Let us assume that your script uses PyQt, Numpy and Scipy.

Then the normal standalone command line will need to look like this:

```
python -m nuitka --standalone --python-flag=nosite --enable-plugin=numpy=scipy --enable-plugin=qt-plugins yourscript.py
```

Or even more options may be needed to reflect your compiler choice and what not.

If you have created ``yourscript.json`` with the method above, the same result can be achieved with the following short command line (and probably in shorter compile time and with a smaller ``dist`` folder):

```
python nuitka-hints.py yourscript.py
```
User plugin ``hinted-mods.py`` detects that standard plugins are required by the script and enables these correspondingly.

> The following standard plugins are currently supported:
> * numpy / scipy
> * tk-inter
> * qt-plugins
> * multiprocessing
> * pmw-freezer
> * torch
> * scikit-learn
> * tensorflow
