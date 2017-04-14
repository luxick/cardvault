import cardlist
import util
import gi
from gi.repository import GObject
gi.require_version('Gtk', '3.0')


def init_library_view(app):
    # Create Tree View for library
    container = app.ui.get_object("libraryContainer")
    card_list = cardlist.CardList(True)
    card_list.set_name("libScroller")
    card_list.list.connect("row-activated", app.handlers.on_library_card_selected)
    container.add(card_list)
    container.add_overlay(app.ui.get_object("libEmpty"))
    container.show_all()


def reload_library(app):
    reload_tag_list(app)
    card_tree = app.ui.get_object("libraryContainer").get_child()
    if util.library.items():
        app.ui.get_object("libEmpty").set_visible(False)
        card_tree.update(util.library)


def add_new_tag(name, app):
    util.add_tag(name)
    reload_tag_list(app)

def reload_tag_list(app):
    tree = app.ui.get_object("tagTree")
    store = tree.get_model()
    store.clear()
    store.append(["_All", "All" + " (" + str(len(util.library)) + ")"])
    for tag, ids in util.tags.items():
        store.append([tag, tag + " (" + str(len(ids)) + ")"])