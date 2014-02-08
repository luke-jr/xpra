# This file is part of Xpra.
# Copyright (C) 2008, 2009 Nathaniel Smith <njs@pobox.com>
# Copyright (C) 2012-2014 Antoine Martin <antoine@devloop.org.uk>
# Xpra is released under the terms of the GNU GPL v2, or, at your option, any
# later version. See the file COPYING for details.

import os
import sys
import logging
import weakref
# This module is used by non-GUI programs and thus must not import gtk.

logging.basicConfig(format="%(asctime)s %(message)s")
logging.root.setLevel(logging.INFO)

#so we can keep a reference to all the loggers in use
#we may have multiple loggers for the same key, so use a dict
#but we don't want to prevent garbage collection so use a list of weakrefs
all_loggers = dict()
def add_logger(categories, logger):
    global all_loggers
    categories = list(categories)
    categories.append("all")
    for cat in categories:
        all_loggers.setdefault(cat, []).append(weakref.ref(logger))

def get_all_loggers():
    global all_loggers
    a = set()
    for loggers in all_loggers.values():
        for l in loggers:
            #weakref:
            v = l()
            if v:
                a.add(v)
    return a

debug_enabled_categories = set()
debug_disabled_categories = set()
def add_debug_category(cat):
    remove_disabled_category(cat)
    debug_enabled_categories.add(cat)

def remove_debug_category(cat):
    if cat in debug_enabled_categories:
        debug_enabled_categories.remove(cat)

def add_disabled_category(cat):
    remove_debug_category(cat)
    debug_disabled_categories.add(cat)

def remove_disabled_category(cat):
    if cat in debug_disabled_categories:
        debug_disabled_categories.remove(cat)


def enable_debug_for(cat):
    loggers = all_loggers.get(cat)
    if loggers:
        for l in loggers:
            #weakref:
            v = l()
            if v:
                v.enable_debug()

def disable_debug_for(cat):
    loggers = all_loggers.get(cat)
    if loggers:
        for l in loggers:
            #weakref:
            v = l()
            if v:
                v.disable_debug()


KNOWN_FILTERS = ["auth", "cairo", "client", "clipboard", "codec", "loader", "video",
                 "csc", "cuda", "cython", "opencl", "swscale", "dbus",
                 "decoder", "avcodec", "vpx", "nvenc", "proxy",
                 "x264", "gobject", "gtk", "main", "util",
                 "window", "icon", "info", "launcher", "mdns",
                 "mmap", "net", "protocol", "notify",
                 "opengl",
                 "osx", "win32",
                 "paint", "platform", "import",
                 "posix", "qt", "keyboard", "server",
                 "shadow",
                 "x11", "bindings", "core", "randr", "ximage", "focus", "tray", "xor"]


# A wrapper around 'logging' with some convenience stuff.  In particular:
#    -- You initialize it with a list of categories
#       If unset, the default logging target is set to the name of the module where
#       Logger() was called.
#    -- Any of the categories can enable debug logging if the environment
#       variable 'XPRA_${CATEGORY}_DEBUG' is set to "1"
#    -- We also keep a list of debug_categories, so these can get enabled
#       programatically too
#    -- We keep track of which loggers are associated with each category,
#       so we can enable/disable debug logging by category
#    -- You can pass exc_info=True to any method, and sys.exc_info() will be
#       substituted.
#    -- __call__ is an alias for debug
#    -- we bypass the logging system unless debugging is enabled for the logger,
#       which is much faster than relying on the python logging code

class Logger(object):
    def __init__(self, *categories):
        self.categories = list(categories)
        caller = sys._getframe(1).f_globals["__name__"]
        if caller=="__main__":
            caller = ".".join(categories)
        else:
            self.categories.append(caller)
        self.logger = logging.getLogger(caller)
        self.logger.setLevel(logging.INFO)
        disabled = False
        enabled = False
        for cat in self.categories:
            if cat in debug_disabled_categories:
                disabled = True
            if "all" in debug_enabled_categories or cat in debug_enabled_categories or os.environ.get("XPRA_%s_DEBUG" % cat.upper(), "0")=="1":
                enabled = True
        if enabled and not disabled:
            self.enable_debug()
        else:
            self.disable_debug()
        #ready, keep track of it:
        add_logger(self.categories, self)

    def __str__(self):
        return "Logger(%s)" % ", ".join(self.categories)

    def is_debug_enabled(self):
        return self.logger.isEnabledFor(logging.DEBUG)

    def enable_debug(self):
        self.logger.setLevel(logging.DEBUG)

    def disable_debug(self):
        self.logger.setLevel(logging.INFO)


    def log(self, level, msg, *args, **kwargs):
        if kwargs.get("exc_info") is True:
            kwargs["exc_info"] = sys.exc_info()
        self.logger.log(level, msg, *args, **kwargs)

    def __call__(self, msg, *args, **kwargs):
        self.log(logging.DEBUG, msg, *args, **kwargs)
    def debug(self, msg, *args, **kwargs):
        self.log(logging.DEBUG, msg, *args, **kwargs)
    def info(self, msg, *args, **kwargs):
        self.log(logging.INFO, msg, *args, **kwargs)
    def warn(self, msg, *args, **kwargs):
        self.log(logging.WARN, msg, *args, **kwargs)
    def error(self, msg, *args, **kwargs):
        self.log(logging.ERROR, msg, *args, **kwargs)
