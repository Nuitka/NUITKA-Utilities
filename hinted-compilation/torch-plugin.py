#     Copyright 2019, Jorj McKie, mailto:<jorj.x.mckie@outlook.de>
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
""" This script is a user plugin to be invoked by the Nuitka compiler.

It ensures correct standalone compilation of scripts using torch and torchvision.
"""
import os
import sys
import pkgutil
import shutil
from logging import info
from nuitka import Options
from nuitka.plugins.PluginBase import UserPluginBase
from nuitka.plugins.Plugins import active_plugin_list
from nuitka.utils.Utils import isWin32Windows
from nuitka.ModuleRegistry import (
    getRootModules,
    done_modules,
    uncompiled_modules,
    active_modules,
)


def get_module_file_attribute(package):
    """ Get the absolute path of the module with the passed-in name.

    Args:
        package: the fully-qualified name of this module.
    Returns:
        absolute path of this module.
    """
    loader = pkgutil.find_loader(package)
    attr = loader.get_filename(package)
    if not attr:
        raise ImportError
    return attr


def get_torch_core_binaries():
    """ Return required files from the torch/lib folder.

    Notes:
        So far only prepared for Windows. Requirements for other platforms
        are unknown.
    """
    binaries = []
    if not isWin32Windows():
        return binaries
    extra_dll = os.path.join(os.path.dirname(get_module_file_attribute("torch")), "lib")
    if not os.path.isdir(extra_dll):
        return binaries

    netto_bins = os.listdir(extra_dll)

    for f in netto_bins:
        # apart from DLLs, also the C header files are required!
        if not f.endswith((".dll", ".h")):
            continue
        binaries.append((os.path.join(extra_dll, f), "."))

    return binaries


class Usr_Plugin(UserPluginBase):

    plugin_name = __file__

    def __init__(self):
        """ Maintain switch to ensure once-only copy of torch/lib files.
        """
        self.files_copied = False
        return None

    def onModuleEncounter(
        self, module_filename, module_name, module_package, module_kind
    ):
        """ Help decide whether to include a module.

        Notes:
            'torchvision.transforms' always imports its 'functional' module,
            which in turn imports several PIL modules. Here we maintain a list
            of these modules and indicate they are required.
        """
        if module_package == "torchvision.transforms":
            # accept everything under this package
            return True, "basic torchvision module"

        if module_package == "PIL" and module_name in (
            "Image",
            "ImageColor",
            "ImageOps",
            "ImageEnhance",
            "ImageStat",
            "ImageFilter",
        ):  # these are imported directly or indirectly by 'functional.py'.
            return True, "required by torchvision"
        return None  # we have no opinion about other stuff

    def considerExtraDlls(self, dist_dir, module):
        """ Copy extra files from torch/lib.

        Args:
            dist_dir: the name of the progscript's dist folder
            module: module object (not used here)
        Returns:
            empty tuple
        """
        if self.files_copied is True:  # not the first time here
            return ()

        if module.getFullName() == "torch":
            self.files_copied = True  # fall thru next time
            binaries = get_torch_core_binaries()
            bin_total = len(binaries)
            if bin_total == 0:
                return ()
            info("")
            info(" Copying files from 'torch/lib':")
            for f in binaries:
                bin_file = f[0].lower()  # full binary file name
                idx = bin_file.find("torch")  # this will always work (idx > 0)
                back_end = bin_file[idx:]  # tail of the string
                tar_file = os.path.join(dist_dir, back_end)

                # create any missing intermediate folders
                if not os.path.exists(os.path.dirname(tar_file)):
                    os.makedirs(os.path.dirname(tar_file))

                shutil.copy(bin_file, tar_file)

            msg = " Copied %i %s."
            msg = msg % (bin_total, "binary" if bin_total < 2 else "binaries")
            info(msg)
        return ()
