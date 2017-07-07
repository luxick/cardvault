import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from urllib.error import URLError, HTTPError

import time

from mtgsdk import Card

from cardvault import application
from cardvault import cardlist
from cardvault import util


class SearchHandlers:
    def __init__(self, app: 'application.Application'):
        self.app = app
        self.init_search_view()

    def do_search_cards(self, sender):
        search_term = self.app.ui.get_object("searchEntry").get_text()

        filters = self.get_filters()

        results = self.search_cards(search_term, filters)

        card_list = self.app.ui.get_object("searchResults").get_child()
        card_list.update(results)

        self.app.ui.get_object("searchOverlay").set_visible(False)

    @staticmethod
    def do_clear_mana_filter(mana_filter_grid):
        for toggle_button in mana_filter_grid.get_children():
            if isinstance(toggle_button, Gtk.ToggleButton):
                toggle_button.set_active(False)

    @staticmethod
    def do_clear_set_filter(entry, icon_pos, button):
        entry.set_text("")

    def do_add_clicked(self, button):
        card_view = self.app.ui.get_object("searchResults").get_child()
        (model, pathlist) = card_view.selection.get_selected_rows()

        for path in pathlist:
            tree_iter = model.get_iter(path)
            card_id = model.get_value(tree_iter, 0)
            card = card_view.lib[card_id]
            self.app.add_card_to_lib(card)
        self.reload_search_view()
        self.app.ui.get_object("searchEntry").grab_focus()

    def search_tree_popup_showed(self, menu):
        # Create tag submenu
        tags_item = self.app.ui.get_object("searchListPopupAddTag")
        tags_sub = Gtk.Menu()
        tags_item.set_submenu(tags_sub)

        for list_name in self.app.tags.keys():
            item = Gtk.MenuItem()
            tags_sub.add(item)
            item.set_label(list_name)
            item.connect('activate', self.search_popup_add_tags)

        # Add separator
        tags_sub.add(Gtk.SeparatorMenuItem())
        # Add new tag item
        new_tag = Gtk.MenuItem("New Tag")
        new_tag.connect('activate', self.new_tag_and_add)
        tags_sub.add(new_tag)

        tags_item.show_all()

        # Create wants Submenu
        wants_item = self.app.ui.get_object("searchListPopupWants")
        wants_sub = Gtk.Menu()
        wants_item.set_submenu(wants_sub)

        for list_name in self.app.wants.keys():
            item = Gtk.MenuItem()
            wants_sub.add(item)
            item.set_label(list_name)
            item.connect('activate', self.search_popup_add_wants)

        # Add separator
        wants_sub.add(Gtk.SeparatorMenuItem())
        # Add new tag item
        new_want = Gtk.MenuItem("New Want List")
        new_want.connect('activate', self.new_wants_and_add)
        wants_sub.add(new_want)

        wants_item.show_all()

    def new_tag_and_add(self, menu_item):
        # Get selected cards
        card_list = self.app.ui.get_object("searchResults").get_child()
        cards = card_list.get_selected_cards()
        response = self.app.show_name_enter_dialog("Enter name for new Tag", "")
        if not response == "":
            self.app.add_tag(response)
            for card in cards.values():
                self.app.add_card_to_lib(card, response)
        else:
            util.log("No tag name entered", util.LogLevel.Warning)
            self.app.push_status("No name for new tag entered")
        self.reload_search_view()

    def new_wants_and_add(self, menu_item):
        # Get selected cards
        card_list = self.app.ui.get_object("searchResults").get_child()
        cards = card_list.get_selected_cards()
        response = self.app.show_name_enter_dialog("Enter name for new Want List", "")
        if not response == "":
            self.app.add_want_list(response)
            for card in cards.values():
                self.app.add_card_to_want_list(response, card)
        else:
            util.log("No list name entered", util.LogLevel.Warning)
            self.app.push_status("No name for new wants list entered")
        self.reload_search_view()

    def search_popup_add_tags(self, item):
        # Get selected cards
        card_list = self.app.ui.get_object("searchResults").get_child()
        cards = card_list.get_selected_cards()
        for card in cards.values():
            self.app.add_card_to_lib(card, item.get_label())
        self.reload_search_view()
        self.app.push_status("Added " + str(len(cards)) + " card(s) to library.")

    def search_popup_add_wants(self, item):
        # Get selected cards
        card_list = self.app.ui.get_object("searchResults").get_child()
        cards = card_list.get_selected_cards()
        for card in cards.values():
            self.app.add_card_to_want_list(item.get_label(), card)
        self.reload_search_view()
        self.app.push_status("Added " + str(len(cards)) + " card(s) to Want List '" + item.get_label() + "'")

    def do_search_clear_all_clicked(self, button):
        """ Rest all controls in search view """
        self.app.ui.get_object("searchEntry").set_text("")
        self.do_clear_mana_filter(self.app.ui.get_object("manaFilterGrid"))
        self.app.ui.get_object("rarityCombo").set_active(0)
        self.app.ui.get_object("typeCombo").set_active(0)
        self.app.ui.get_object("setEntry").set_text("")

    def do_show_card_details(self, menu_item):
        tree = self.app.ui.get_object("searchResults").get_child()
        cards = tree.get_selected_cards()
        for card in cards.values():
            self.app.show_card_details(card)

    def do_search_add_to_lib(self, menu_item):
        tree = self.app.ui.get_object("searchResults").get_child()
        cards = tree.get_selected_cards()
        for card in cards.values():
            self.app.add_card_to_lib(card)
        self.reload_search_view()

    def init_search_view(self):
        # set mana icons on filter buttons
        buttons = [x for x in self.app.ui.get_object("manaFilterGrid").get_children()
                   if isinstance(x, Gtk.ToggleButton)]
        self._init_mana_buttons(buttons)
        # set auto completion for filter entry
        self._init_set_entry(self.app.ui.get_object("setEntry"))
        # Fill rarity box
        self._init_combo_box(self.app.ui.get_object("rarityCombo"), util.rarity_dict.keys())
        # Fill type box
        self._init_combo_box(self.app.ui.get_object("typeCombo"), util.card_types)
        # Create Model for search results
        self._init_results_tree()

    def reload_search_view(self):
        """ Reload the card tree """
        results_tree = self.app.ui.get_object("searchResults").get_child()
        cards = results_tree.lib
        results_tree.update(cards)

    def get_filters(self) -> dict:
        """ Read selected filters from UI and return values as dict """
        output = {}
        # Mana colors
        color_list = []
        # Go through mana color buttons an get the active filters
        for button in self.app.ui.get_object("manaFilterGrid").get_children():
            if isinstance(button, Gtk.ToggleButton):
                if button.get_active():
                    color_list.append(button.get_name())
        output["mana"] = ",".join(color_list)
        # Rarity
        combo = self.app.ui.get_object("rarityCombo")
        output["rarity"] = self._get_combo_value(combo)
        # Type
        combo = self.app.ui.get_object("typeCombo")
        output["type"] = self._get_combo_value(combo)
        # Set
        name = self.app.ui.get_object("setEntry").get_text()
        output["set"] = ""
        for mtgset in self.app.sets.values():
            if mtgset.name == name:
                output["set"] = mtgset.code
        return output

    def search_cards(self, term: str, filters: dict) -> dict:
        """Return a dict of cards based on a search term and filters"""
        # Check if a local database can be used for searching
        if self.app.config["local_db"]:
            util.log("Starting local search for '" + term + "'", util.LogLevel.Info)
            start = time.time()

            cards = self.app.db.search_cards_by_name_filtered(term, filters, 100)

            end = time.time()
            util.log("Card info fetched in {}s".format(round(end - start, 3)), util.LogLevel.Info)

        else:
            util.log("Starting online search for '" + term + "'", util.LogLevel.Info)
            util.log("Used Filters: " + str(filters), util.LogLevel.Info)

            # Load card info from internet
            try:
                util.log("Fetching card info ...", util.LogLevel.Info)
                start = time.time()
                data = Card.where(name=term) \
                    .where(colorIdentity=filters["mana"]) \
                    .where(types=filters["type"]) \
                    .where(set=filters["set"]) \
                    .where(rarity=filters["rarity"]) \
                    .where(pageSize=50) \
                    .where(page=1).all()
                end = time.time()
                util.log("Card info fetched in {}s".format(round(end - start, 3)), util.LogLevel.Info)
            except (URLError, HTTPError) as err:
                util.log(err, util.LogLevel.Error)
                return {}

            # Remove duplicate entries
            if util.SHOW_FROM_ALL_SETS is False:
                data = self._remove_duplicates(data)
            # Pack results in a dictionary
            cards = {}
            for card in data:
                cards[card.multiverse_id] = card

        # Check if results were found
        if len(cards) == 0:
            # TODO UI show no cards found
            util.log("No Cards found", util.LogLevel.Info)
            return {}
        util.log("Found " + str(len(cards)) + " cards", util.LogLevel.Info)
        return cards

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

    def on_search_tree_press_event(self, treeview, event):
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
                self.app.ui.get_object("searchListPopup").emit('show')
                self.app.ui.get_object("searchListPopup").popup(None, None, None, None, 0, event.time)
            return True

    # -------------------------- Class Functions -------------------------------

    def _init_results_tree(self):
        overlay = self.app.ui.get_object("searchResults")
        card_list = cardlist.CardList(False, self.app, util.SEARCH_TREE_COLORS)
        card_list.set_name("resultsScroller")
        card_list.tree.connect("row-activated", self.on_search_card_selected)
        card_list.selection.connect("changed", self.on_search_selection_changed)
        overlay.add(card_list)
        overlay.add_overlay(self.app.ui.get_object("searchOverlay"))
        overlay.show_all()

        # Connect signal for context menu
        card_list.tree.connect("button-press-event", self.on_search_tree_press_event)

    @staticmethod
    def _init_combo_box(combo, card_list: list):
        """ Initialize a combo box model """
        model = Gtk.ListStore(str)
        model.append(["All"])
        for entry in card_list:
            model.append([entry.title()])
        combo.set_model(model)
        cell = Gtk.CellRendererText()
        combo.pack_start(cell, True)
        combo.add_attribute(cell, "text", 0)
        combo.set_active(0)

    @staticmethod
    def _remove_duplicates(cards: list) -> list:
        """ Remove cards with the same name from a list """
        unique_cards = []
        unique_names = []
        # Reverse cardlist so we get the version with the most modern art
        for card in reversed(cards):
            if card.name not in unique_names:
                unique_names.append(card.name)
                unique_cards.append(card)
        return unique_cards

    @staticmethod
    def _get_combo_value(combo) -> str:
        """ Get value from a combo box control """
        tree_iter = combo.get_active_iter()
        value = combo.get_model().get_value(tree_iter, 0)
        return value.replace("All", "")

    def _init_mana_buttons(self, button_list):
        """ Initialize mana buttons """
        for button in button_list:
            image = Gtk.Image.new_from_pixbuf(self.app.get_mana_icons("{" + button.get_name() + "}"))
            button.set_image(image)

    def _init_set_entry(self, entry):
        """ Initialize model for set entry """
        set_store = Gtk.ListStore(str, str)
        for mtgset in self.app.sets.values():
            set_store.append([mtgset.name, mtgset.code])
        completer = Gtk.EntryCompletion()
        completer.set_model(set_store)
        completer.set_text_column(0)
        entry.set_completion(completer)
