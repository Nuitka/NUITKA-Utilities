#     Copyright 2019-2020, Jorj McKie, mailto:<jorj.x.mckie@outlook.de>
#     Copyright 2019-2020, Orsiris de Jong, mailto:<ozy@netpower.fr>
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
""" This script is a user plugin and invoked by the Nuitka compiler.

Via the plugin option mechanism, it must be given the name of a JSON file,
which contains all the package and module names that the to-be-compiled script
will import when running.
An array of these items is created and immediately used to detect any standard
plugins that must be enabled.

During the compilation process, for every module it encounters, Nuitka will ask
this plugin, whether to include it.
"""
import os
import sys
import json

from nuitka import Options
from nuitka.containers.oset import OrderedSet
from nuitka.containers.odict import OrderedDict
from nuitka.plugins.PluginBase import NuitkaPluginBase
from nuitka.plugins.Plugins import lateActivatePlugin, getActivePlugins
from nuitka.utils.FileOperations import getFileContents
from nuitka.utils.Timing import StopWatch
from nuitka.utils.Utils import getOS
from nuitka.Version import getNuitkaVersion


def remove_suffix(mod_dir, mod_name):
    if mod_name not in mod_dir:
        return mod_dir
    l = len(mod_name)
    p = mod_dir.find(mod_name) + l
    return mod_dir[:p]


def check_dependents(full_name, import_list):
    """ Check if we are parent of a loaded / recursed-to module file.

    Notes:
        Accept full_name if full_name.something is a recursed-to module

    Args:
        full_name: The full module name
        import_list: List of recursed-to modules
    Returns:
        Bool
    """
    search_name = full_name + "."
    for item in import_list:
        if item.startswith(search_name):
            return True
    return False


def get_checklist(full_name):
    """ Generate a list of names that may contain the 'full_name'.

    Notes:
        Eg. if full_name looks like "a.b.c", then the list

        ["a.b.c", "a.*", "a.b.*", "a.b.c.*"]

        is generated. So either the full name itself may be found, or when
        full_name is included in some *-import.
    Args:
        full_name: The full module name
    Returns:
        List of possible "containers".
    """
    if not full_name:  # guard against nonsense
        return []
    checklist = [full_name]  # full name is always looked up first
    m0 = ""
    while True:     # generate *-import names
        pkg, full_name = full_name.splitPackageName()
        if not pkg: break
        m = pkg.asString()
        m0 += "." + m if m0 else m
        checklist.append(m0 + ".*")
    return tuple(checklist)  # tuples are a bit more efficient


def drop_msg(module_name, module_package):
    """ Create info message for dropped modules.
    """
    if module_package is not None:
        ignore_msg = "drop %s (in %s)" % (module_name, module_package)
    else:
        ignore_msg = "drop %s" % module_name
    return ignore_msg


