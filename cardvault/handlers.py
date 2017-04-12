import gi
import config
import util
import search_funct
from mtgsdk import Card
from gi.repository import Gtk
gi.require_version('Gtk', '3.0')


class Handlers:
    def __init__(self, app):
        self.app = app
        
    def do_search_cards(self, sender):
        search_term = self.app.ui.get_object("searchEntry").get_text()

        results = search_funct.search_cards(search_term)

        card_list = self.app.ui.get_object("searchResults").get_child()
        card_list.update(results)

        self.app.ui.get_object("searchOverlay").set_visible(False)

    def on_view_changed(self, item):
        if item.get_active():
            container = self.app.ui.get_object("contentPage")
            new_page = self.app.pages[item.get_name()]
            if self.app.current_page:
               container.remove(self.app.current_page)
            self.app.current_page = new_page
            container.pack_start(self.app.current_page, True, True, 0)
            container.show_all()

            app_title = new_page.get_name() + " - " + config.application_title
            self.app.ui.get_object("mainWindow").set_title(app_title)

    def do_clear_mana_filter(self, mana_filter_grid):
        for toggle_button in mana_filter_grid.get_children():
            if isinstance(toggle_button, Gtk.ToggleButton):
                toggle_button.set_active(False)

    def do_clear_set_filter(self, entry, icon_pos, button):
        entry.set_text("")

    def do_add_remove_clicked(self, button):
        pass

    # Handlers for TreeViews etc. wich have been not added by Glade

    def on_search_card_selected(self, tree, row_no, column):
        (model, path_list) = tree.get_selection().get_selected_rows()

        for path in path_list:
            tree_iter = model.get_iter(path)
            card_id = model.get_value(tree_iter, 0)
            card_list = self.app.ui.get_object("searchResults").get_child()
            card = card_list.lib[card_id]
            self.app.show_card_details(card)


