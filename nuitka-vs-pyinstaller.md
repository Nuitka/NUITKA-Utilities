# Case Study: Standalone Folder Sizes of Nuitka vs. PyInstaller
It has been observed that folder sizes of standalone applications generated with Nuitka are very large compared to the corresponding output of other alternatives like PyInstaller.

And indeed, generating a simple "Hello, world!" script as an "EXE" file under Windows results in the following sizes (MB). To reduce distribution size, the binary compression utility was executed for applicable files using two different compression options (LZMA and GZIP).

| UPX: | --lzma | -9 | none |
| ------ | ---- | -- | ------ |
| PyInstaller | 7.18 | 7.4 | 10.4 |
| Nuitka | 19.4 | 21.3 | 51.1 |

But the situation ***changes radically*** for complex scripts!

## Case
Two scripts using the following imports:

```python
import os
from PIL import Image
import piexif
import PySimpleGUI as sg
import base64
from io import BytesIO
import fitz
```

Packed together in one **common distribution folder** yielded the following results (MB):

| Method | lzma | -9 | normal |
| ------ | ---- | -- | ------ |
| PyInstaller | 150.0 | 175.2 | 613.0 |
| Nuitka | 50.0 | 55.6 | 151.1 |

> I would argue that the PyInstaller non-compressed folder size is prohibitively large for -- after all -- just two scripts with a total line count of about 500. The compression sizes are still about three times larger than the Nuitka alternative.

## Environment information:
* Windows Version 10.0.17134.472
* Python v3.7.1 64bit
* PyInstaller v3.4
* Nuitka v0.6.1rc9