class HintedModsPlugin(NuitkaPluginBase):

    # Derive from filename, but can and should also be explicit.
    plugin_name = __name__.split(".")[-1]

    def __init__(self, hinted_json_file):
        """ Read the JSON file and enable any standard plugins.

        Notes:
            Read the JSON file produced during the get-hints step. It will
            contain a list of imported items ("calls") and a list of modules /
            packages ("files") to be loaded and recursed into.
            Depending on the items in 'files', we will trigger loading standard
            plugins.
        """

        # start a timer
        self.timer = StopWatch()
        self.timer.start()

        self.implicit_imports = OrderedSet()  # speed up repeated lookups
        self.ignored_modules = OrderedSet()  # speed up repeated lookups
        options = Options.options

        # Load json file contents from --hinted-json-file= argument
        filename = hinted_json_file
        try:
            # read it and extract the two lists
            import_info = json.loads(getFileContents(filename))
        except (ValueError, FileNotFoundError):
            raise FileNotFoundError('Cannot load json file %s' % filename)
        self.import_calls = import_info["calls"]
        self.import_files = import_info["files"]
        self.msg_count = dict()  # to limit keep messages
        self.msg_limit = 21

        # suppress pytest / _pytest / unittest?
        # TODO: disabled because self.getPluginOptionBool does not exist anymore
        #self.accept_test = self.getPluginOptionBool("test", False)
        self.accept_test = False

        """
        Check if we should enable any (optional) standard plugins. This code
        must be modified whenever more standard plugin become available.
        """
        show_msg = False  # only show info if one ore more detected
        # indicators for found packages
        tk = np = qt = scipy = mp = pmw = torch = sklearn = False
        eventlet = tflow = gevent = mpl = trio = dill = False
        msg = "'%s' is adding the following options:" % os.path.basename(
            self.plugin_name
        )

        # we need matplotlib-specific cleanup to happen first:
        # if no mpl backend is used, reference to matplotlib is removed alltogether
        if "matplotlib.backends" not in self.import_files:
            temp = [
                f
                for f in self.import_calls
                if not f.startswith(("matplotlib", "mpl_toolkits"))
            ]
            self.import_calls = temp
            temp = [
                f
                for f in self.import_files
                if not f.startswith(("matplotlib", "mpl_toolkits"))
            ]
            self.import_files = temp

        # detect required standard plugins and request enabling them
        for m in self.import_calls:  # scan thru called items
            if m in ("numpy", "numpy.*"):
                np = True
                show_msg = True
            if m in ("matplotlib", "matplotlib.*"):
                mpl = True
                show_msg = True
            elif m in ("tkinter", "Tkinter", "tkinter.*", "Tkinter.*"):
                tk = True
                show_msg = True
            elif m.startswith(("PyQt", "PySide")):
                qt = True
                show_msg = True
            elif m in ("scipy", "scipy.*"):
                scipy = True
                show_msg = True
            elif m in ("multiprocessing", "multiprocessing.*") and getOS() == "Windows":
                mp = True
                show_msg = True
            elif m in ("Pmw", "Pmw.*"):
                pmw = True
                show_msg = True
            elif m == "torch":
                torch = True
                show_msg = True
            elif m in ("sklearn", "sklearn.*"):
                sklearn = True
                show_msg = True
            elif m in ("tensorflow", "tensorflow.*"):
                tflow = True
                show_msg = True
            elif m in ("gevent", "gevent.*"):
                gevent = True
                show_msg = True
            elif m in ("eventlet", "eventlet.*"):
                eventlet = True
                show_msg = True
            elif m in ("dill", "dill.*"):
                dill = True
                show_msg = True
            # elif m in ("trio", "trio.*"):
            #    trio = True
            #    show_msg = True

        if show_msg is True:
            self.info(msg)

        to_enable = OrderedDict()

        if np:
            to_enable["numpy"] = {
                "include_matplotlib": mpl,
                "include_scipy": scipy,
                # TODO: Numpy plugin didn't use this, work in progress or not needed?
                # "sklearn" : sklearn
            }

        if tk:
            to_enable["tk-inter"] = {}

        if qt:
            # TODO more scrutiny for the qt options!
            to_enable["qt-plugins"] = {}

        if mp:
            to_enable["multiprocessing"] = {}

        if pmw:
            to_enable["pmw-freezer"] = {}            

        if torch:
            to_enable["torch"] = {}            

        if tflow:
            to_enable["tensorflow"] = {}            

        if gevent:
            to_enable["gevent"] = {}                        

        if eventlet:
            to_enable["eventlet"] = {}                                    

        if dill:
            to_enable["dill-compat"] = {}                                                

        # if trio:
        #    to_enable["trio"] = {}

        recurse_count = 0
        for f in self.import_files:  # request recursion to called modules
            if self.accept_test is False and f.startswith(
                ("pytest", "_pytest", "unittest")
            ):
                continue
            options.recurse_modules.append(f)
            recurse_count += 1

        # no plugin detected, but recursing to modules?
        if not show_msg and recurse_count > 0:
            self.info(msg)

        for plugin_name, option_values in to_enable.items():
            self.info("Enabling Nuitka plugin '%s' as needed." % plugin_name)

            # No the values could be set.
            lateActivatePlugin(plugin_name, option_values)

        if len(self.import_files) > 0:
            msg = "--recurse-to=%s and %i more modules" % (
                self.import_files[-1],
                recurse_count - 1,
            )
            self.info(msg)

        self.implicit_imports_plugin = None  # the 'implicit-imports' plugin object

    @classmethod
    def addPluginCommandLineOptions(cls, group):
        group.add_option(
            "--hinted-json-file",
            action="store",
            dest="hinted_json_file",
            default=None,
            help="[REQUIRED] Path to the json file produced by get-hints."
        )


    def onModuleEncounter(self, module_filename, module_name, module_kind):
        """ Help decide whether to include a module.

        Notes:
            Performance considerations: the calls array is rather long
            (may be thousands of items). So we store ignored modules
            separately and check that array first.
            We also maintain an array for known implicit imports and early
            check against them, too.

        Args:
            module_filename: path of the module
            module_name: module name
            module_kind: one of "py" or "shlib" (not used here)

        Returns:
            None, (True, 'text') or (False, 'text').
            Example: (False, "because it is not called").
        """
        full_name = module_name
        top_level_package_name = full_name.getTopLevelPackageName()
        package = module_name.getPackageName()
        package_dir = remove_suffix(module_filename, top_level_package_name)

        # fall through for easy cases
        if top_level_package_name == "pkg_resources":
            return None

        if (
            full_name in self.ignored_modules or top_level_package_name in self.ignored_modules
        ):  # known to be ignored
            return False, "module is not used"

        if self.accept_test is False and top_level_package_name in (
            "pytest",
            "_pytest",
            "unittest",
        ):
            self.info(drop_msg(full_name, package))
            self.ignored_modules.add(full_name)
            return False, "suppress testing components"

        if full_name in self.implicit_imports:  # known implicit import
            return True, "module is an implicit import"  # ok

        # check if other plugins would accept this
        for plugin in getActivePlugins():
            if plugin.plugin_name == self.plugin_name:
                continue  # skip myself of course
            rc = plugin.onModuleEncounter(module_filename, module_name, module_kind)
            if rc is not None:
                if rc[0] is True:  # plugin wants to keep this
                    self.implicit_imports.add(full_name)
                    keep_msg = "keep %s (plugin '%s')" % (full_name, plugin.plugin_name)
                    count = self.msg_count.get(plugin.plugin_name, 0)
                    if count < self.msg_limit:
                        self.info(keep_msg)
                    self.msg_count[plugin.plugin_name] = count + 1
                    if count == self.msg_limit:
                        self.info(
                            "... 'keep' msg limit exceeded for '%s'."
                            % plugin.plugin_name
                        )
                    return True, "module is imported"  # ok
                # plugin wants to drop this
                self.ignored_modules.add(full_name)
                ignore_msg = "drop %s (plugin '%s')" % (full_name, plugin.plugin_name)
                self.info(ignore_msg)
                return False, "dropped by plugin " + plugin.plugin_name

        if full_name == "cv2":
            return True, "needed by OpenCV"

        if str(full_name.getTopLevelPackageName()).startswith("pywin"):
            return True, "needed by pywin32"

        checklist = get_checklist(full_name)
        for m in self.import_calls:  # loop thru the called items
            if m in checklist:
                return True, "module is hinted to"  # ok

        if check_dependents(full_name, self.import_files) is True:
            return True, "parent of recursed-to module"

        # next we ask if implicit imports knows our candidate
        if self.implicit_imports_plugin is None:  # the plugin is not yet loaded
            for plugin in getActivePlugins():
                if plugin.plugin_name == "implicit-imports":
                    self.implicit_imports_plugin = plugin
                    break
            if self.implicit_imports_plugin is None:
                sys.exit("could not find 'implicit-imports' plugin")

        # ask the 'implicit-imports' plugin whether it knows this guy
        if package is not None:
            try:
                import_set = self.implicit_imports_plugin.getImportsByFullname(
                    package, package_dir
                )
            except TypeError:
                sys.exit(
                    "versions of hinted-mods.py and ImplicitImports.py are incompatible"
                )

            import_list0 = [item[0] for item in import_set]  # only the names
            if full_name in import_list0:  # found!
                for item in import_list0:  # store everything in that list
                    self.implicit_imports.add(item)
                return True, "module is an implicit import"  # ok

        # not known by anyone: kick it out!
        self.info(drop_msg(full_name, package))  # issue ignore message
        # faster decision next time
        self.ignored_modules.add(full_name)
        return False, "module is not used"

    def getImplicitImports(self, module):
        """Declare all matplotlib.backends modules as implicit imports."""
        full_name = module.getFullName()
        if full_name == "__main__":  # need to make sure that backends are used
            for f in Options.options.recurse_modules:
                if f.startswith("matplotlib.backends"):
                    yield f

    def onStandaloneDistributionFinished(self, dist_dir):
        """ Only used to output the compilation time."""
        self.timer.end()
        t = int(round(self.timer.getDelta()))
        if t > 240:
            unit = "minutes"
            if t >= 600:
                t = int(round(t / 60.0))
            else:
                t = round(t / 60, 1)
        else:
            unit = "seconds"

        self.info("Compiled '%s' in %g %s." % (sys.argv[-1], t, unit))
