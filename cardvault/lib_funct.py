import cardlist
import util
import gi
gi.require_version('Gtk', '3.0')


def init_library_view(app):
    # Create Tree View for library
    container = app.ui.get_object("libraryContainer")
    card_list = cardlist.CardList(True)
    card_list.set_name("libScroller")
    card_list.list.connect("row-activated", app.handlers.on_library_card_selected)
    container.add(card_list)
    container.add_overlay(app.ui.get_object("noResults"))
    container.add_overlay(app.ui.get_object("libEmpty"))
    container.show_all()

    app.ui.get_object("noResults").set_visible(False)


def reload_library(app, tag=None):
    lib = {}
    if tag == "untagged":
        lib = util.get_untagged_cards()
        tag = None
    else:
        lib = util.get_library(tag)
    reload_tag_list(app, tag)
    card_tree = app.ui.get_object("libraryContainer").get_child()
    if lib:
        app.ui.get_object("libEmpty").set_visible(False)
        app.ui.get_object("noResults").set_visible(False)
        card_tree.update(lib)
    else:
        card_tree.store.clear()
        app.ui.get_object("noResults").set_visible(True)



def add_new_tag(name, app):
    util.add_tag(name)
    reload_tag_list(app, True)


def reload_tag_list(app, preserve=False):
    tree = app.ui.get_object("tagTree")
    (path, column)  = tree.get_cursor()
    store = tree.get_model()
    store.clear()
    for tag, ids in util.tags.items():
        store.append([tag, tag + " (" + str(len(ids)) + ")"])
    if preserve:
        tree.set_cursor(path if path else 0)


def tag_cards(card_list, tag):
    # Check if tag exist and create if necessary
    if not util.tags.__contains__(tag):
        util.add_tag(tag)

    for card in card_list.values():
        if not util.tags[tag].__contains__(card.multiverse_id):
            util.tag_card(card, tag)
