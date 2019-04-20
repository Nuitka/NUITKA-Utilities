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
""" Details see below in class definition.
"""
import os
import subprocess
from logging import info
from nuitka import Options
from nuitka.plugins.PluginBase import UserPluginBase
from nuitka.utils.Timing import StopWatch


class MyExit(UserPluginBase):
    """ User plugin supporting post-processing in standalone mode.

    Notes:
        Upon initialization, this plugin establishes a few options.
        Among these are enabling or disabling standard plugins.

        Compilation post-processing can be either
        (a) option "upx" for invoking UPX compression, or
        (b) option "onefile" for creating a distribution file in OneFile format, or
        (c) TODO: option "onedir" for creating a distribution file in OneDir format.

        The options for the standard plugins tk-plugin (code "tk"), numpy-plugin
        ("np") and qt-plugins ("qt") can also be added as options to this plugin.
        This will enable the respective plugin. If the code is prefixed with "no",
        then the plugin will be disabled and certain modules will not be recursed
        to. For example:
        - "tk" will generate "--enable-plugin=tk-plugin"
        - "notk" will generate "--disable-plugin=tk-plugin" and
          "--recurse-not-to=PIL.ImageTk".
    """

    plugin_name = __file__

    def __init__(self):

        options = Options.options
        self.sep_line1 = "=" * 80
        self.sep_line2 = "-" * 80

        self.excludes = []

        info(self.sep_line1)

        if not Options.isStandaloneMode():
            info(" can only run in standalone mode")
            info(self.sep_line1)
            raise SystemExit()

        # start a timer
        self.timer = StopWatch()
        self.timer.start()

        # get the list of options
        self.myoptions = self.getPluginOptions()
        self.tk = self.getPluginOptionBool("tk", None)
        self.qt = self.getPluginOptionBool("qt", None)
        self.numpy = self.getPluginOptionBool("np", None)

        # check for post processors
        self.onefile = 1 if self.getPluginOptionBool("onefile", False) else 0
        self.onedir = 1 if self.getPluginOptionBool("onedir", False) else 0
        self.upx = 1 if self.getPluginOptionBool("upx", False) else 0

        if self.onefile + self.onedir + self.upx > 1:
            raise SystemExit("only 1 post-processor can be chosen")

        # announce how we will execute
        msg = " '%s' established the following configuration" % self.plugin_name
        info(msg)
        info(self.sep_line2)

        if self.numpy is False:
            options.recurse_not_modules.append("numpy")
            info(" --recurse-not-to=numpy")
            options.plugins_disabled.append("numpy")
            info(" --disable-plugin=numpy")
        elif self.numpy is True:
            options.plugins_enabled.append("numpy")
            info(" --enable-plugin=numpy")

        if self.qt is False:
            options.recurse_not_modules.append("PIL.ImageQt")
            info(" --recurse-not-to=PIL.ImageQt")
            options.plugins_disabled.append("qt-plugins")
            info(" --disable-plugin=qt-plugins")
        elif self.qt is True:
            options.plugins_enabled.append("qt-plugins")
            info(" --enable-plugin=qt-plugins")

        if self.tk is False:
            options.recurse_not_modules.append("PIL.ImageTk")
            info(" --recurse-not-to=PIL.ImageTk")
            options.plugins_disabled.append("tk-inter")
            info(" --disable-plugin=tk-inter")
        elif self.tk is True:
            options.plugins_enabled.append("tk-inter")
            info(" --enable-plugin=tk-inter")

        info(self.sep_line2)

    def removeDllDependencies(self, dll_filename, dll_filenames):
        if self.tk is False:
            basename = os.path.basename(dll_filename)
            if basename.startswith(("tk", "tcl")):
                info(" exluding " + basename)
                self.excludes.append(basename)
            yield ()
        if "qt" in dll_filename.lower():
            print(dll_filename)
        yield ()

    def onStandaloneDistributionFinished(self, dist_dir):
        """ Post-process the distribution folder.

        Notes:
            Except just exiting, other options are available:
            * Create an installation file with the OneFile option
            * TODO: create a normal installation file
            * Compress the folder using UPX

        Args:
            dist_dir: name of the distribution folder
        Returns:
            None
        """
        self.timer.end()
        t = int(round(self.timer.delta()))
        info(" Compilation ended in %i seconds." % t)

        for f in self.excludes:
            fname = os.path.join(dist_dir, f)
            if os.path.exists(fname):
                os.remove(fname)

        if self.onefile:
            info(" Now starting OneFile maker")
            info(self.sep_line1)
            subprocess.call("python onefile-maker.py " + dist_dir)
            return None

        if self.onedir:
            info(" Now starting OneDir maker")
            info(self.sep_line1)
            subprocess.call("python onedir-maker.py " + dist_dir)
            return None

        if self.upx:
            info(" Now starting UPX packer")
            info(self.sep_line1)
            subprocess.call("python upx-packer.py " + dist_dir)
            return None

        info(self.sep_line1)
