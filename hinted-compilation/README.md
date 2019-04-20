# How to compile scripts in standalone profile-guided mode with Nuitka
This is a description focussing on things that must be done - without providing much detail of **why** things must be done in exactly this way.

All steps explained in the following must be done **exactly** as described.

This text is based on experience made on a Windows 10 platform. Doing a similar thing on different platforms like Linux or Mac OSX will require changes - allthough hopefully much of this can be adopted in an obvious way.

## Prerequisites

* Your script must work in interpreted mode. Syntax errors will cause exceptions in the compile.

* Nuitka must have been installed. Use the current **development** version. We will need several support aspects, that are not yet part of the regular release, like:
    - availability of experimental feature ``pefile``
    - numpy plugin must be available under its new name ``numpy``
    - Tkinter plugin must be available under its new name ``tk-inter``

## Preparation
Before you actually can compile your script, it must be executed in a way that traces and records all Python ``import`` statements.

You need **all** of the following files in the **same folder**:
* ``yourscript.py`` - script created by you
* ``get-hints.py`` - script in this directory

In order to do this tracing, now execute the following command in that folder:

``python get-hints.py yourscript.py arg1 arg2 ...``

This will run your script in the normal way, interpreted by Python. You can pass arguments to it as usual, and you will see its output like normal, any GUI windows will appear, etc.

When your script finishes, the service script ``get-hints.py`` will collect the import trace that your script has produced while executing. The result will be a JSON file of name ``yourscript.json`` in the same directory.

Every time you change your script, please also re-execute the above command. This ensures, that any changes to imported modules are correctly reflected in the JSON file.

See [here](https://github.com/Nuitka/NUITKA-Utilities/edit/master/hinted-compilation/get-hints.jpg) for a graphical overview of this process.

## Compilation
For compilation, you need **all** of the following files again in the **same folder**:
* ``yourscript.py`` - script created by you
* ``yourscript.json`` - file created in previous step
* ``torch-plugin.py`` - for **_pytorch_** scripts only, file in this directory
* ``nuitka-hints.py`` - file in this directory
* ``hinted-mods.py`` - file in this directory

Execute the following command to compile your **_pytorch_** script:

``python nuitka-hints.py --user-plugin=torch-plugin.py yourscript.py``

Execute this command for other scripts:

``python nuitka-hints.py yourscript.py``

``nuitka-hints.py`` will invoke the Nuitka compiler with all required parameters generated automatically.

You should see quite a large number of information messages, which you can ignore. There may also be some warnings which you can ignore, too (hopefully).

The duration of the compile will obviously vary with the size of your script and with the number of packages it uses. Using complex packages like ``pytorch``, ``sklearn``, ``numpy``, ``scipy`` and similar will cause compile times go up to several minutes.

See [here](https://github.com/Nuitka/NUITKA-Utilities/edit/master/hinted-compilation/hinted-compile.jpg) for a graphical overview of this process.

## Testing the result
Enter the folder ``yourscript.dist`` and execute the command

``yourscript.exe args1 arg2 ...``

You should get the same result as in interpreted mode.

**_Important_**: you must type the complete name ``yourscript.exe`` - **including the** ``.exe`` **suffix!** If you don't do this, your script may fail if it uses multiprocessing features. This restriction in the current (0.6.3) development version will be lifted in one of the next releases.

## Remarks
We recommend using this feature to do all your standalone compiles. The benefits are:

* shorter compile times: because it is known which parts of which packages your program actually uses, the compiler will only process those and ignore others that are also contained somewhere in the code.
* smaller ``dist`` folders, because unused code will not become a part of it.
* shorter command line: the invoker script ``nuitka-hints.py`` has a list of options which it passes to the Nuitka compiler. It cooperates with ``hinted-mods.py`` (a user plugin which it automatically activates) to **dynamically enable** any other of the standard plugins as required. It also automatically switches off the console window, it your script ends with ``.pyw``. If you need different options for your installation, just edit ``nuitka-hints.py`` and change the options list.

Assuming that your script uses PyQt, numpy and scipy, the normal command line will look like this:

```
python -m nuitka --standalone --python-flag=nosite --enable-plugin=numpy=scipy --enable-plugin=qt-plugins yourscript.py
```

Even more options may be needed to reflect your compiler choice and what not.

If you have created ``yourscript.json`` with the method above, the same result can be achieved with the following command line (but probably quicker and with a smaller ``dist`` folder):

```
python nuitka-hints.py yourscript.py
```
All of the above options have been generated.
