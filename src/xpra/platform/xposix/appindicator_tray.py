# This file is part of Xpra.
# Copyright (C) 2010 Nathaniel Smith <njs@pobox.com>
# Copyright (C) 2011-2017 Antoine Martin <antoine@xpra.org>
# Xpra is released under the terms of the GNU GPL v2, or, at your option, any
# later version. See the file COPYING for details.

# Ubuntu re-invents the wheel, and it's a broken one

import os

from xpra.util import envbool
from xpra.os_util import is_unity, monotonic_time, getUbuntuVersion, PYTHON2, PYTHON3
from xpra.client.tray_base import TrayBase
from xpra.platform.paths import get_icon_dir, get_icon_filename
from xpra.log import Logger

log = Logger("tray", "posix")

DELETE_TEMP_FILE = envbool("XPRA_APPINDICATOR_DELETE_TEMP_FILE", True)


_appindicator = False
def get_appindicator():
    global _appindicator
    if _appindicator is False:
        try:
            import sys
            if "gi" in sys.modules or PYTHON3:
                if getUbuntuVersion()>=(18,4) and is_unity():
                    #causes segfaults just by importing it
                    #shambolic
                    pass
                else:
                    import gi
                    gi.require_version('AppIndicator3', '0.1')
                    from gi.repository import AppIndicator3 #@UnresolvedImport @Reimport
                    _appindicator = AppIndicator3
            else:
                import appindicator                     #@UnresolvedImport
                _appindicator = appindicator
        except ImportError:
            _appindicator = None
    return _appindicator

def get_application_category(appindicator):
    v = getattr(appindicator, "CATEGORY_APPLICATION_STATUS", None)
    if v is None:
        cat = getattr(appindicator, "IndicatorCategory", None)
        if cat:
            v = getattr(cat, "APPLICATION_STATUS", None)
    return v

def can_use_appindicator():
    return get_appindicator() is not None


class AppindicatorTray(TrayBase):

    def __init__(self, *args, **kwargs):
        TrayBase.__init__(self, *args, **kwargs)
        filename = get_icon_filename(self.default_icon_filename)
        self.appindicator = get_appindicator()
        self._has_icon = False
        assert self.appindicator, "appindicator is not available!"
        category = get_application_category(self.appindicator)
        assert category is not None, "appindicator category is not available!"
        if PYTHON2:
            self.tray_widget = self.appindicator.Indicator(self.tooltip, filename, category)
        else:
            self.tray_widget = self.appindicator.Indicator()
            self.tray_widget.set_property("label", self.tooltip)
            self.tray_widget.set_property("category", category)
        if hasattr(self.tray_widget, "set_icon_theme_path"):
            self.tray_widget.set_icon_theme_path(get_icon_dir())
        self.tray_widget.set_attention_icon("xpra.png")
        if filename:
            self.set_icon_from_file(filename)
        if not self._has_icon:
            self.tray_widget.set_label("Xpra")
        if self.menu:
            self.tray_widget.set_menu(self.menu)

    def hide(self, *_args):
        self.tray_widget.set_status(self.appindicator.STATUS_PASSIVE)

    def show(self, *_args):
        self.tray_widget.set_status(self.appindicator.STATUS_ACTIVE)

    def set_blinking(self, on):
        #"I'm Afraid I Can't Do That"
        pass

    def set_tooltip(self, text=None):
        #we only use this if we haven't got an icon
        #as with appindicator this creates a large text label
        #next to where the icon is/should be
        if not self._has_icon:
            self.tray_widget.set_label(text or "Xpra")

    def set_icon_from_data(self, pixels, has_alpha, w, h, rowstride, _options=None):
        #use a temporary file (yuk)
        from xpra.gtk_common.gtk_util import COLORSPACE_RGB, pixbuf_new_from_data
        import tempfile
        try:
            filename = tempfile.mkstemp(suffix=".png")[1]
            log("set_icon_from_data%s using temporary file %s",
                ("%s pixels" % len(pixels), has_alpha, w, h, rowstride), filename)
            tray_icon = pixbuf_new_from_data(pixels, COLORSPACE_RGB, has_alpha, 8, w, h, rowstride)
            tray_icon.save(filename, "png")
            self.do_set_icon_from_file(filename)
        finally:
            if DELETE_TEMP_FILE:
                os.unlink(filename)

    def do_set_icon_from_file(self, filename):
        if not hasattr(self.tray_widget, "set_icon_theme_path"):
            self.tray_widget.set_icon(filename)
            self._has_icon = True
            return
        head, icon_name = os.path.split(filename)
        if head:
            log("do_set_icon_from_file(%s) setting icon theme path=%s", filename, head)
            self.tray_widget.set_icon_theme_path(head)
        #remove extension (wtf?)
        noext = os.path.splitext(icon_name)[0]
        log("do_set_icon_from_file(%s) setting icon=%s", filename, noext)
        self.tray_widget.set_icon(noext)
        self._has_icon = True
        self.icon_timestamp = monotonic_time()


def main():
    log.enable_debug()
    appindicator = get_appindicator()
    if not appindicator:
        log("appindicator not available")
        return

    log("main: appindicator=%s", appindicator)
    if not can_use_appindicator():
        log("appindicator may not be shown...")

    from xpra.gtk_common.gobject_compat import import_glib, import_gtk
    glib = import_glib()
    gtk = import_gtk()

    menu = gtk.Menu()
    item = gtk.MenuItem("Some Menu Item Here")
    menu.append(item)
    menu.show_all()
    a = AppindicatorTray(None, None, menu, "test", "xpra.png", None, None, None, gtk.main_quit)
    a.show()
    glib.timeout_add(1000*10, gtk.main_quit)
    gtk.main()


if __name__ == "__main__":
    main()
