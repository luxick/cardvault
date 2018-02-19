import os

from cv_gtk3.card_view import CardView
from cv_gtk3.gtk_util import GTKUtilities


class SearchPageHandlers:
    """ Class for handling Signals from the search page """
    def __init__(self, app):
        """ Constructor
        :param app: Reference to an CardvaultGTK object
        """
        self.app = app

        # Build the card view
        overlay = self.app.ui.get_object("searchResults")
        self.card_list = CardView(filtered=False)
        self.card_list.set_name("resultsScroller")
        # TODO Context menu for card view
        # card_list.tree.connect("row-activated", self.on_search_card_selected)
        # card_list.selection.connect("changed", self.on_search_selection_changed)
        overlay.add(self.card_list)
        overlay.add_overlay(self.app.ui.get_object("searchOverlay"))
        overlay.show_all()

    def do_search_cards(self, search_entry):
        """ Search cards in database based on user input and display them in a card view
        :param search_entry: Search entry widget
        """
        search_term = search_entry.get_text()
        results = self.app.engine.search_by_name(search_term)
        self.card_list.update(results)
        # Switch Overlay off and set info diaplay
        self.app.ui.get_object("searchOverlay").set_visible(False)
        self.app.ui.get_object("search_title_label").set_visible(True)
        self.app.ui.get_object("search_title").set_text(search_term)

    @staticmethod
    def do_clear_mana_filter(button_grid):
        """ Reset filter buttons in mana grid """
        for button in button_grid.get_children():
            if hasattr(button, 'set_active'):
                button.set_active(False)

    @staticmethod
    def do_clear_set_filter(entry, *_):
        """ Reset set filter combo box """
        entry.set_text('')

    def do_search_clear_all_clicked(self, *_):
        """ Rest all controls in search view """
        self.app.ui.get_object("searchEntry").set_text("")
        self.do_clear_mana_filter(self.app.ui.get_object("manaFilterGrid"))
        self.app.ui.get_object("rarityCombo").set_active(0)
        self.app.ui.get_object("typeCombo").set_active(0)
        self.app.ui.get_object("setEntry").set_text("")

    def search_tree_popup_showed(self, _):
        pass

    def do_show_card_details(self, _):
        pass

    def do_search_add_to_lib(self, _):
        pass
