import os

import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from cv_core import engine, util

from cv_gtk3.main_window import MainWindowFunctions
from cv_gtk3.setting import GUISettings
from cv_gtk3.signal_handlers import handlers
from cv_gtk3.gtk_util import GTKUtilities


class CardvaultGTK(MainWindowFunctions):
    """ Main UI class for the GTK interface """
    def __init__(self):
        # Start engine (without config file)
        self.engine = engine.CardvaultEngine()
        # Load Glade files
        glade_files = ['mainwindow.glade', 'search.glade', 'overlays.glade']
        self.ui = Gtk.Builder()
        for file in glade_files:
            self.ui.add_from_string(GTKUtilities.load_ui_resource(file))
        # Set pages for the ui to use
        GUISettings.pages = {
            "search": self.ui.get_object("searchView"),
        }
        # Verify that cache directories exist
        if not os.path.isdir(util.CoreConfig.cache_path):
            os.mkdir(util.CoreConfig.cache_path)
        if not os.path.isdir(util.CoreConfig.icon_cache_path):
            os.mkdir(util.CoreConfig.icon_cache_path)
        # Load single mana icons
        GTKUtilities.mana_icons = GTKUtilities.load_icon_cache(os.path.join(GTKUtilities.resources_path, 'mana'))
        # Load the the pre constructed icon cache
        GTKUtilities.precon_icon_cache = GTKUtilities.load_icon_cache(util.CoreConfig.icon_cache_path)
        # Call constructor of superclasses
        MainWindowFunctions.__init__(self, self.ui)
        # Create Signal handlers and connect them to the UI
        self.handlers = handlers.Handlers(self)
        self.ui.connect_signals(self.handlers)
        # Initialize starting view
        self.ui.get_object('mainWindow').show_all()
        self.hide_initial_widgets()
        self.switch_page('search')


def main():
    CardvaultGTK()
    Gtk.main()

if __name__ == '__main__':
    main()


