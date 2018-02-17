import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from cv_engine import engine
from cv_engine.util import Utilities

from cv_gtk3.main_window import MainWindowFunctions
from cv_gtk3.setting import GUISettings


class CardvaultGTK(MainWindowFunctions):
    """
    Main UI class for the GTK interface
    """
    def __init__(self):
        # Start engine (without config file)
        self.engine = engine.CardvaultEngine()

        # Load Glade files
        glade_files = ['mainwindow.glade', 'overlays.glade', 'search.glade', 'dialogs.glade']
        self.ui = Gtk.Builder()
        for file in glade_files:
            self.ui.add_from_file(Utilities.expand_file_path(__file__, ['gui', file]))

        # Set pages for the ui to use
        GUISettings.pages = {
            "search": self.ui.get_object("searchView"),
        }

        # Call constructor of superclasses
        MainWindowFunctions.__init__(self, self.ui)

        self.ui.get_object('mainWindow').connect('delete-event', Gtk.main_quit)
        self.ui.get_object('mainWindow').show_all()
        self.hide_initial_widgets()

        self.switch_page('search')

if __name__ == '__main__':
    CardvaultGTK()
    Gtk.main()

