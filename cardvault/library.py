import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from cardvault import application
from cardvault import util
from cardvault import cardlist


class LibraryHandlers:
    def __init__(self, app: 'application.Application'):
        """Initialize the library view"""
        self.app = app
        # Create Tree View for library
        container = self.app.ui.get_object("libraryContainer")
        card_list = cardlist.CardList(True, self.app, util.GENERIC_TREE_COLORS)
        card_list.set_name("libScroller")
        # Show details
        card_list.tree.connect("row-activated", self.on_library_card_selected)
        # Show Context menu
        card_list.tree.connect("button-press-event", self.on_library_tree_press_event)
        card_list.filter.set_visible_func(self.app.filter_lib_func)
        container.add(card_list)
        container.add_overlay(self.app.ui.get_object("noResults"))
        container.show_all()

        self.app.ui.get_object("noResults").set_visible(False)

    def do_reload_library(self, view):
        """Handler for the 'show' signal"""
        self.reload_library()

    def do_tag_entry_changed(self, entry):
        input_valid = entry.get_text() and entry.get_text() != ""
        self.app.ui.get_object("newTagButton").set_sensitive(input_valid)

    def do_new_tag_clicked(self, entry):
        self.add_new_tag(entry.get_text())
        entry.set_text("")

    def do_show_all_clicked(self, button):
        # Clear selection in tag list
        self.app.ui.get_object("tagTree").get_selection().unselect_all()
        self.app.current_lib_tag = "All"
        self.reload_library("All")

    def do_show_untagged_clicked(self, button):
        # Clear selection in tag list
        self.app.ui.get_object("tagTree").get_selection().unselect_all()
        self.app.current_lib_tag = "Untagged"
        self.reload_library("Untagged")

    def do_tag_cards(self, entry):
        card_view = self.app.ui.get_object("libraryContainer").get_child()
        selected_cards = card_view.get_selected_cards()
        tag = entry.get_text()
        if tag != "":
            self.tag_cards(selected_cards, tag)
            self.reload_library(tag)
        entry.set_text("")

    def on_tag_selected(self, selection, path, column):
        (model, pathlist) = selection.get_selected_rows()
        for path in pathlist:
            tree_iter = model.get_iter(path)
            tag = model.get_value(tree_iter, 0)
            self.app.current_lib_tag = tag
            self.reload_library(tag)

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

            new_name = self.app.show_name_enter_dialog("Rename Tag", tag)
            if new_name and new_name != "":
                self.app.tag_rename(tag, new_name)
                self.app.current_page.emit('show')

    def do_tag_list_delete(self, tree):
        (model, pathlist) = tree.get_selection().get_selected_rows()
        for path in pathlist:
            tree_iter = model.get_iter(path)
            tag = model.get_value(tree_iter, 0)
            question = "Really delete tag: {}?".format(tag)
            dialog = Gtk.MessageDialog(self.app.ui.get_object("mainWindow"), 0, Gtk.MessageType.WARNING,
                                       Gtk.ButtonsType.YES_NO, question)
            response = dialog.run()
            dialog.destroy()
            if response == Gtk.ResponseType.NO:
                return
            self.app.tag_delete(tag)
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
        self.reload_library(tag)
        self.reload_tag_list(none_selected=True)

    def do_popup_remove_card(self, item):
        # Get selected cards
        card_list = self.app.ui.get_object("libraryContainer").get_child()
        cards = card_list.get_selected_cards()
        # Remove selected cards
        for card in cards.values():
            self.app.lib_card_remove(card)
        self.reload_library(self.app.current_lib_tag)
        self.reload_tag_list(none_selected=True)

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
            # Get the selection
            selection = treeview.get_selection()
            # Get the selected path(s)
            rows = selection.get_selected_rows()
            # If not clicked on selection, change selected rows
            if path[0] not in rows[1]:
                selection.unselect_all()
                selection.select_path(path[0])
            self.app.ui.get_object("libListPopup").emit('show')
            self.app.ui.get_object("libListPopup").popup(None, None, None, None, 0, event.time)
            return True

    # -------------------------- Class Functions -------------------------------

    def reload_library(self, tag="All"):
        if tag == "Untagged":
            lib = self.app.get_untagged_cards()
        elif tag == "All":
            lib = self.app.library
        else:
            lib = self.app.get_tagged_cards(tag)
        self.reload_tag_list(tag == "All" or tag == "Untagged")
        tag_combo = self.app.ui.get_object("tagCardCombo")
        tag_combo.set_model(self.app.ui.get_object("tagStore"))

        card_tree = self.app.ui.get_object("libraryContainer").get_child()
        if lib:
            self.app.ui.get_object("noResults").set_visible(False)
            card_tree.update(lib)
        else:
            card_tree.store.clear()
            self.app.ui.get_object("noResults").set_visible(True)

    def add_new_tag(self, name):
        self.app.tag_new(name)
        self.reload_tag_list(True)

    def reload_tag_list(self, none_selected=False):
        """Reload left pane tag list"""
        tree = self.app.ui.get_object("tagTree")
        (path, column) = tree.get_cursor()
        store = tree.get_model()
        store.clear()
        for tag, ids in self.app.tags.items():
            store.append([tag, tag + " (" + str(len(ids)) + ")"])
        if none_selected:
            tree.set_cursor(path if path else 0)
        store.set_sort_column_id(1, Gtk.SortType.ASCENDING)

    def tag_cards(self, card_list, tag):
        # Check if tag exist and create if necessary
        if not self.app.tags.__contains__(tag):
            self.app.tag_new(tag)

        for card in card_list.values():
            if not self.app.tags[tag].__contains__(card.multiverse_id):
                self.app.tag_card(card, tag)

