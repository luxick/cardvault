import os

from cv_gtk3.card_view import CardView
from cv_gtk3.setting import GUISettings


class SearchPageHandlers:
    """ Class for handling Signals from the search page """
    def __init__(self, app):
        """ Constructor
        :param app: Reference to an CardvaultGTK object
        """
        self.app = app

        # Build the card view
        overlay = self.app.ui.get_object("searchResults")
        card_list = CardView(ui_file=os.path.join(GUISettings.glade_file_path, 'cardtree.glade'), filtered=False)
        card_list.set_name("resultsScroller")
        # TODO Context menu for card view
        # card_list.tree.connect("row-activated", self.on_search_card_selected)
        # card_list.selection.connect("changed", self.on_search_selection_changed)
        overlay.add(card_list)
        overlay.add_overlay(self.app.ui.get_object("searchOverlay"))
        overlay.show_all()

    def do_search_cards(self, *args):
        pass

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
