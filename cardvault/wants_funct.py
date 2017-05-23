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
    # Add card list to container
    container.add(card_list)
    container.add_overlay(app.ui.get_object("wantsOverlay"))
    container.show_all()
    # Hide no results overlay
    app.ui.get_object("wantsOverlay").set_visible(False)


def reload_wants_view(app: 'application.Application'):
    store = app.ui.get_object("wantsListsStore")
    store.clear()
    for list_name in app.wants.keys():
        display_name = list_name + " (" + str(len(app.wants[list_name])) + ")"
        store.append([list_name, display_name])


