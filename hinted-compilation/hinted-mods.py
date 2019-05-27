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
from nuitka.plugins.PluginBase import NuitkaPluginBase
from nuitka.plugins.Plugins import active_plugin_list
from nuitka.utils.Timing import StopWatch
from nuitka.utils.Utils import getOS


def get_checklist(full_name):
    """ Generate a list of names that may contain the 'full_name'.

    Notes:
        If full_name = "a.b.c", then the list

        ["a.b.c", "a.*", "a.b.*", "a.b.c.*"]

        is generated. So either the full name itself is found, or it is
        included in some *-import.
    Args:
        full_name: The full module name
    Returns:
        List of possible "containers".
    """
    if not full_name:  # guard against nonsense
        return []
    mtab = full_name.split(".")  # separate components by dots
    checklist = [full_name]  # full name is always looked up first
    m0 = ""
    for m in mtab:  # generate *-import names
        m0 += "." + m if m0 else m
        checklist.append(m0 + ".*")
    return tuple(checklist)  # tuples are a bit more efficient


class UserPlugin(NuitkaPluginBase):

    plugin_name = __file__

    def __init__(self):
        """ Read the JSON file and enable any standard plugins.
        """
        # start a timer
        self.timer = StopWatch()
        self.timer.start()

        self.implicit_imports = set()  # speed up repeated lookups
        self.ignored_modules = set()  # speed up repeated lookups
        options = Options.options
        fin_name = self.getPluginOptions()[0]  # the JSON  file name
        fin = open(fin_name)
        self.import_info = json.loads(fin.read())  # read it and make an array
        fin.close()
        self.import_calls = self.import_info["calls"]
        self.import_files = self.import_info["files"]
        self.msg_count = dict()
        self.msg_limit = 21
        """
        Check if we should enable any standard plugins.
        Currently supported: "tk-inter", "numpy", "multiprocessing" and
        "qt-plugins". For "numpy", we also support the "scipy" option.
        """
        show_msg = False  # only show info message if parameters are generated
        tk = np = qt = sc = mp = pmw = torch = sklearn = False
        tflow = gevent = mpl = False
        msg = " '%s' is adding the following options:" % self.plugin_name

        # detect required standard plugin in order to enable them
        for mod in self.import_calls:  # scan thru called items
            m = mod[0]
            if m == "numpy":
                np = True
                show_msg = True
            if m == "matplotlib":
                mpl = True
                show_msg = True
            elif m in ("tkinter", "Tkinter"):
                tk = True
                show_msg = True
            elif m.startswith(("PyQt", "PySide")):
                qt = True
                show_msg = True
            elif m == "scipy":
                sc = True
                show_msg = True
            elif m == "multiprocessing" and getOS() == "Windows":
                mp = True
                show_msg = True
            elif m == "Pmw":
                pmw = True
                show_msg = True
            elif m == "torch":
                torch = True
                show_msg = True
            elif m == "sklearn":
                sklearn = True
                show_msg = True
            elif m == "tensorflow":
                tflow = True
                show_msg = True
            elif m == "gevent":
                gevent = True
                show_msg = True

        if show_msg is True:
            info(msg)

        if np:
            o = "numpy="
            if mpl:
                o += "matplotlib"
            if sc:
                o += "scipy" if o.endswith("=") else ",scipy"
            options.plugins_enabled.append(o)
            info(" --enable-plugin=" + o)

        if tk:
            options.plugins_enabled.append("tk-inter")
            info(" --enable-plugin=tk-inter")

        if qt:
            options.plugins_enabled.append("qt-plugins=sensible")
            info(" --enable-plugin=qt-plugins=sensible")

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

        if gevent:
            options.plugins_enabled.append("gevent")
            info(" --enable-plugin=gevent")

        for f in self.import_files:
            options.recurse_modules.append(f)

        # no plugin detected, but recursing to modules?
        if show_msg is False and len(self.import_files) > 0:
            info(msg)

        msg = " --recurse-to for %i imported modules." % len(self.import_files)

        if len(self.import_files) > 0:
            info(msg)
            info("")

        self.ImplicitImports = None  # the 'implicit-imports' plugin goes here
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

        # fall through for easy cases
        if full_name in self.ignored_modules:  # known to be ignored
            return False, "module is not used"

        if full_name in self.implicit_imports:  # known implicit import
            return True, "module is an implicit import"  # ok

        # check if other plugins would accept this
        for plugin in active_plugin_list:
            if plugin.plugin_name == self.plugin_name:
                continue  # skip myself of course
            rc = plugin.onModuleEncounter(
                module_filename, module_name, module_package, module_kind
            )
            if rc is not None:
                if rc[0] is True:  # plugin wants to keep this
                    self.implicit_imports.add(full_name)
                    keep_msg = " keep %s (plugin '%s')" % (
                        full_name,
                        plugin.plugin_name,
                    )
                    count = self.msg_count.get(plugin.plugin_name, 0)
                    if count < self.msg_limit:
                        info(keep_msg)
                    self.msg_count[plugin.plugin_name] = count + 1
                    if count == self.msg_limit:
                        info(
                            " ... 'keep' msg limit exceeded for '%s'."
                            % plugin.plugin_name
                        )
                    return True, "module is imported"  # ok
                # plugin wants to drop this
                self.ignored_modules.add(full_name)
                ignore_msg = " drop %s (plugin '%s')" % (full_name, plugin.plugin_name)
                info(ignore_msg)
                return False, "dropped by plugin " + plugin.plugin_name

        if full_name == "cv2":
            return True, "needed by OpenCV"

        checklist = get_checklist(full_name)
        for mod in self.import_calls:  # loop thru the called items
            m = mod[0]
            if m in checklist:
                return True, "module is hinted to"  # ok

        # next we ask if implicit imports knows our candidate
        if self.ImplicitImports is None:  # the plugin is not yet loaded
            for plugin in active_plugin_list:
                if plugin.plugin_name == "implicit-imports":
                    self.ImplicitImports = plugin
                    break
            if self.ImplicitImports is None:
                sys.exit("could not find 'implicit-imports' plugin")

        # ask the 'implicit-imports' plugin whether it knows this guy
        if module_package is not None:
            import_set = self.ImplicitImports.getImportsByFullname(module_package)
            import_list0 = [item[0] for item in import_set]  # only the names
            if full_name in import_list0:  # found!
                for item in import_list0:  # store everything in that list
                    self.implicit_imports.add(item)
                return True, "module is an implicit imported"  # ok

        # not known by anyone: kick it out!
        if module_package is not None:
            ignore_msg = " drop %s (in %s)" % (module_name, module_package)
        else:
            ignore_msg = " drop %s" % module_name
        info(ignore_msg)  # issue ignore message

        # faster decision next time
        self.ignored_modules.add(full_name)
        return False, "module is not used"

    def onStandaloneDistributionFinished(self, dist_dir):
        self.timer.end()
        t = int(round(self.timer.delta()))
        if t > 300:
            t = int(round(t / 60.0))
            unit = "minutes"
        else:
            unit = "seconds"
        info(" Compile time %i %s." % (t, unit))

