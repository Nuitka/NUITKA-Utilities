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
""" This script is a user plugin to be invoke by the Nuitka compiler.

Via the plugin option mechanism, it must be given the name of a JSON file,
which contains all the package and module names that the to-be-compiled script
invokes.
An array of these items is created and immediately used to detect any standard
plugins that must be enabled.

During the compilation process, for every encountered module Nuitka will ask
this plugin, whether to include it.
"""
import os
import sys
import json
from logging import info
from nuitka import Options
from nuitka.plugins.PluginBase import UserPluginBase
from nuitka.plugins.Plugins import active_plugin_list
from nuitka.ModuleRegistry import (
    getRootModules,
    done_modules,
    uncompiled_modules,
    active_modules,
)
from nuitka.utils.Timing import StopWatch


def getNuitkaModules():
    """ Create a list of all modules known to Nuitka.

    Notes:
        This will be executed at most once: on the first time when a module
        is encountered and cannot be found in the recorded calls (JSON array).
    Returns:
        List of all modules.
    """
    mlist = []
    for m in getRootModules():
        if m not in mlist:
            mlist.append(m)

    for m in done_modules:
        if m not in mlist:
            mlist.append(m)

    for m in uncompiled_modules:
        if m not in mlist:
            mlist.append(m)

    for m in active_modules:
        if m not in mlist:
            mlist.append(m)

    return mlist


class Usr_Plugin(UserPluginBase):

    plugin_name = __file__

    def __init__(self):
        """ Read the JSON file and enable any standard plugins.
        """
        # start a timer
        self.timer = StopWatch()
        self.timer.start()

        self.implicit_imports = []  # speed up repeated lookups
        self.ignored_modules = []  # speed up repeated lookups
        self.nuitka_modules = False  # switch when checking Nuitka modules
        options = Options.options

        fin_name = self.getPluginOptions()[0]  # the JSON  file name
        fin = open(fin_name)
        self.modules = json.loads(fin.read())  # read it and make an array
        fin.close()

        """
        Check if we should enable any standard plugins.
        Currently supported: "tk-inter", "numpy", "multiprocessing" and
        "qt-plugins". For "numpy", we also support the "scipy" option.
        """
        tk = np = qt = sc = mp = False
        msg = " Enabling the following plugins:"
        for m in self.modules:  # scan thru called items
            if m == "numpy":
                np = True
            elif m == "_tkinter":  # valid indicator for PY2 and PY3
                tk = True
            elif m.startswith(("PyQt", "PySide")):
                qt = True
            elif m == "scipy":
                sc = True
            elif m == "multiprocessing":
                mp = True

        if any((tk, np, sc, qt, mp)):
            info(msg)

        if np:
            o = "numpy" if not sc else "numpy=scipy"
            options.plugins_enabled.append(o)
            info(" --enable-plugin=" + o)

        if tk:
            options.plugins_enabled.append("tk-inter")
            info(" --enable-plugin=tk-inter")

        if qt:
            options.plugins_enabled.append("qt-plugins")
            info(" --enable-plugin=qt-plugins")

        if mp:
            options.plugins_enabled.append("multiprocessing")
            info(" --enable-plugin=multiprocessing")

        return None

    def onModuleEncounter(
        self, module_filename, module_name, module_package, module_kind
    ):
        """ Help decide whether to include a module.

        Notes:
            Performance considerations: the calls array is rather long
            (may be thousands of items). So we store ignored modules
            separately and check that array first.
            We also maintain an array for known implicit imports and early
            check against them, too.

        Args:
            module_filename: filename (not used here) 
            module_name: module name
            module_package: package name
            module_kind: one of "py" or "shlib" (not used here)

        Returns:
            None, (True, 'text') or (False, 'text').
            Example: (False, "because it is not called").
        """
        if module_package:
            # the standard case:
            full_name = module_package + "." + module_name

            # also happens: module_name = package.module
            # then use module_name as the full_name
            if module_name.startswith(module_package):
                t = module_name[len(module_package) :]
                if t.startswith("."):
                    full_name = module_name
        else:
            full_name = module_name

        if full_name in self.ignored_modules:  # known to be ignored
            return False, "module is not used"

        if full_name in self.implicit_imports:  # known implicit import
            return None

        for m in self.modules:  # loop thru the called items
            if m == full_name:  # full name found
                return None  # ok
            if m == full_name + ".*":  # is a '*'-import
                return None  # ok
            if module_package and m == module_package + ".*":
                # is part of a package
                return None  # ok

        """
        We have a dubious case here:
        Check if full_name is one of the implicit imports.
        Expensive logic, but can only happen once per module.
        Scan through all modules identified by Nuitka and ask each active
        plugin, if full_name is an implicit import of any of them.
        """
        if not self.nuitka_modules:  # first time here?
            # make our copy of implicit import names known to Nuitka modules.
            modules = []
            for m in getNuitkaModules():
                for plugin in active_plugin_list:
                    for im in plugin.getImplicitImports(m):
                        modules.append(im[0])
            self.implicit_imports = sorted(list(set(modules)))
            self.nuitka_modules = True

        if full_name not in self.implicit_imports:
            # check if other plugins would accept this
            for plugin in active_plugin_list:
                if plugin.plugin_name == self.plugin_name:
                    continue
                rc = plugin.onModuleEncounter(
                    module_filename, module_name, module_package, module_kind
                )
                if rc is not None and rc[0] is True:
                    self.implicit_imports.append(full_name)

        if full_name in self.implicit_imports:
            # full_name is acceptable for someone else
            info(" implicit: " + full_name)
            return None  # ok

        ignore_msg = " ignoring %s (%s)" % (module_name, module_package)
        info(ignore_msg)  # issue ignore message
        self.ignored_modules.append(full_name)  # faster decision next time
        return False, "module is not used"

    def onStandaloneDistributionFinished(self, dist_dir):
        self.timer.end()
        t = int(round(self.timer.delta()))
        info(" Compile time %i seconds." % t)

