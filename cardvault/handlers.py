import gi
import config
import lib_funct
import search_funct
import util
from gi.repository import Gtk
gi.require_version('Gtk', '3.0')


class Handlers:
    def __init__(self, app):
        self.app = app

    # ----------------Main Window-----------------

    def do_save_library(self, item):
        util.save_library()

    def do_export_library(self, item):
        util.export_library()

    def do_import_library(self, item):
        util.import_library()
        self.app.current_page.emit('show')

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

            app_title = new_page.get_name() + " - " + config.application_title
            self.app.ui.get_object("mainWindow").set_title(app_title)

    def do_delete_event(self, arg1, arg2):
        if util.unsaved_changes:
            response = util.show_question_dialog("Unsaved Changes", "You have unsaved changes in your library. "
                                                                    "Save before exiting?")
            if response == Gtk.ResponseType.YES:
                util.save_library()

    # ----------------Search-----------------

    def do_search_cards(self, sender):
        search_term = self.app.ui.get_object("searchEntry").get_text()

        results = search_funct.search_cards(search_term)

        card_list = self.app.ui.get_object("searchResults").get_child()
        card_list.update(results)

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
            search_funct.add_to_library(card)
        search_funct.reload_serach_view(self.app)

    #----------------Library-----------------

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
        lib_funct.reload_library(self.app)

    def do_show_untagged_clicked(self, button):
        # Clear selection in tag list
        self.app.ui.get_object("tagTree").get_selection().unselect_all()
        lib_funct.reload_library(self.app, "untagged")

    def do_tag_cards(self, entry):
        card_view = self.app.ui.get_object("libraryContainer").get_child()
        selected_cards = card_view.get_selected_cards()
        tag = entry.get_text()
        lib_funct.tag_cards(selected_cards, tag)
        lib_funct.reload_library(self.app, tag)

    def on_drag_data_received(self, widget, drag_context, x,y, data,info, time):
        print("drag received")

    def on_tag_selected(self, selection, path, column):
        (model, pathlist) = selection.get_selected_rows()
        for path in pathlist:
            tree_iter = model.get_iter(path)
            tag = model.get_value(tree_iter, 0)
            lib_funct.reload_library(self.app, tag)

    # Handlers for TreeViews etc. wich have been not added by Glade

    #----------------Search-----------------

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

    # ----------------Library-----------------

    def on_library_card_selected(self, tree, row_no, column):
        (model, path_list) = tree.get_selection().get_selected_rows()
        for path in path_list:
            tree_iter = model.get_iter(path)
            card_id = model.get_value(tree_iter, 0)
            card_list = self.app.ui.get_object("libraryContainer").get_child()
            card = card_list.lib[card_id]
            self.app.show_card_details(card)


