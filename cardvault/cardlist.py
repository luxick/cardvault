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
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.set_hexpand(True)
        self.set_vexpand(True)

        self.filtered = filtered
        self.lib = {}
        self.app = app
        self.row_colors = row_colors

        # Columns are these:
        # 0 Multiverse ID
        # 1 Card Name
        # 2 Card Supertypes (Legendary,..)
        # 3 Card types (Creature, etc)
        # 4 Rarity
        # 5 Power
        # 6 Toughness
        # 7 Printings (Sets with this card in it)
        # 8 Mana Cost(Form: {G}{2})
        # 9 CMC
        # 10 Edition
        # 11 Color indicating if the card is owned or wanted
        self.store = Gtk.ListStore(int, str, str, str, str, str, str, str, GdkPixbuf.Pixbuf, int, str, str)
        if self.filtered:
            self.filter = self.store.filter_new()
            self.filter_and_sort = Gtk.TreeModelSort(self.filter)
            self.filter_and_sort.set_sort_func(4, self.compare_rarity, None)
            self.list = Gtk.TreeView(self.filter_and_sort)
        else:
            self.store.set_sort_func(4, self.compare_rarity, None)
            self.list = Gtk.TreeView(self.store)
        self.add(self.list)

        self.list.set_rules_hint(True)
        self.selection = self.list.get_selection()
        self.selection.set_mode(Gtk.SelectionMode.MULTIPLE)

        bold_renderer = Gtk.CellRendererText(xalign=0.5, yalign=0.5)
        bold_renderer.set_property("weight", 800)

        text_renderer = Gtk.CellRendererText(xalign=0.5, yalign=0.5)
        text_renderer.set_property("weight", 500)
        image_renderer = Gtk.CellRendererPixbuf()

        col_id = Gtk.TreeViewColumn(title="Multiverse ID", cell_renderer=text_renderer, text=0, foreground=11)
        col_id.set_visible(False)

        col_title = Gtk.TreeViewColumn(title="Name", cell_renderer=bold_renderer, text=1, foreground=11)
        col_title.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        col_title.set_expand(True)
        col_title.set_sort_column_id(1)

        col_supertypes = Gtk.TreeViewColumn(title="Supertypes", cell_renderer=text_renderer, text=2, foreground=11)
        col_supertypes.set_sort_column_id(2)
        col_supertypes.set_visible(False)

        col_types = Gtk.TreeViewColumn(title="Types", cell_renderer=text_renderer, text=3, foreground=11)
        col_types.set_sort_column_id(3)

        col_rarity = Gtk.TreeViewColumn(title="Rarity", cell_renderer=text_renderer, text=4, foreground=11)
        col_rarity.set_sort_column_id(4)

        col_power = Gtk.TreeViewColumn(title="Power", cell_renderer=text_renderer, text=5, foreground=11)
        col_power.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        col_power.set_fixed_width(50)
        col_power.set_sort_column_id(5)
        col_power.set_visible(False)

        col_thoughness = Gtk.TreeViewColumn(title="Toughness", cell_renderer=text_renderer, text=6, foreground=11)
        col_thoughness.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        col_thoughness.set_fixed_width(50)
        col_thoughness.set_sort_column_id(6)
        col_thoughness.set_visible(False)

        col_printings = Gtk.TreeViewColumn(title="Printings", cell_renderer=text_renderer, text=7, foreground=11)
        col_printings.set_sort_column_id(7)
        col_printings.set_visible(False)

        col_mana = Gtk.TreeViewColumn(title="Mana Cost", cell_renderer=image_renderer, pixbuf=8)
        col_mana.set_expand(False)
        col_mana.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        col_mana.set_sort_column_id(9)

        col_cmc = Gtk.TreeViewColumn(title="CMC", cell_renderer=text_renderer, text=9, foreground=11)
        col_cmc.set_visible(False)

        col_set_name = Gtk.TreeViewColumn(title="Edition", cell_renderer=text_renderer, text=10, foreground=11)
        col_set_name.set_expand(False)
        col_set_name.set_sort_column_id(10)

        self.list.append_column(col_id)
        self.list.append_column(col_title)
        self.list.append_column(col_supertypes)
        self.list.append_column(col_types)
        self.list.append_column(col_rarity)
        self.list.append_column(col_set_name)
        self.list.append_column(col_power)
        self.list.append_column(col_thoughness)
        self.list.append_column(col_printings)
        self.list.append_column(col_mana)
        self.list.append_column(col_cmc)

        self.store.set_sort_column_id(1, Gtk.SortType.ASCENDING)

    def get_selected_cards(self):
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
            self.list.freeze_child_notify()
            self.list.set_model(None)

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
            self.list.set_model(self.filter_and_sort)
            self.list.thaw_child_notify()

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


