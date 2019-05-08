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
from nuitka.utils.Timing import StopWatch


def get_checklist(full_name):
    """ Generate a list of names that may contain the 'full_name'.

    Notes:
        If full_name = "a.b.c", then ["a.b.c", "a.*", a.b.*", "a.b.c.*"] is
        generated.
    Args:
        full_name: The full module name
    Returns:
        List of possible "containers".
    """
    if not full_name:
        return []
    mtab = full_name.split(".")
    checklist = [full_name]
    m0 = ""
    for m in mtab:
        m0 += "." + m if m0 else m
        checklist.append(m0 + ".*")
    return tuple(checklist)


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
        self.import_info = json.loads(fin.read())  # read it and make an array
        fin.close()
        self.import_calls = self.import_info["calls"]
        self.import_files = self.import_info["files"]

        """
        Check if we should enable any standard plugins.
        Currently supported: "tk-inter", "numpy", "multiprocessing" and
        "qt-plugins". For "numpy", we also support the "scipy" option.
        """
        tk = np = qt = sc = mp = pmw = torch = sklearn = False
        tflow = enum = gevent = False
        msg = " '%s' is adding the following options:" % self.plugin_name
        for mod in self.import_calls:  # scan thru called items
            m = mod[0]
            if m == "numpy":
                np = True
            elif m in ("tkinter", "Tkinter"):
                tk = True
            elif m.startswith(("PyQt", "PySide")):
                qt = True
            elif m == "scipy":
                sc = True
            elif m == "multiprocessing":
                mp = True
            elif m == "Pmw":
                pmw = True
            elif m == "torch":
                torch = True
            elif m == "sklearn":
                sklearn = True
            elif m == "tensorflow":
                tflow = True
            elif m == "enum":
                enum = True
            elif m == "gevent":
                gevent = True

        info(msg)

        if np:
            o = "numpy" if not sc else "numpy=scipy"
            options.plugins_enabled.append(o)
            info(" --enable-plugin=" + o)

        if tk:
            options.plugins_enabled.append("tk-inter")
            info(" --enable-plugin=tk-inter")

        if qt:
            options.plugins_enabled.append("qt-plugins=all")
            info(" --enable-plugin=qt-plugins=all")

        if mp:
            options.plugins_enabled.append("multiprocessing")
            info(" --enable-plugin=multiprocessing")

        if pmw:
            options.plugins_enabled.append("pmw-freezer")
            info(" --enable-plugin=pmw-freezer")

        if torch:
            options.plugins_enabled.append("torch")
            info(" --enable-plugin=torch")

        if sklearn:
            options.plugins_enabled.append("sklearn")
            info(" --enable-plugin=sklearn")

        if tflow:
            options.plugins_enabled.append("tensorflow")
            info(" --enable-plugin=tensorflow")

        if enum:
            options.plugins_enabled.append("enum-compat")
            info(" --enable-plugin=enum-compat")

        if gevent:
            options.plugins_enabled.append("gevent")
            info(" --enable-plugin=gevent")

        info("")

        for f in self.import_files:
            options.recurse_modules.append(f)
        msg = " Requested Nuitka to recurse to %i modules." % len(self.import_files)
        info(msg)
        info("")

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
            # also happens: package = a.b.c.module
            # then use package as full_name
            elif module_package.endswith(module_name):
                full_name = module_package
        else:
            full_name = module_name

        if full_name in self.ignored_modules:  # known to be ignored
            return False, "module is not used"

        if full_name in self.implicit_imports:  # known implicit import
            return True, "module is imported"  # ok

        checklist = get_checklist(full_name)
        for mod in self.import_calls:  # loop thru the called items
            m = mod[0]
            if m in checklist:
                return True, "module is hinted to"  # ok

        # check if other plugins would accept this
        for plugin in active_plugin_list:
            if plugin.plugin_name == self.plugin_name:
                continue  # skip myself of course
            rc = plugin.onModuleEncounter(
                module_filename, module_name, module_package, module_kind
            )
            if rc is not None and rc[0] is True:
                self.implicit_imports.append(full_name)
                keep_msg = " keep %s (plugin '%s')" % (full_name, plugin.plugin_name)
                info(keep_msg)
                return True, "module is imported"  # ok

        if module_package is not None:
            ignore_msg = " drop %s (in %s)" % (module_name, module_package)
        else:
            ignore_msg = " drop %s" % module_name
        info(ignore_msg)  # issue ignore message
        self.ignored_modules.append(full_name)  # faster decision next time
        return False, "module is not used"

    def onStandaloneDistributionFinished(self, dist_dir):
        self.timer.end()
        t = int(round(self.timer.delta()))
        info(" Compile time %i seconds." % t)

