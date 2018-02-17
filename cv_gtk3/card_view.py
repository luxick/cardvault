import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from cv_gtk3.gtk_util import GTKUtilities
from cv_engine.util import MTGConstants


class CardView(Gtk.ScrolledWindow):
    """ Class for displaying a list of cards in an GTKTreeView """
    def __init__(self, ui_file, filtered):
        """ Constructor for a card list display
        :param ui_file: Full path to an CardView glade file
        :param filtered: Should the card list be filterable
        """
        self.filtered = filtered
        self.cards = []
        # Call constructor of superclass
        super(CardView, self).__init__()
        self.set_hexpand(True)
        self.set_vexpand(True)
        # Build UI
        self.ui = Gtk.Builder()
        self.ui.add_from_file(ui_file)
        self.tree = self.ui.get_object('cardTree')
        self.store = self.ui.get_object('cardStore')
        self.store.set_sort_func(4, self.compare_rarity, None)
        # Add the TreeView
        self.add(self.tree)

    def get_selected_cards(self):
        """ Get the currently selected cards in the TreeView
        :return: List od card objects
        """
        (model, path_list) = self.ui.get_object("cardTree").get_selection().get_selected_rows()
        selected_ids = []
        for path in path_list:
            tree_iter = model.get_iter(path)
            selected_ids.append(model.get_value(tree_iter, 0))
        return [card for card in self.cards if card.multiverse_id in selected_ids]

    def update(self, card_list):
        """ Update the card view with a new list of cards
        :param card_list:
        """
        self.cards = card_list
        self.ui.get_object("cardStore").clear()
        # Disable update if tree is filtered (performance)
        if self.filtered:
            self.tree.freeze_child_notify()
        # Fill list with new cards
        for card in card_list:
            if card.multiverse_id is None: continue
            # TODO load row color base on card status (owned, wanted,...)
            color = 'black'
            mana_cost = None
            if not card.types.__contains__('Land'):
                mana_cost = GTKUtilities.get_mana_icons(card.mana_cost)
            item = [card.multiverse_id,
                    card.name,
                    ' '.join(card.supertypes or ''),
                    ' '.join(card.types or ''),
                    card.rarity,
                    card.power,
                    card.toughness,
                    ', '.join(card.printings or ''),
                    mana_cost,
                    card.cmc,
                    card.set_name,
                    color,
                    card.original_text]
            self.store.append(item)
        # Reactivate update for filtered trees
        if self.filtered:
            self.tree.thaw_child_notify()

    @staticmethod
    def compare_rarity(model, row1, row2, _):
        """ Compare function for two the rarities of two cards
        :param model: The tree view model
        :param row1: The first row to compare
        :param row2: The second row to compare
        :param _: ignored
        :return: Integer value based on comparison
        """
        sort_column = 4
        value1 = model.get_value(row1, sort_column)
        value2 = model.get_value(row2, sort_column)
        if MTGConstants.rarities[value1.lower()] < MTGConstants.rarities[value2.lower()]:
            return -1
        elif value1 == value2:
            return 0
        else:
            return 1


