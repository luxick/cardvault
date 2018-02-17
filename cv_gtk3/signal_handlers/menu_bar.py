import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


class MenuBarHandlers:
    """
    Class for handling signals from the menu bar
    """
    def __init__(self, app):
        """
        Constructor
        :param app: Reference to a CardvaultGTK object
        """
        self.app = app

    def do_save_library(self, menu_item):
        pass

    def do_export_library(self, menu_item):
        pass

    def do_import_library(self, menu_item):
        pass

    def do_delete_user_library(self, menu_item):
        pass

    def do_delete_card_data(self, menu_item):
        pass

    def do_change_view(self, menu_item):
        pass

    def do_prefs_open(self, manu_item):
        pass

    @staticmethod
    def do_delete_event(*args):
        """
        Signal will be sent when app should close
        :param args: Arguments to the delete event
        """
        Gtk.main_quit()