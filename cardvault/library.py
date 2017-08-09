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
        self.active_tag = "All"
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
        self.active_tag = "All"
        self.reload_library("All")

    def do_show_untagged_clicked(self, button):
        # Clear selection in tag list
        self.app.ui.get_object("tagTree").get_selection().unselect_all()
        self.active_tag = "Untagged"
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
            self.active_tag = tag
            self.reload_library(tag)

    def do_tag_tree_press_event(self, tree, event):
        if event.button == 3:  # right click
            path = tree.get_path_at_pos(int(event.x), int(event.y))
            if path:
                tree_iter = tree.get_model().get_iter(path[0])
                tag = tree.get_model().get_value(tree_iter, 0)
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

            question = "Really delete '{}'?".format(tag)
            response = self.app.show_dialog_yn("Delete Tag", question)

            if response == Gtk.ResponseType.YES:
                self.app.tag_delete(tag)
                self.app.current_page.emit('show')

    @staticmethod
    def do_refilter_library(container):
        # Access Card View inside of container
        container.get_child().filter.refilter()

    def lib_tree_popup_showed(self, menu):
        """
        Construct the context menu for the card tree in library view.
        Menu items can vary if one or more cards are selected an if they are already tagged.
        Called By: libListPopup UI Element
        """
        tree = self.app.ui.get_object("libraryContainer").get_child()
        selected = tree.get_selected_cards()

        root = self.app.ui.get_object("tagItem")
        tags_men = Gtk.Menu()
        root.set_submenu(tags_men)

        for list_name in self.app.tags.keys():
            item = Gtk.MenuItem()
            tags_men.add(item)
            item.set_label(list_name)
            item.connect('activate', self.tag_cards_sig, selected, list_name)

        # Add separator
        tags_men.add(Gtk.SeparatorMenuItem())
        # Add new tag item
        new_tag = Gtk.MenuItem("New Tag")
        new_tag.connect('activate', self.lib_new_tag_and_add, selected)
        tags_men.add(new_tag)

        root.show_all()

        # Check if a selected card is tagged
        for id_list in self.app.tags.values():
            for card_id in selected.keys():
                if id_list.__contains__(card_id):
                    self.app.ui.get_object("untagItem").set_sensitive(True)
                    return

    def do_popup_untag_cards(self, item):
        # Get selected cards
        card_list = self.app.ui.get_object("libraryContainer").get_child()
        cards = card_list.get_selected_cards()
        tag = self.active_tag
        for card in cards.values():
            self.app.untag_card(card, tag)
        self.reload_library(tag)
        self.reload_tag_list(clear_selection=True)

    def do_popup_remove_card(self, item):
        # Get selected cards
        card_list = self.app.ui.get_object("libraryContainer").get_child()
        cards = card_list.get_selected_cards()
        # Remove selected cards
        for card in cards.values():
            self.app.lib_card_remove(card)
        self.reload_library(self.active_tag)
        self.reload_tag_list(clear_selection=True)

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
        self.reload_tag_list(not (tag == "All" or tag == "Untagged"))
        tag_combo = self.app.ui.get_object("tagCardCombo")
        tag_combo.set_model(self.app.ui.get_object("tagStore"))

        card_tree = self.app.ui.get_object("libraryContainer").get_child()
        if lib:
            self.app.ui.get_object("noResults").set_visible(False)
            card_tree.update(lib)
        else:
            card_tree.store.clear()
            self.app.ui.get_object("noResults").set_visible(True)

        self.app.ui.get_object("searchTitle").set_text(tag)

    def lib_new_tag_and_add(self, item, cards):
        response = self.app.show_name_enter_dialog("Enter name for new Tag", "")
        if not response == "":
            self.app.tag_new(response)
            self.tag_cards(cards, response)
        else:
            util.log("No tag name entered", util.LogLevel.Warning)
            self.app.push_status("No name for new tag entered")
        self.reload_library(self.active_tag)

    def add_new_tag(self, name):
        self.app.tag_new(name)
        self.reload_tag_list(True)

    def reload_tag_list(self, clear_selection=False):
        """Reload left pane tag list"""
        tree = self.app.ui.get_object("tagTree")
        (path, column) = tree.get_cursor()
        store = tree.get_model()
        store.clear()
        for tag, ids in self.app.tags.items():
            store.append([tag, tag + " (" + str(len(ids)) + ")"])
        if clear_selection:
            tree.set_cursor(path if path else 0)
        store.set_sort_column_id(1, Gtk.SortType.ASCENDING)

    def tag_cards_sig(self, wigdet, cards, tag):
        self.tag_cards(cards, tag)
        self.reload_library(self.active_tag)

    def tag_cards(self, card_list, tag):
        # Check if tag exist and create if necessary
        if not self.app.tags.__contains__(tag):
            self.app.tag_new(tag)

        for card in card_list.values():
            if not self.app.tags[tag].__contains__(card.multiverse_id):
                self.app.tag_card(card, tag)
