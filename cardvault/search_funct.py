import gi
import util
import config
import cardlist
import handlers
from gi.repository import Gtk
from mtgsdk import Card
from urllib.error import URLError, HTTPError
gi.require_version('Gtk', '3.0')


def init_search_view(app):
    # set mana icons on filter buttons
    buttons = [x for x in app.ui.get_object("manaFilterGrid").get_children()
               if isinstance(x, Gtk.ToggleButton)]
    _init_mana_buttons(buttons)
    # set auto completion for filter entry
    _init_set_entry(app.ui.get_object("setEntry"))
    # Fill rarity box
    _init_combo_box(app.ui.get_object("rarityCombo"), util.rarity_dict.keys())
    # Fill type box
    _init_combo_box(app.ui.get_object("typeCombo"), util.card_types)
    # Create Model for search results
    _init_results_tree(app.ui.get_object("cardTree"), app)


def search_cards(term):
    # Load filters from UI
    filters = _get_filters(util.app)

    # Load card info from internet
    try:
        cards = Card.where(name=term) \
            .where(colorIdentity=filters["mana"]) \
            .where(types=filters["type"]) \
            .where(set=filters["set"]) \
            .where(rarity=filters["rarity"]) \
            .where(pageSize=50) \
            .where(page=1).all()
    except (URLError, HTTPError) as err:
        print("Error connecting to the internet")
        return

    if len(cards) == 0:
        # TODO UI show no cards found
        return

    # Remove duplicate entries
    if config.show_from_all_sets is False:
        cards = _remove_duplicates(cards)

    # Pack results in a dictionary
    lib = {}
    for card in cards:
        lib[card.multiverse_id] = card
    return lib


def _init_results_tree(tree_view, app):
    overlay = app.ui.get_object("searchResults")
    card_list = cardlist.CardList(tree_view, False)
    card_list.set_name("resultsScroller")
    card_list.list.connect("row-activated", app.handlers.on_search_card_selected)
    overlay.add(card_list)
    overlay.add_overlay(app.ui.get_object("searchOverlay"))
    overlay.show_all()    


def _init_combo_box(combo, list):
    model = Gtk.ListStore(str)
    model.append(["All"])
    for entry in list:
        model.append([entry.title()])
    combo.set_model(model)
    cell = Gtk.CellRendererText()
    combo.pack_start(cell, True)
    combo.add_attribute(cell, "text", 0)
    combo.set_active(0)


def _get_filters(app):
    output = {}
    # Mana colors
    color_list = []
    # Go through mana color buttons an get the active filters
    for button in app.ui.get_object("manaFilterGrid").get_children():
        if isinstance(button, Gtk.ToggleButton):
            if button.get_active():
                color_list.append(button.get_name())
    output["mana"] = ",".join(color_list)
    # Rarity
    combo = app.ui.get_object("rarityCombo")
    output["rarity"] = _get_combo_value(combo)
    # Type
    combo = app.ui.get_object("typeCombo")
    output["type"] = _get_combo_value(combo)
    # Set
    name = app.ui.get_object("setEntry").get_text()
    for set in util.set_list:
        if set.name == name:
            output["set"] = set.code
    return output


def _remove_duplicates(cards):
    unique_cards = []
    unique_names = []
    # Reverse cardlist so we get the version with the most modern art
    for card in reversed(cards):
        if card.name not in unique_names:
            unique_names.append(card.name)
            unique_cards.append(card)
    return unique_cards


def _get_combo_value(combo):
    tree_iter = combo.get_active_iter()
    value = combo.get_model().get_value(tree_iter, 0)
    return value.replace("All", "")


def _init_mana_buttons(button_list):
    for button in button_list:
        image = Gtk.Image.new_from_pixbuf(util.create_mana_icons("{" + button.get_name() + "}"))
        button.set_image(image)


def _init_set_entry(entry):
    set_store = Gtk.ListStore(str, str)
    for set in util.set_list:
        set_store.append([set.name, set.code])
    completer = Gtk.EntryCompletion()
    completer.set_model(set_store)
    completer.set_text_column(0)
    entry.set_completion(completer)
