import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from cardvault import cardlist
from cardvault import application


def init_wants_view(app: 'application.Application'):
    # Get container for Cardlist Tree
    container = app.ui.get_object("wantsListContainer")
    # Create new Cardlist
    card_list = cardlist.CardList(True, app)
    card_list.set_name("wantsScroller")
    # Show details
    card_list.list.connect("row-activated", app.handlers.on_wants_card_selected)
    card_list.list.connect("button-press-event", app.handlers.on_wants_cards_press_event)
    # Add card list to container
    container.add(card_list)
    container.add_overlay(app.ui.get_object("wantsOverlay"))
    container.show_all()
    # Hide no results overlay
    app.ui.get_object("wantsOverlay").set_visible(False)


def reload_wants_view(app: 'application.Application', selected_list: str = None):
    tree = app.ui.get_object("wantsListContainer").get_child()  # type: cardlist.CardList
    cards = app.get_wanted_cards(selected_list)
    reload_wants_list(app, True)
    if cards:
        app.ui.get_object("wantsOverlay").set_visible(False)
        tree.update(cards)
    else:
        tree.store.clear()
        app.ui.get_object("wantsOverlay").set_visible(True)

    # Set Title
    label = app.ui.get_object("wantsTileLabel")  # type: Gtk.Label
    label.set_markup("<big>" + selected_list + "</big>")

def reload_wants_list(app: 'application.Application', preserve=False):
    tree = app.ui.get_object("wantsListsTree")
    (path, column) = tree.get_cursor()
    store = tree.get_model()
    store.clear()

    for list_name, cards in app.wants.items():
        store.append([list_name, list_name + " (" + str(len(cards)) + ")"])
    if preserve:
        tree.set_cursor(path if path else 0)
    store.set_sort_column_id(1, Gtk.SortType.ASCENDING)
