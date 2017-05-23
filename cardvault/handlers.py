import gi
gi.require_version('Gtk', '3.0')
import datetime
import os
from gi.repository import Gtk
from typing import Type

from cardvault import lib_funct
from cardvault import search_funct
from cardvault import wants_funct
from cardvault import util
from cardvault import application


class Handlers:
    def __init__(self, app):
        self.app = Type[application.Application]
        self.app = app

    # ---------------------------------Main Window----------------------------------------------

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
            file = {"library": self.app.library, "tags": self.app.tags}
            util.export_library(dialog.get_filename(), file)

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
                # Cause current page to reload with imported data
                self.app.current_page.emit('show')
                self.app.unsaved_changes = True
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

    # ---------------------------------Search----------------------------------------------

    def do_search_cards(self, sender):
        search_term = self.app.ui.get_object("searchEntry").get_text()

        filters = search_funct.get_filters(self.app)

        results = search_funct.search_cards(search_term, filters)

        card_list = self.app.ui.get_object("searchResults").get_child()
        card_list.update(results, colorize=True)

        self.app.ui.get_object("searchOverlay").set_visible(False)

    def do_clear_mana_filter(self, mana_filter_grid):
        for toggle_button in mana_filter_grid.get_children():
            if isinstance(toggle_button, Gtk.ToggleButton):
                toggle_button.set_active(False)

    def do_clear_set_filter(self, entry, icon_pos, button):
        entry.set_text("")

    def do_add_clicked(self, button):
        card_view = self.app.ui.get_object("searchResults").get_child()
        (model, pathlist) = card_view.selection.get_selected_rows()

        for path in pathlist:
            tree_iter = model.get_iter(path)
            card_id = model.get_value(tree_iter, 0)
            card = card_view.lib[card_id]
            self.app.add_card_to_lib(card)
        search_funct.reload_serach_view(self.app)
        self.app.ui.get_object("searchEntry").grab_focus()

    # ---------------------------------Library----------------------------------------------

    def do_reload_library(self, view):
        lib_funct.reload_library(self.app)

    def do_tag_entry_changed(self, entry):
        input_valid = entry.get_text() and entry.get_text() != ""
        self.app.ui.get_object("newTagButton").set_sensitive(input_valid)

    def do_new_tag_clicked(self, entry):
        lib_funct.add_new_tag(entry.get_text(), self.app)
        entry.set_text("")

    def do_show_all_clicked(self, button):
        # Clear selection in tag list
        self.app.ui.get_object("tagTree").get_selection().unselect_all()
        self.app.current_lib_tag = "All"
        lib_funct.reload_library(self.app)

    def do_show_untagged_clicked(self, button):
        # Clear selection in tag list
        self.app.ui.get_object("tagTree").get_selection().unselect_all()
        self.app.current_lib_tag = "Untagged"
        lib_funct.reload_library(self.app, "Untagged")

    def do_tag_cards(self, entry):
        card_view = self.app.ui.get_object("libraryContainer").get_child()
        selected_cards = card_view.get_selected_cards()
        tag = entry.get_text()
        if tag != "":
            lib_funct.tag_cards(selected_cards, tag, self.app)
            lib_funct.reload_library(self.app, tag)
        entry.set_text("")

    def on_drag_data_received(self, widget, drag_context, x, y, data, info, time):
        print("drag received")

    def on_tag_selected(self, selection, path, column):
        (model, pathlist) = selection.get_selected_rows()
        for path in pathlist:
            tree_iter = model.get_iter(path)
            tag = model.get_value(tree_iter, 0)
            self.app.current_lib_tag = tag
            lib_funct.reload_library(self.app, tag)

    def do_tag_tree_press_event(self, treeview, event):
        if event.button == 3:  # right click
            path = treeview.get_path_at_pos(int(event.x), int(event.y))
            if path:
                tree_iter = treeview.get_model().get_iter(path[0])
                tag = treeview.get_model().get_value(tree_iter, 0)
                self.app.ui.get_object("tagListPopup").popup(None, None, None, None, 0, event.time)

    def do_tag_list_rename(self, tree):
        (model, pathlist) = tree.get_selection().get_selected_rows()
        for path in pathlist:
            tree_iter = model.get_iter(path)
            tag = model.get_value(tree_iter, 0)

            self.app.show_tag_rename_dialog(tag)

    def do_tag_list_delete(self, tree):
        (model, pathlist) = tree.get_selection().get_selected_rows()
        for path in pathlist:
            tree_iter = model.get_iter(path)
            tag = model.get_value(tree_iter, 0)
            self.app.remove_tag(tag)
            self.app.current_page.emit('show')

    def do_refilter_library(self, container):
        # Access Card View inside of container
        container.get_child().filter.refilter()

    def lib_tree_popup_showed(self, menu):
        # Get selected cards
        card_list = self.app.ui.get_object("libraryContainer").get_child()
        cards = card_list.get_selected_cards()

        # Check if a tag is selected
        current_tag = self.app.current_lib_tag
        if current_tag == "All" or current_tag == "Untagged":
            return

        # Check if selected Cards are tagged
        for id_list in self.app.tags.values():
            for card_id in cards.keys():
                if id_list.__contains__(card_id):
                    # Enable untag menu item
                    self.app.ui.get_object("untagItem").set_sensitive(True)
                    return

    def do_popup_untag_cards(self, item):
        # Get selected cards
        card_list = self.app.ui.get_object("libraryContainer").get_child()
        cards = card_list.get_selected_cards()
        tag = self.app.current_lib_tag
        for card in cards.values():
            self.app.untag_card(card, tag)
        lib_funct.reload_library(self.app, tag)
        lib_funct.reload_tag_list(self.app, preserve=True)

    def do_popup_remove_card(self, item):
        # Get selected cards
        card_list = self.app.ui.get_object("libraryContainer").get_child()
        cards = card_list.get_selected_cards()
        # Remove selected cards
        for card in cards.values():
            self.app.remove_card_from_lib(card)
        lib_funct.reload_library(self.app, self.app.current_lib_tag)
        lib_funct.reload_tag_list(self.app, preserve=True)

    # ---------------------------------Wants----------------------------------------------

    def do_reload_wants(self, view):
        wants_funct.reload_wants_view(self.app)

    def on_new_wants_list_clicked(self, entry):
        name = entry.get_text()
        # Check if list name already exists
        if self.app.wants.__contains__(name):
            return
        self.app.add_want_list(name)
        wants_funct.reload_wants_view(self.app)

    # Handlers for TreeViews etc. wich have been not added by Glade

    # ---------------------------------Search Tree----------------------------------------------

    def on_search_card_selected(self, tree, row_no, column):
        (model, path_list) = tree.get_selection().get_selected_rows()
        for path in path_list:
            tree_iter = model.get_iter(path)
            card_id = model.get_value(tree_iter, 0)
            card_list = self.app.ui.get_object("searchResults").get_child()
            card = card_list.lib[card_id]
            self.app.show_card_details(card)

    def on_search_selection_changed(self, selection):
        (model, pathlist) = selection.get_selected_rows()
        tools = self.app.ui.get_object("selectionToolsBox")
        add_remove_button = self.app.ui.get_object("addRemoveButton")

        if pathlist:
            add_remove_button.set_sensitive(True)
        else:
            add_remove_button.set_sensitive(False)

    # ---------------------------------Library Tree----------------------------------------------

    def on_library_card_selected(self, tree, row_no, column):
        (model, path_list) = tree.get_selection().get_selected_rows()
        for path in path_list:
            tree_iter = model.get_iter(path)
            card_id = model.get_value(tree_iter, 0)
            card_list = self.app.ui.get_object("libraryContainer").get_child()
            card = card_list.lib[card_id]
            self.app.show_card_details(card)

    def on_library_tree_press_event(self, treeview, event):
        if event.button == 3:  # right click
            path = treeview.get_path_at_pos(int(event.x), int(event.y))
            if path:
                tree_iter = treeview.get_model().get_iter(path[0])
                self.app.ui.get_object("libListPopup").emit('show')
                self.app.ui.get_object("libListPopup").popup(None, None, None, None, 0, event.time)
            return True

    # ---------------------------------Wants Tree----------------------------------------------

    def on_wants_card_selected(self, tree, row, column):
        # TODO
        pass
