import gi
import os

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from cv_engine import engine

from cv_gtk3.main_window import MainWindowFunctions
from cv_gtk3.setting import GUISettings
from cv_gtk3.signal_handlers import handlers


class CardvaultGTK(MainWindowFunctions):
    """ Main UI class for the GTK interface """
    def __init__(self):
        # Start engine (without config file)
        self.engine = engine.CardvaultEngine()
        # Set Glade file location
        GUISettings.glade_file_path = os.path.join(os.path.dirname(__file__), 'gui')
        # Load Glade files
        glade_files = ['mainwindow.glade', 'search.glade', 'overlays.glade']
        self.ui = Gtk.Builder()
        for file in glade_files:
            self.ui.add_from_file(os.path.join(GUISettings.glade_file_path, file))
        # Set pages for the ui to use
        GUISettings.pages = {
            "search": self.ui.get_object("searchView"),
        }
        # Call constructor of superclasses
        MainWindowFunctions.__init__(self, self.ui)
        # Create Signal handlers and connect them to the UI
        self.handlers = handlers.Handlers(self)
        self.ui.connect_signals(self.handlers)
        # Initialize starting view
        self.ui.get_object('mainWindow').show_all()
        self.hide_initial_widgets()
        self.switch_page('search')

if __name__ == '__main__':
    CardvaultGTK()
    Gtk.main()

