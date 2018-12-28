# Case Study: Standalone Folder Sizes of Nuitka vs. PyInstaller
It has been observed that folder sizes of standalone applications generated with Nuitka are very large compared to the corresponding output of other alternatives like PyInstaller.

And indeed, generating a simple "Hello, world!" script as an "EXE" file under Windows results in the following sizes (MB). To reduce distribution size, the binary compression utility was executed for applicable files using two different compression options (LZMA and GZIP).

| UPX: | --lzma | -9 | none |
| ------ | ---- | -- | ------ |
| PyInstaller | 7.18 | 7.4 | **10.4** |
| Nuitka | 19.4 | 21.3 | **51.1** |

As can be seen, the Nuitka size is 3 to 5 times larger. But the situation ***changes radically*** for complex scripts - when it counts!

## Case
I have two scripts which do some Image formatting and watermarking for Instagram publications. They jointly use the following set of imports:

```python
import os                       # both
from PIL import Image           # both
import piexif                   # both
import PySimpleGUI as sg        # both
import base64                   # script 1
from io import BytesIO          # script 1
import fitz                     # script 2
```

Putting the standalone binaries together in one **common distribution folder** yielded the following results (MB):

| UPX: | --lzma | -9 | none |
| ------ | ---- | -- | ------ |
| PyInstaller | 150.0 | 175.2 | **613.0** |
| Nuitka | 50.0 | 55.6 | **151.1** |

> I would argue that the PyInstaller non-compressed folder size is prohibitively large (**613 MB!!**) for, after all, just two scripts with a total line count of about 500. Even the UPX-compressed sizes are three times larger than the Nuitka alternative.
>
> And we should not forget that UPX-compressed binaries **do suffer** from a performance penalty. Admittedly, it is low and it only hits at first-time use of a binary during any single execution. But the Nuitka non-compressed folder still favorably competes with every compressed PyInstaller folder.

## Environment information:
* Windows Version 10.0.17134.472
* VS 2017 Community C++ Compiler
* Python v3.7.1 64bit
* PyInstaller v3.4
* Nuitka v0.6.1rc9
