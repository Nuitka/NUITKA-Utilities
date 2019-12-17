# How to compile scripts in standalone, profile-guided mode with Nuitka
"Hinted compilation" is a way to compile scripts in **standalone** mode with Nuitka. In addition to basic Nuitka compilation, **hinted** compilation uses information about which Python ``import`` statements a script **actually executes** when running. The **executed** ``import`` statements are often a significantly smaller set, than the total number of statements found by Nuitka's source code analysis.

Obviously, a smaller number of modules leads to a **smaller ``dist`` folder size** and a **shorter compile time**.

Another benefit of this approach: knowing the used packages allows to exactly configure Nuitka's compilation parameters. Most prominently, all required Nuitka **standard plugins** are detected and automatically included.

The basic logic of hinted compilation is as follows:
* Tell Nuitka to **follow no imports** automatically (``--recurse-none``)
* Tell Nuitka which **standard plugins** should be enabled by generating all required ``--enable-plugin`` arguments
* Tell Nuitka which modules / packages should be loaded by generating all required ``--recurse-to`` arguments
* When Nuitka then parses these ``--recurse-to`` modules, for each encountered ``import`` statement Nuitka will ask whether to follow it. The hinting logic will provide the appropriate answers based on its recorded information. This will lead to a rather fine-grained set of packages, sub-packages and modules included in the ``dist`` folder.

------
## Prerequisites

* As always when using Nuitka: Your script first **must work in interpreted mode**. Syntax errors will cause exceptions during the compile. And of course all required packages must have been installed.

* Nuitka must have been installed - preferably the current version or even its development branch when running into issues. But be sure to use at least version 0.6.6.

* Hinted compilation is for **standalone** mode only. It does not work, or respectively makes no sense otherwise.

------
## Preparation
Before you can compile your script with Nuitka, you must execute it in a way that records all Python ``import`` statements in a logfile. Achieve this by running the following script:

You need **all** of the following files in the **same folder**:
* ``yourscript.py`` - the script you want to compile
* ``get-hints.py`` - script in this repository folder

In order to create the logfile, now execute the following command in that folder. This will run your script in the normal, interpreted way. You can pass arguments to it as usual, and you will see any output like normal, any GUI windows will appear, etc.

```
python get-hints.py yourscript.py arg1 arg2 ...
```

When your script finishes, the service script ``get-hints.py`` will collect and process the import traces produced by your script. The final result will be a JSON file with the name ``yourscript-<...>.json``, again in the same directory.

> The string ``<...>`` is a "platform tag", containing information on platform, Python version and bitness. You must execute the above again if any of these change. And of course you also should re-execute after any changes to your script.

> This ensures, that any changes to imported modules are correctly reflected in the JSON file(s).

