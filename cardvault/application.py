import sys
try:
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk
    from gi.repository import Pango
    from gi.repository import GdkPixbuf
except ImportError as ex:
    print("Couldn't import GTK dependencies. Make sure you "
          "installed the PyGTK package and %s module." % ex.name)
    sys.exit(-1)

import os
import copy
import re
import mtgsdk
from typing import Type, Dict, List

from cardvault import handlers
from cardvault import util
from cardvault import search_funct
from cardvault import lib_funct
from cardvault import wants_funct




class Application:
    # ---------------------------------Initialize the Application----------------------------------------------
    def __init__(self):
        # Load ui files
        self.ui = Gtk.Builder()
        self.ui.add_from_file(util.get_ui_filename("mainwindow.glade"))
        self.ui.add_from_file(util.get_ui_filename("overlays.glade"))
        self.ui.add_from_file(util.get_ui_filename("search.glade"))
        self.ui.add_from_file(util.get_ui_filename("library.glade"))
        self.ui.add_from_file(util.get_ui_filename("wants.glade"))
        self.ui.add_from_file(util.get_ui_filename("dialogs.glade"))

        self.current_page = None
        self.unsaved_changes = False
        self.current_lib_tag = "All"

        not_found = self.ui.get_object("pageNotFound")
        self.pages = {
            "search": self.ui.get_object("searchView"),
            "library": self.ui.get_object("libraryView"),
            "decks": not_found,
            "wants": self.ui.get_object("wantsView")
        }

        # Load configuration file
        self.configfile = util.get_root_filename("config.json")
        self.config = util.parse_config(self.configfile, util.default_config)

        util.LOG_LEVEL = self.config["log_level"]

        # Load data from cache path
        self.image_cache = util.reload_image_cache(util.CACHE_PATH + "images/")
        self.precon_icons = util.reload_preconstructed_icons(util.CACHE_PATH + "icons/")
        self.mana_icons = util.load_mana_icons(os.path.dirname(__file__) + "/resources/mana/")

        self.sets = util.load_sets(util.get_root_filename("sets"))

        self.library = Dict[str, Type[mtgsdk.Card]]
        self.tags = Dict[str, str]
        self.wants = Dict[str, List[Type[mtgsdk.Card]]]
        self.load_library()

        self.handlers = handlers.Handlers(self)
        self.ui.connect_signals(self.handlers)

        # Initialize the views

        search_funct.init_search_view(self)

        lib_funct.init_library_view(self)

        wants_funct.init_wants_view(self)

        self.ui.get_object("mainWindow").connect('delete-event', Gtk.main_quit)
        self.ui.get_object("mainWindow").show_all()
        self.push_status("Card Vault ready.")

        view_menu = self.ui.get_object("viewMenu")
        start_page = [page for page in view_menu.get_children() if page.get_name() == util.START_PAGE]
        start_page[0].activate()

    def push_status(self, msg):
        status_bar = self.ui.get_object("statusBar")
        status_bar.pop(0)
        status_bar.push(0, msg)

    def show_card_details(self, card):
        builder = Gtk.Builder()
        builder.add_from_file(util.get_ui_filename("detailswindow.glade"))
        builder.add_from_file(util.get_ui_filename("overlays.glade"))
        window = builder.get_object("cardDetails")
        window.set_title(card.name)
        # Card Image
        container = builder.get_object("imageContainer")
        pixbuf = self.get_card_image(card, 63 * 5, 88 * 5)
        image = Gtk.Image().new_from_pixbuf(pixbuf)
        container.add(image)
        # Name
        builder.get_object("cardName").set_text(card.name)
        # Types
        supertypes = ""
        if card.subtypes is not None:
            supertypes = " - " + " ".join(card.subtypes)
        types = " ".join(card.types) + supertypes
        builder.get_object("cardTypes").set_text(types)
        # Rarity
        builder.get_object("cardRarity").set_text(card.rarity if card.rarity else "")
        # Release
        builder.get_object("cardReleaseDate").set_text(card.release_date if card.release_date else "")
        # Set
        builder.get_object("cardSet").set_text(card.set_name)
        # Printings
        prints = []
        for set in card.printings:
            prints.append(self.sets[set].name)
        builder.get_object("cardPrintings").set_text(", ".join(prints))
        # Legalities
        grid = builder.get_object("legalitiesGrid")
        rows = 1
        for legality in card.legalities if card.legalities else {}:
            date_label = Gtk.Label()
            date_label.set_halign(Gtk.Align.END)
            text_label = Gtk.Label()
            text_label.set_line_wrap_mode(Pango.WrapMode.WORD)
            text_label.set_line_wrap(True)
            text_label.set_halign(Gtk.Align.END)
            color = self.config['legality_colors'][legality["legality"]]
            date_label.set_markup("<span fgcolor=\""+color+"\">" + legality["format"] + ":" + "</span>")
            text_label.set_markup("<span fgcolor=\""+color+"\">" + legality["legality"] + "</span>")
            grid.attach(date_label, 0, rows + 2, 1, 1)
            grid.attach(text_label, 1, rows + 2, 1, 1)

            rows += 1
        grid.show_all()

        # Rulings
        if card.rulings:
            grid = builder.get_object("rulesGrid")
            rows = 1
            for rule in card.rulings:
                date_label = Gtk.Label(rule["date"])
                text_label = Gtk.Label(rule["text"])
                text_label.set_line_wrap_mode(Pango.WrapMode.WORD)
                text_label.set_line_wrap(True)
                text_label.set_justify(Gtk.Justification.LEFT)
                text_label.set_halign(Gtk.Align.START)

                grid.attach(date_label, 0, rows+2, 1, 1)
                grid.attach(text_label, 1, rows+2, 1, 1)

                rows += 1
            grid.show_all()
        else:
            builder.get_object("ruleBox").set_visible(False)

        window.show_all()

        def eval_key_pressed(widget,event):
            key, modifier = Gtk.accelerator_parse('Escape')
            keyval = event.keyval
            if keyval == key:
                window.destroy()

        window.connect("key-press-event", eval_key_pressed)

    def show_question_dialog(self, title, message):
        dialog = Gtk.MessageDialog(self.ui.get_object("mainWindow"), 0, Gtk.MessageType.WARNING,
                                   Gtk.ButtonsType.YES_NO, title)
        dialog.format_secondary_text(message)
        response = dialog.run()
        dialog.destroy()
        return response

    def show_message(self, title, message):
        dialog = Gtk.MessageDialog(self.ui.get_object("mainWindow"), 0, Gtk.MessageType.INFO,
                                   Gtk.ButtonsType.OK, title)
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def show_rename_dialog(self, name: str) -> str:
        dialog = self.ui.get_object("renameDialog")     # type: Gtk.Dialog
        dialog.set_transient_for(self.ui.get_object("mainWindow"))
        entry = self.ui.get_object("renameDialogEntry")
        entry.set_text(name)

        result = dialog.run()
        dialog.hide()

        if result == Gtk.ResponseType.OK:
            return entry.get_text()
        else:
            return name

    def save_library(self):
        # Save library file
        util.save_file(util.get_root_filename("library"), self.library)
        # Save tags file
        util.save_file(util.get_root_filename("tags"), self.tags)
        # Save wants file
        util.save_file(util.get_root_filename("wants"), self.wants)
        self.unsaved_changes = False
        self.push_status("Library saved")

    def load_library(self):
        all_existing = True

        # Load library file
        self.library = util.load_file(util.get_root_filename("library"))
        if not self.library:
            all_existing = False
            self.library = {}

        # Load tags file
        self.tags = util.load_file(util.get_root_filename("tags"))
        if not self.tags:
            all_existing = False
            self.tags = {}

        # Load wants lists
        self.wants = util.load_file(util.get_root_filename("wants"))
        if not self.wants:
            all_existing = False
            self.wants = {}

        # If parts were missing save to create the files
        if not all_existing:
            self.save_library()
        self.push_status("Library loaded")

    def get_untagged_cards(self):
        lib = copy.copy(self.library)
        for ids in self.tags.values():
            for card_id in ids:
                try:
                    del lib[card_id]
                except KeyError:
                    pass
        return lib

    def get_tagged_cards(self, tag):
        if not tag:
            return self.library
        else:
            lib = {}
            for card_id in self.tags[tag]:
                lib[card_id] = self.library[card_id]
            return lib

    def tag_card(self, card, tag):
        list = self.tags[tag]
        list.append(card.multiverse_id)
        self.unsaved_changes = True

    def untag_card(self, card, tag):
        list = self.tags[tag]
        list.remove(card.multiverse_id)
        self.unsaved_changes = True

    def add_tag(self, tag):
        self.tags[tag] = []
        util.log("Tag '" + tag + "' added", util.LogLevel.Info)
        self.push_status("Added Tag \"" + tag + "\"")
        self.unsaved_changes = True

    def remove_tag(self, tag):
        del self.tags[tag]
        util.log("Tag '" + tag + "' removed", util.LogLevel.Info)
        self.push_status("Removed Tag \"" + tag + "\"")
        self.unsaved_changes = True

    def rename_tag(self, old, new):
        self.tags[new] = self.tags[old]
        del self.tags[old]
        util.log("Tag '" + old + "' renamed to '" + new + "'", util.LogLevel.Info)
        self.unsaved_changes = True

    def get_wanted_card_ids(self) -> List[str]:
        all_ids = []
        for cards in self.wants.values():
            next_ids = [card.multiverse_id for card in cards]
            all_ids = list(set(all_ids) | set(next_ids))
        return all_ids

    def get_wanted_cards(self, list_name: str = None) -> Dict[str, Type[mtgsdk.Card]]:
        if list_name:
            out = {card.multiverse_id: card for card in self.wants[list_name]}
            return out

    def rename_want_list(self, old, new):
        self.wants[new] = self.wants[old]
        del self.wants[old]
        util.log("Want List '" + old + "' renamed to '" + new + "'", util.LogLevel.Info)
        self.unsaved_changes = True

    def add_want_list(self, name):
        self.wants[name] = []
        util.log("Want list  '" + name + "' created", util.LogLevel.Info)
        self.push_status("Created want listwantsListContainer '" + name + "'")
        self.unsaved_changes = True

    def add_card_to_want_list(self, list_name, card):
        self.wants[list_name].append(card)
        util.log(card.name + " added to want list " + list_name, util.LogLevel.Info)
        self.unsaved_changes = True

    def add_card_to_lib(self, card, tag=None):
        if tag is not None:
            self.tag_card(card, tag)
        self.library[card.multiverse_id] = card
        self.push_status(card.name + " added to library")
        self.unsaved_changes = True

    def remove_card_from_lib(self, card):
        # Check if card is tagged
        for card_ids in self.tags.values():
            if card_ids.__contains__(card.multiverse_id):
                card_ids.remove(card.multiverse_id)

        del self.library[card.multiverse_id]
        self.push_status(card.name + " removed from library")
        self.unsaved_changes = True

    def get_card_image(self, card, sizex, sizey):
        # Try using file from local cache, or load online
        try:
            pixbuf = self.image_cache[card.multiverse_id]
        except KeyError as err:
            util.log("No local image for " + card.name + ". Loading from " + card.image_url, util.LogLevel.Info)
            pixbuf = util.load_card_image_online(card, sizex, sizey)
            self.image_cache[card.multiverse_id] = pixbuf
        return pixbuf

    def get_mana_icons(self, mana_string):
        if not mana_string:
            util.log("No mana string provided", util.LogLevel.Warning)
            return
        icon_list = re.findall("{(.*?)}", mana_string)
        icon_name = "_".join(icon_list)
        try:
            icon = self.precon_icons[icon_name]
        except KeyError:
            icon = util.create_mana_icons(self.mana_icons, mana_string)
            self.precon_icons[icon_name] = icon
        return icon

    def filter_lib_func(self, model, iter, data):
        filter_text = self.ui.get_object("searchLibEntry").get_text()
        if filter_text == "":
            return True
        else:
            return filter_text.lower() in model[iter][1].lower()


def main():
    win = Application()
    Gtk.main()
