import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from cardvault import cardlist
from cardvault import application
from cardvault import util


class WantsHandlers:
    def __init__(self, app: 'application.Application'):
        self.app = app
        self.init_wants_view()

    def do_reload_wants(self, view):
        self.reload_wants_view()

    def on_new_wants_list_clicked(self, entry):
        name = entry.get_text()
        entry.set_text("")
        # Check if list name already exists
        if self.app.wants.__contains__(name):
            return
        self.app.add_want_list(name)
        self.reload_wants_view()

    def on_want_list_selected(self, selection, path, column):
        (model, pathlist) = selection.get_selected_rows()
        for path in pathlist:
            tree_iter = model.get_iter(path)
            list_name = model.get_value(tree_iter, 0)
            self.reload_wants_view(list_name)

    def do_wants_tree_press_event(self, treeview, event):
        if event.button == 3:  # right click
            path = treeview.get_path_at_pos(int(event.x), int(event.y))
            # Get the selection
            selection = treeview.get_selection()
            # Get the selected path(s)
            rows = selection.get_selected_rows()
            # If not clicked on selection, change selected rows
            if path:
                if path[0] not in rows[1]:
                    selection.unselect_all()
                    selection.select_path(path[0])
                self.app.ui.get_object("wants_wantsListPopup").popup(None, None, None, None, 0, event.time)
            return True

    def do_rename_wants_list(self, tree):
        (model, pathlist) = tree.get_selection().get_selected_rows()
        for path in pathlist:
            tree_iter = model.get_iter(path)
            tag = model.get_value(tree_iter, 0)

            new_name = self.app.show_name_enter_dialog("Rename Want List", tag)
            if not tag == new_name:
                self.app.rename_want_list(tag, new_name)
                self.app.current_page.emit('show')

    def do_delete_wants_list(self, tree):
        (model, pathlist) = tree.get_selection().get_selected_rows()
        for path in pathlist:
            tree_iter = model.get_iter(path)
            name = model.get_value(tree_iter, 0)

            self.app.delete_wants_list(name)
            self.app.current_page.emit('show')

    def on_want_cards_add_activated(self, menu_item):
        # Get selected cards
        tree = self.app.ui.get_object("wantsListContainer").get_child()
        selected = tree.get_selected_cards()

        # Get selected list
        list_tree = self.app.ui.get_object("wantsListsTree")
        (model, pathlist) = list_tree.get_selection().get_selected_rows()
        for path in pathlist:
            tree_iter = model.get_iter(path)
            list_name = model.get_value(tree_iter, 0)

            for card in selected.values():
                self.app.add_card_to_lib(card)
                self.app.remove_card_from_want_list(card, list_name)

        self.reload_wants_view(list_name)

    def on_want_cards_remove_activated(self, menu_item):
        # Get selected cards
        tree = self.app.ui.get_object("wantsListContainer").get_child()
        selected = tree.get_selected_cards()

        # Get selected list
        list_tree = self.app.ui.get_object("wantsListsTree")
        (model, pathlist) = list_tree.get_selection().get_selected_rows()
        for path in pathlist:
            tree_iter = model.get_iter(path)
            list_name = model.get_value(tree_iter, 0)

            for card in selected.values():
                self.app.remove_card_from_want_list(card, list_name)

        self.reload_wants_view(list_name)

    # ---------------------------------Wants Tree----------------------------------------------

    def on_wants_card_selected(self, tree, row, column):
        (model, path_list) = tree.get_selection().get_selected_rows()
        for path in path_list:
            tree_iter = model.get_iter(path)
            card_id = model.get_value(tree_iter, 0)
            card_list = self.app.ui.get_object("wantsListContainer").get_child()
            card = card_list.lib[card_id]
            self.app.show_card_details(card)

    def on_wants_cards_press_event(self, treeview, event):
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

            # Show popup and emit 'show' to trigger update function of popup
            self.app.ui.get_object("wants_cardListPopup").emit('show')
            self.app.ui.get_object("wants_cardListPopup").popup(None, None, None, None, 0, event.time)
            return True

    # -------------------------- Class Functions -------------------------------

    def init_wants_view(self):
        # Get container for Cardlist Tree
        container = self.app.ui.get_object("wantsListContainer")
        # Create new Cardlist
        card_list = cardlist.CardList(True, self.app, util.GENERIC_TREE_COLORS)
        card_list.set_name("wantsScroller")
        # Show details
        card_list.tree.connect("row-activated", self.on_wants_card_selected)
        card_list.tree.connect("button-press-event", self.on_wants_cards_press_event)
        # Add card list to container
        container.add(card_list)
        container.add_overlay(self.app.ui.get_object("wantsOverlay"))
        container.show_all()
        # Hide no results overlay
        self.app.ui.get_object("wantsOverlay").set_visible(False)

    def reload_wants_view(self, selected_list: str = None):
        tree = self.app.ui.get_object("wantsListContainer").get_child()  # type: cardlist.CardList
        cards = self.app.get_wanted_cards(selected_list)
        self.reload_wants_list(True)
        if cards:
            self.app.ui.get_object("wantsOverlay").set_visible(False)
            tree.update(cards)
        else:
            tree.store.clear()
            self.app.ui.get_object("wantsOverlay").set_visible(True)

        # Set Title
        label = self.app.ui.get_object("wantsTileLabel")  # type: Gtk.Label
        label.set_markup("<big>" + str(selected_list) + "</big>")


    def reload_wants_list(self, preserve=False):
        tree = self.app.ui.get_object("wantsListsTree")
        (path, column) = tree.get_cursor()
        store = tree.get_model()
        store.clear()

        for list_name, cards in self.app.wants.items():
            store.append([list_name, list_name + " (" + str(len(cards)) + ")"])
        if preserve:
            tree.set_cursor(path if path else 0)
        store.set_sort_column_id(1, Gtk.SortType.ASCENDING)