import gi
import sys

import math

gi.require_version('Gtk', '3.0')
import time, datetime
import os
import threading
from gi.repository import Gtk, GObject

from cardvault import util, application
from mtgsdk import Card, MtgException

from cardvault.search import SearchHandlers
from cardvault.library import LibraryHandlers
from cardvault.wants import WantsHandlers


class Handlers(SearchHandlers, LibraryHandlers, WantsHandlers):
    def __init__(self, app: 'application.Application'):
        """Initialize handlers for UI signals"""
        self.app = app
        # Token to cancel a running download
        self.cancel_token = False

        # Call constructor of view handlers classes
        SearchHandlers.__init__(self, app)
        LibraryHandlers.__init__(self, app)
        WantsHandlers.__init__(self, app)

    # --------------------------------- Main Window Handlers ----------------------------------------------

    def do_save_library(self, item):
        self.app.save_data()

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

    def export_cell_toggled(self, widget, pos):
        model = self.app.ui.get_object("export_treestore")
        iter = model.get_iter(pos)
        model.set_value(iter, 0, not widget.get_active())

        if len(pos.split(":")) > 1:
            # A child node has been clicked
            pass

    def do_export_json(self, item):
        """
        Export user data to file
        Called By: Export menu item
        """
        # dialog = self.app.ui.get_object("export_dialog")
        # dialog.set_transient_for(self.app.ui.get_object("mainWindow"))
        #
        # store = self.app.ui.get_object("export_treestore") # type: Gtk.TreeStore
        # store.clear()
        # store.append(None, [True, False, "Library"])
        # store.append(None, [True, False, "Decks"])
        # store.append(None, [True, False, "Wants Lists"])
        #
        # lib_iter = store.get_iter_first()
        # deck_iter = store.iter_next(lib_iter)
        # wants_iter = store.iter_next(deck_iter)
        #
        # store.append(lib_iter, [True, True, "Untagged Cards"])
        # for tag in self.app.tags.keys():
        #     store.append(lib_iter, [True, True, tag])
        #
        # for name in self.app.wants.keys():
        #     store.append(wants_iter, [True, True, name])
        #
        # self.app.ui.get_object("export_sel_tree").expand_all()
        #
        # response = dialog.run()
        # dialog.hide()
        #
        # if not response == Gtk.ResponseType.OK:
        #     return

        # TODO Read treemodel to select witch parts to export

        dialog = Gtk.FileChooserDialog("Export Library", self.app.ui.get_object("mainWindow"),
                                       Gtk.FileChooserAction.SAVE,
                                       (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                        Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        dialog.set_current_name("mtg_export-" + datetime.datetime.now().strftime("%Y-%m-%d") + ".json")
        dialog.set_current_folder(os.path.expanduser("~"))
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            # prepare export file
            file = {"library": self.app.library, "tags": self.app.tags, "wants": self.app.wants}
            util.export_json(dialog.get_filename(), file)
            self.app.push_status("Library exported")

        dialog.destroy()

    def do_import_library(self, item):
        """Called by menu item import library"""
        # Show file picker dialog for import
        dialog = Gtk.FileChooserDialog("Import Library", self.app.ui.get_object("mainWindow"),
                                       Gtk.FileChooserAction.OPEN,
                                       (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                        Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        dialog.set_current_folder(os.path.expanduser("~"))
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            override_question = self.app.show_dialog_yn(
                "Import Library", "Importing a library will override your current library.\nProceed?")
            if override_question == Gtk.ResponseType.YES:
                imports = util.import_library(dialog.get_filename())
                self.app.library = imports[0]
                self.app.tags = imports[1]
                self.app.wants = imports[2]
                self.app.db_override_user_data()
                self.app.current_page.emit('show')
        dialog.destroy()

    def do_card_data_user(self, menu_item):
        """
        Handler for Clear User Data menu item.
        """
        response = self.app.show_dialog_yn("Deleting All User Data", "You are about to delete all data in the "
                                                                     "library.\nThis can not be undone.\nProceed?")
        if response == Gtk.ResponseType.YES:
            util.log("Deleting all local card data", util.LogLevel.Info)
            self.app.db_delete_user_data()
            util.log("Done", util.LogLevel.Info)
            self.app.push_status("Library deleted")

    def do_card_data_card(self, item):
        """Handler for Clear Card Data menu item"""
        response = self.app.show_dialog_yn("Deleting All Card Data", "You are about to delete all local card data.\n"
                                                                     "Further searches will use the internet to search "
                                                                     "for cards.\nProceed?")
        if response == Gtk.ResponseType.YES:
            util.log("Deleting all library data", util.LogLevel.Info)
            self.app.db_delete_card_data()
            util.log("Done", util.LogLevel.Info)
            self.app.push_status("Local card data deleted. Switching to online mode.")

    def prefs_open(self, item):
        """
        Handler for open preferences menu item
        Called By: prefs_item menu item
        """
        self.app.show_preferences_dialog()

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

            self.app.config["last_viewed"] = new_page.get_name().lower()
            self.app.save_config()

    def do_delete_event(self, arg1, arg2):
        if self.app.unsaved_changes():
            response = self.app.show_dialog_ync("Unsaved Changes",
                                                "You have unsaved changes in your library. "
                                                "Save before exiting?")
            if response == Gtk.ResponseType.YES:
                self.app.save_data()
                return False
            elif response == Gtk.ResponseType.CANCEL:
                return True

    def do_cancel_download(self, item: Gtk.MenuItem):
        """The cancel button was pressed, set cancel_token to stop download thread"""
        self.cancel_token = True
        # Delete Dialog
        self.app.ui.get_object("loadDataDialog").hide()
        self.app.push_status("Download canceled")
        util.log("Download canceled by user", util.LogLevel.Info)

    def download_canceled(self):
        """The download thread was canceled and finished executing"""
        self.cancel_token = False
        util.log("Download thread ended", util.LogLevel.Info)

    def download_failed(self, err: MtgException):
        # Delete Dialog
        self.app.ui.get_object("loadDataDialog").hide()
        self.app.push_status("Download canceled")
        self.app.show_message("Download Failed", str(err))

    def download_finished(self):
        """Download thread finished without errors"""
        self.cancel_token = False
        self.app.set_online(False)
        self.app.ui.get_object("loadDataDialog").hide()
        self.app.push_status("Card data downloaded")
        util.log("Card data download finished", util.LogLevel.Info)

    def do_download_card_data(self, item: Gtk.MenuItem):
        """Download button was pressed in the menu bar. Starts a thread to load data from the internet"""
        info_string = "Start downloading card information from the internet?\n" \
                      "You can cancel the download at any point."
        response = self.app.show_dialog_yn("Download Card Data", info_string)
        if response == Gtk.ResponseType.NO:
            return
        # Launch download info dialog
        dl_dialog = self.app.ui.get_object("loadDataDialog")
        dl_dialog.set_transient_for(self.app.ui.get_object("mainWindow"))
        dl_dialog.show()

        # Hide Progress UI until download started
        self.app.ui.get_object("dl_progress_bar").set_visible(False)
        self.app.ui.get_object("dl_progress_label").set_visible(False)

        # Create and start the download in a separate thread so it will not block the UI
        thread = threading.Thread(target=self.load_thread)
        thread.daemon = True
        thread.start()
        util.log("Attempt downloading all cards. This may take a while...", util.LogLevel.Info)

    def load_thread(self):
        """Worker thread to download info using the mtgsdk"""

        # Gatherer uses rate limit on Card.all()
        # Takes ~10 minutes to download all cards
        # all = self.load_thread_gatherer()

        # Download from mtgjson.com
        GObject.idle_add(self.load_show_insert_ui, "Downloading...")

        # Waiting in case a canceled thread is still running.
        while self.cancel_token:
            continue

        util.log("Starting download", util.LogLevel.Info)
        s = time.time()
        all_json = util.net_all_cards_mtgjson()
        e = time.time()
        util.log("Finished in {}s".format(round(e - s, 3)), util.LogLevel.Info)

        if self.cancel_token:
            GObject.idle_add(self.download_canceled)
            return

        self.app.db_delete_card_data()

        GObject.idle_add(self.load_show_insert_ui, "Saving data to disk...")
        util.log("Saving to sqlite", util.LogLevel.Info)
        s = time.time()
        GObject.idle_add(self.app.db.db_insert_data_card, all_json)
        e = time.time()
        util.log("Finished in {}s".format(round(e - s, 3)), util.LogLevel.Info)

        self.download_finished()

    def load_thread_gatherer(self):
        all = []
        all_num = util.get_all_cards_num()
        all_pages = int(math.ceil(all_num / 100))

        # Paging for ui control between downloads
        for i in range(all_pages):
            req_start = time.time()
            try:
                new_cards = Card.where(page=i).where(pageSize=100).all()
            except MtgException as err:
                util.log(str(err), util.LogLevel.Error)
                return
            all = all + new_cards
            req_end = time.time()

            # Check if the action was canceled during download
            if self.cancel_token:
                GObject.idle_add(self.download_canceled)
                return

            # Activate download UI
            self.app.ui.get_object("dl_spinner").set_visible(False)
            self.app.ui.get_object("dl_progress_bar").set_visible(True)
            self.app.ui.get_object("dl_progress_label").set_visible(True)
            passed = str(round(req_end - req_start, 3))
            GObject.idle_add(self.load_update_ui, all, all_num, passed)

        return all

    def load_update_ui(self, current_list: list, max_cards: int, time_passed: str):
        """Called from withing the worker thread. Updates the download dialog with infos."""
        # Get info widgets
        info_label = self.app.ui.get_object("dl_info_label")
        progress_label = self.app.ui.get_object("dl_progress_label")
        bar = self.app.ui.get_object("dl_progress_bar")
        # Compute numbers for display
        size_human = util.sizeof_fmt(sys.getsizeof(current_list))
        size_bytes = sys.getsizeof(current_list)
        percent = len(current_list) / max_cards
        # Update UI
        info_label.set_text("Downloading Cards...")
        progress_label.set_text("{:.1%} ({})".format(percent, size_human))
        bar.set_fraction(percent)
        util.log("Downloading: {:.1%} | {} Bytes | {}s".format(percent, size_bytes, time_passed), util.LogLevel.Info)

    def load_show_insert_ui(self, info: str):
        """Called from worker thread after download finished. Sets UI to display the passed string"""
        self.app.ui.get_object("dl_info_label").set_text(info)
        self.app.ui.get_object("dl_spinner").set_visible(True)
        self.app.ui.get_object("dl_progress_bar").set_visible(False)
        self.app.ui.get_object("dl_progress_label").set_visible(False)
