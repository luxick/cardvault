import gi
gi.require_version('Gtk', '3.0')
import datetime
import os
from gi.repository import Gtk

from cardvault import util
from cardvault import application

from search import SearchHandlers
from library import LibraryHandlers
from wants import WantsHandlers


class Handlers(SearchHandlers, LibraryHandlers, WantsHandlers):
    def __init__(self, app: 'application.Application'):
        """Initialize handlers for UI signals"""
        self.app = app

        # Call constructor of view handlers classes
        SearchHandlers.__init__(self, app)
        LibraryHandlers.__init__(self, app)
        WantsHandlers.__init__(self, app)

    # --------------------------------- Main Window Handlers ----------------------------------------------

    def do_save_library(self, item):
        self.app.save_library()

    def do_export_library(self, item):
        dialog = Gtk.FileChooserDialog("Export Library", self.app.ui.get_object("mainWindow"),
                                       Gtk.FileChooserAction.SAVE,
                                       (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                        Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        dialog.set_current_name("mtg_export-" + datetime.datetime.now().strftime("%Y-%m-%d"))
        dialog.set_current_folder(os.path.expanduser("~"))
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            # prepare export file
            file = {"library": self.app.library, "tags": self.app.tags, "wants": self.app.wants}
            util.export_library(dialog.get_filename(), file)
            self.app.push_status("Library exported")

        dialog.destroy()

    def do_import_library(self, item):
        # Show file picker dialog for import
        dialog = Gtk.FileChooserDialog("Import Library", self.app.ui.get_object("mainWindow"),
                                       Gtk.FileChooserAction.OPEN,
                                       (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                        Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        dialog.set_current_folder(os.path.expanduser("~"))
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            # Show confirmation message
            override_question = self.app.show_question_dialog("Import Library",
                                                              "Importing a library will override your current library. "
                                                              "Proceed?")
            if override_question == Gtk.ResponseType.YES:
                imports = util.import_library(dialog.get_filename())
                self.app.library = imports[0]
                self.app.tags = imports[1]
                self.app.wants = imports[2]
                # Cause current page to reload with imported data
                self.app.current_page.emit('show')
                self.app.unsaved_changes = True
                self.app.push_status("Library imported")
        dialog.destroy()

    def on_view_changed(self, item):
        if item.get_active():
            container = self.app.ui.get_object("contentPage")
            new_page = self.app.pages[item.get_name()]
            if self.app.current_page:
                container.remove(self.app.current_page)
            self.app.current_page = new_page
            container.pack_start(self.app.current_page, True, True, 0)
            container.show_all()
            self.app.current_page.emit('show')

            app_title = new_page.get_name() + " - " + util.APPLICATION_TITLE
            self.app.ui.get_object("mainWindow").set_title(app_title)

    def do_delete_event(self, arg1, arg2):
        if self.app.unsaved_changes:
            response = self.app.show_question_dialog("Unsaved Changes", "You have unsaved changes in your library. "
                                                                        "Save before exiting?")
            if response == Gtk.ResponseType.YES:
                self.app.save_library()
                return False
            elif response == Gtk.ResponseType.CANCEL:
                return True
