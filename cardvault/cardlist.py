import copy

import gi
from cardvault import util
from cardvault import application
from gi.repository import Gtk, GdkPixbuf, Gdk

from typing import Dict, Type
from mtgsdk import Card

import time
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')


class CardList(Gtk.ScrolledWindow):
    def __init__(self, filtered, app: 'application.Application', row_colors: Dict[str, str]):
        Gtk.ScrolledWindow.__init__(self)
        self.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.set_hexpand(True)
        self.set_vexpand(True)

        self.filtered = filtered
        self.lib = {}
        self.app = app
        self.row_colors = row_colors

        builder = Gtk.Builder()
        builder.add_from_file(util.get_ui_filename("cardtree.glade"))

        self.filter = builder.get_object("cardStoreFiltered")

        self.store = builder.get_object("cardStore")

        self.tree = builder.get_object("cardTree")

        self.store.set_sort_func(4, self.compare_rarity, None)

        self.add(self.tree)

        self.selection = self.tree.get_selection()

    def get_selected_cards(self) -> dict:
        (model, pathlist) = self.selection.get_selected_rows()
        output = {}
        for path in pathlist:
            tree_iter = model.get_iter(path)
            card_id = model.get_value(tree_iter, 0)
            card = self.lib[card_id]
            output[card_id] = card
        return output

    def update(self, library: Dict[str, Type[Card]]):
        self.store.clear()
        if library is None:
            return
        self.lib = library
        # Disable update if tree is filtered (performance)
        if self.filtered:
            self.tree.freeze_child_notify()

        util.log("Updating tree view", util.LogLevel.Info)
        start = time.time()
        all_wants = self.app.get_wanted_card_ids()

        for card in library.values():
            if card.multiverse_id is not None:
                color = self.get_row_color(card, self.app.library, all_wants, self.row_colors)
                mana_cost = None if card.type == "Land" else self.app.get_mana_icons(card.mana_cost)
                item = [card.multiverse_id,
                        card.name,
                        " ".join(card.supertypes if card.supertypes else ""),
                        " ".join(card.types),
                        card.rarity,
                        card.power,
                        card.toughness,
                        ", ".join(card.printings),
                        mana_cost,
                        card.cmc,
                        card.set_name,
                        color]
                self.store.append(item)
        end = time.time()
        util.log("Time to build Table: " + str(round(end - start, 3)) + "s", util.LogLevel.Info)
        util.log("Total entries: " + str(len(self.lib)), util.LogLevel.Info)

        # Reactivate update for filtered trees
        if self.filtered:
            self.tree.thaw_child_notify()

    @staticmethod
    def compare_rarity(model, row1, row2, user_data):
        # Column for rarity
        sort_column = 4
        value1 = model.get_value(row1, sort_column)
        value2 = model.get_value(row2, sort_column)
        if util.rarity_dict[value1.lower()] < util.rarity_dict[value2.lower()]:
            return -1
        elif value1 == value2:
            return 0
        else:
            return 1

    @staticmethod
    def get_row_color(card, lib: dict, wants: dict, colors: dict) -> str:
        if lib.__contains__(card.multiverse_id):
            return colors["owned"]
        elif wants.__contains__(card.multiverse_id):
            return colors["wanted"]
        else:
            return colors["unowned"]