See [here](https://github.com/Nuitka/NUITKA-Utilities/edit/master/hinted-compilation/get-hints.jpg) for a graphical overview of this process.

------
## Compilation
After completing the previous step, you can now compile your script in standalone mode with Nuitka. You need **all** of the following files -  again in the **same folder**:
* ``yourscript.py`` - the script you want to compile
* ``yourscript-<...>.json`` - file created in previous step
* ``nuitka-hints.py`` - script in this repository folder
* ``hinted-mods.py`` - script in this repository folder

**Compile your script** in standalone mode with this command:
```
python nuitka-hints.py yourscript.py
```

``nuitka-hints.py`` **invokes the Nuitka compiler** with a number of standard parameters which you can adapt to your environment.

``hinted-mods.py`` is a **user plugin** for the Nuitka compiler. It will read ``yourscript-<...>.json`` and generate required ``--enable-plugin`` and ``--recurse-to`` parameters during its initialization.

Later, during compilation, it will be asked by Nuitka whether to include specific components and decide appropriately. You will see ``keep`` and ``drop`` info messages reflecting these decisions.

See [here](https://github.com/Nuitka/NUITKA-Utilities/edit/master/hinted-compilation/hinted-compile.jpg) for a graphical overview of this process.

------
## Testing the result
Enter the folder ``yourscript.dist`` and execute the command

```
Windows: yourscript.exe arg1 arg2 ...
Linux:   ./yourscript arg1 arg2 ...
```

You should get the same result as in interpreted mode.

------
## Remarks
We recommend using this feature to do all your standalone compiles. The benefits are:

* **shorter compile times**: because it is known which parts of which packages your program actually uses, the compiler will only process those (and not all it finds somewhere in each corner of the code).
* **smaller ``dist`` folder**, because lots of unused code will not become part of it.
* **shorter command line**: the invoker script ``nuitka-hints.py`` has a list of options which it passes to the Nuitka compiler. It also automatically turns off the console window, if your script ends with ``.pyw``. It enables user plugin ``hinted-mods.py`` which in turn **dynamically enables** required standard plugins.
* If you need different standard compile options for your installation, just edit ``nuitka-hints.py`` and make change to its options list (``my_opts``).
* Additional Nuitka's command line options are also fully supported as before. Include them before your script. Add e.g. icon inclusion and other stuff in this way.

------
## Example 1
Let us assume your script uses **PyQt**, **Numpy** and **Scipy**.

Then the normal standalone command line will then need to look like this:

```
python -m nuitka --standalone --python-flag=nosite --enable-plugin=numpy=scipy --enable-plugin=qt-plugins yourscript.py
```

More options may be needed to reflect your compiler choice, console window suppression, and what not.

If you have created ``yourscript.json`` like above, the same result can be achieved with the following short command line (**and** probably in shorter compile time **and** with a smaller ``dist`` folder):

```
python nuitka-hints.py yourscript.py
```

------
## Example 2
Now a simple, real life example (on Windows) compiled for standalone using a number of alternatives. This is the script:

```python
from PIL import Image
import base64, io, time

infile64 = base64.b64decode(  # some image in base64 encoding
    b"iVBORw0KGgoAAAANSUhEUgAAAMYAAADHCAYAAABCxyz4AAAABGdBTUEAALGPC/xhBQAAAA"
    ... more data ...
)

img = Image.open(io.BytesIO(infile64))
print("image format: %s (%s)" % (img.format, img.format_description))
print("image size:", img.size)
print("image info:", img.info)
print("***** PIL test successful *****")
```

Compiling this without any special precautions looked like this, took about **5 minutes** and generated a ``dist`` folder of **67 MB**.

```
D:\Jorj\Desktop\Develop\nuitka>python -m nuitka --standalone pil-test.py
Nuitka:WARNING:Use '--plugin-enable=qt-plugins' for: Inclusion of Qt plugins.
Nuitka:WARNING:Use '--plugin-enable=numpy' for: numpy support.
Nuitka:WARNING:Unresolved '__import__' call at 'C:\Users\Jorj\AppData\Local\Programs\Python\Python37\lib\site-packages\PIL\Image.py:428' may require use of '--include-plugin-directory' or '--include-plugin-files'.
Nuitka:WARNING:Unresolved '__import__' call at 'C:\Users\Jorj\AppData\Local\Programs\Python\Python37\lib\site-packages\cffi\verifier.py:151' may require use of '--include-plugin-directory' or '--include-plugin-files'.
Nuitka:WARNING:Unresolved '__import__' call at 'C:\Users\Jorj\AppData\Local\Programs\Python\Python37\lib\site-packages\numpy\core\function_base.py:453' may require use of '--include-plugin-directory' or '--include-plugin-files'.
Nuitka:WARNING:Unresolved '__import__' call at 'C:\Users\Jorj\AppData\Local\Programs\Python\Python37\lib\site-packages\numpy\lib\utils.py:366' may require use of '--include-plugin-directory' or '--include-plugin-files'.
Nuitka:WARNING:Unresolved '__import__' call at 'C:\Users\Jorj\AppData\Local\Programs\Python\Python37\lib\site-packages\numpy\lib\utils.py:865' may require use of '--include-plugin-directory' or '--include-plugin-files'.
Nuitka:WARNING:Unresolved '__import__' call at 'C:\Users\Jorj\AppData\Local\Programs\Python\Python37\lib\site-packages\numpy\lib\utils.py:923' may require use of '--include-plugin-directory' or '--include-plugin-files'.
Nuitka:WARNING:Unresolved '__import__' call at 'C:\Users\Jorj\AppData\Local\Programs\Python\Python37\lib\site-packages\py\_vendored_packages\apipkg.py:69' may require use of '--include-plugin-directory' or '--include-plugin-files'.
```
A number of warnings are issued by Nuitka, because its source code parsing finds references to Qt and Numpy (both are contained in PIL by the way). My script does not use either of them ... but how is Nuitka's source code parsing supposed to know that?

In an effort to react to the plugin warnings, the next alternative tries to exclude numpy and Qt. The revised compile took about **3 minutes** and generated a ``dist`` folder size of **50 MB**.

```
D:\Jorj\Desktop\Develop\nuitka>python -m nuitka --standalone --recurse-not-to=numpy --recurse-not-to=PyQt5 pil-test.py
Nuitka:WARNING:Use '--plugin-enable=qt-plugins' for: Inclusion of Qt plugins.
Nuitka:WARNING:Unresolved '__import__' call at 'C:\Users\Jorj\AppData\Local\Programs\Python\Python37\lib\site-packages\PIL\Image.py:428' may require use of '--include-plugin-directory' or '--include-plugin-files'.
Nuitka:WARNING:Unresolved '__import__' call at 'C:\Users\Jorj\AppData\Local\Programs\Python\Python37\lib\site-packages\cffi\verifier.py:151' may require use of '--include-plugin-directory' or '--include-plugin-files'.
```

As we see, some import to some unknown Qt component inside PIL is still happening ...

Now the hinted compilation alternative.

1. Run ``get-hints.py``

```
$ python get-hints.py pil-test.py
image format: PNG (Portable network graphics)
image size: (198, 199)
image info: {'gamma': 0.45455, 'srgb': 0, 'chromaticity': (0.3127, 0.329, 0.64, 0.33, 0.3, 0.6, 0.15, 0.06), 'aspect': (72, 72)}
***** PIL test successful *****
Call cleaning has removed 42 items.
```

2. Hinted compilation

```
$ python nuitka-hints.py pil-test.py
NUITKA v0.6.6rc7 on Python 3.7.5 (win32) is compiling 'pil-test.py' with these options:
 --standalone
 --remove-output
 --recurse-none

Nuitka:INFO:User plugin 'hinted-mods.py' is being loaded.
Nuitka:INFO:'hinted-mods.py' is adding the following options:
Nuitka:INFO:--recurse-to for 36 imported modules.
Nuitka:INFO:
Nuitka:INFO:drop site
Nuitka:INFO:drop tempfile
Nuitka:INFO:drop PyAccess (in PIL)
Nuitka:INFO:drop ImageFilter (in PIL)
Nuitka:INFO:drop ImageQt (in PIL)
Nuitka:INFO:drop ImageShow (in PIL)
Nuitka:INFO:drop colorsys
Nuitka:INFO:drop random
Nuitka:INFO:drop subprocess
Nuitka:INFO:drop MpoImagePlugin (in PIL)
Nuitka:INFO:drop copy
Nuitka:INFO:drop _cffi_backend
Nuitka:INFO:drop cparser (in cffi)
Nuitka:INFO:drop verifier (in cffi)
Nuitka:INFO:drop sysconfig
Nuitka:INFO:drop dir_util (in distutils)
Nuitka:INFO:drop recompiler (in cffi)
Nuitka:INFO:drop util (in ctypes)
Nuitka:INFO:drop _ctypes
Nuitka:INFO:drop _collections_abc
Nuitka:WARNING:Not recursing to unused '__future__'.
Nuitka:WARNING:Not recursing to unused 'abc'.
Nuitka:WARNING:Not recursing to unused 'decimal'.
Nuitka:WARNING:Not recursing to unused 'fnmatch'.
Nuitka:WARNING:Not recursing to unused 'functools'.
Nuitka:WARNING:Not recursing to unused 'ntpath'.
Nuitka:WARNING:Not recursing to unused 'operator'.
Nuitka:WARNING:Not recursing to unused 'posixpath'.
Nuitka:WARNING:Not recursing to unused 'stat'.
Nuitka:WARNING:Not recursing to unused 'urllib.parse'.
Nuitka:INFO:Compile time 114 seconds.
```

This required only **2 minutes** and lead to a ``dist`` folder size of below **28 MB**.

Here is an overview of the results. Please regard it as indicative only - your scripts probably will yield different findings.

| Compile Method | dist size | compile time |
-------------- | --------- | ------------ |
| standard | 67 MB | 5 minutes |
| improved | 50 MB | 3 minutes |
| hinted | 28 MB | 2 minutes |
