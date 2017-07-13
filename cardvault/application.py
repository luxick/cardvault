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
import time
from typing import Type, Dict, List

from cardvault import handlers
from cardvault import util
from cardvault import database


class Application:
    # ---------------------------------Initialize the Application----------------------------------------------
    def __init__(self):

        # Load configuration file
        self.configfile = util.get_root_filename("config.json")
        self.config = util.parse_config(self.configfile, util.default_config)
        util.LOG_LEVEL = self.config["log_level"]
        util.log("Start using config file: '{}'".format(self.configfile), util.LogLevel.Info)

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

        self.db = database.CardVaultDB(util.get_root_filename(util.DB_NAME))

        # Create database tables if they do not exist
        self.db.db_create()

        not_found = self.ui.get_object("pageNotFound")
        self.pages = {
            "search": self.ui.get_object("searchView"),
            "library": self.ui.get_object("libraryView"),
            "decks": not_found,
            "wants": self.ui.get_object("wantsView")
        }

        # Load data from cache path
        util.log("Loading image cache...", util.LogLevel.Info)
        self.image_cache = util.reload_image_cache(util.CACHE_PATH + "images/")
        self.precon_icons = util.reload_preconstructed_icons(util.CACHE_PATH + "icons/")
        self.mana_icons = util.load_mana_icons(os.path.dirname(__file__) + "/resources/mana/")

        util.log("Loading set list...", util.LogLevel.Info)
        self.sets = util.load_sets(util.get_root_filename("sets"))

        self.library = Dict[str, Type[mtgsdk.Card]]
        self.tags = Dict[str, str]
        self.wants = Dict[str, List[Type[mtgsdk.Card]]]

        self.load_data()

        self.handlers = handlers.Handlers(self)
        self.ui.connect_signals(self.handlers)

        self.ui.get_object("mainWindow").connect('delete-event', Gtk.main_quit)
        self.ui.get_object("mainWindow").show_all()
        self.push_status("Card Vault ready.")

        view_menu = self.ui.get_object("viewMenu")
        start_page = [page for page in view_menu.get_children() if page.get_name() == util.START_PAGE]
        start_page[0].activate()

        util.log("Launching Card Vault version {}".format(util.VERSION), util.LogLevel.Info)

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
        pixbuf = util.load_card_image(card, 63 * 5, 88 * 5, self.image_cache)
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
        # Rarityget_card_image
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
            store = builder.get_object("rulesStore")
            for rule in card.rulings:
                store.append([rule["date"], rule["text"]])
        else:
            builder.get_object("ruleBox").set_visible(False)

        window.show_all()

        def eval_key_pressed(widget,event):
            key, modifier = Gtk.accelerator_parse('Escape')
            keyval = event.keyval
            if keyval == key:
                window.destroy()

        window.connect("key-press-event", eval_key_pressed)

    def show_dialog_ync(self, title: str, message: str) -> Gtk.ResponseType:
        """Display a simple Yes/No Question dialog and return the result"""
        dialog = self.ui.get_object("ync_dialog")
        dialog.set_transient_for(self.ui.get_object("mainWindow"))
        dialog.set_title(title)
        self.ui.get_object("ync_label").set_text(message)
        response = dialog.run()
        dialog.hide()
        return response

    def show_dialog_yn(self, title: str, message: str) -> Gtk.ResponseType:
        """Display a simple Yes/No Question dialog and return the result"""
        dialog = self.ui.get_object("yn_dialog")
        dialog.set_transient_for(self.ui.get_object("mainWindow"))
        dialog.set_title(title)
        self.ui.get_object("yn_label").set_text(message)
        response = dialog.run()
        dialog.hide()
        return response

    def show_message(self, title, message):
        dialog = Gtk.MessageDialog(self.ui.get_object("mainWindow"), 0, Gtk.MessageType.INFO,
                                   Gtk.ButtonsType.OK, title)
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def show_name_enter_dialog(self, title: str, value: str) -> str:
        dialog = self.ui.get_object("nameEnterDialog")     # type: Gtk.Dialog
        dialog.set_transient_for(self.ui.get_object("mainWindow"))
        label = self.ui.get_object("nameEnterLabel")
        label.set_text(title)
        entry = self.ui.get_object("nameEnterEntry")
        entry.set_text(value)
        entry.grab_focus()

        result = dialog.run()
        dialog.hide()

        if result == Gtk.ResponseType.OK:
            return entry.get_text()
        else:
            return value

    def save_config(self):
        cf = util.get_root_filename("config.json")
        util.save_config(self.config, cf)
        util.log("Config saved to '{}'".format(cf), util.LogLevel.Info)

    def save_data(self):
        # util.log("Saving Data to database", util.LogLevel.Info)
        # start = time.time()
        # self.db.save_library(self.library)
        # self.db.save_tags(self.tags)
        # self.db.save_wants(self.wants)
        # end = time.time()
        # util.log("Finished in {}s".format(str(round(end - start, 3))), util.LogLevel.Info)
        # self.unsaved_changes = False
        # self.push_status("All data saved.")
        pass

    def load_data(self):
        util.log("Loading Data from database", util.LogLevel.Info)
        start = time.time()
        self.library = self.db.lib_get_all()
        self.tags = self.db.tag_get_all()
        self.wants = self.db.wants_get_all()
        end = time.time()
        util.log("Finished in {}s".format(str(round(end-start, 3))), util.LogLevel.Info)
        self.push_status("All data loaded.")

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

    def tag_card(self, card, tag: str):
        """Add a card to tag"""
        list = self.tags[tag]
        list.append(card.multiverse_id)
        self.db.tag_card_add(tag, card.multiverse_id)

    def untag_card(self, card, tag: str):
        list = self.tags[tag]
        list.remove(card.multiverse_id)
        self.db.tag_card_remove(tag, card.multiverse_id)

    def tag_new(self, tag: str):
        self.tags[tag] = []
        self.db.tag_new(tag)
        util.log("Tag '" + tag + "' added", util.LogLevel.Info)
        self.push_status("Added Tag \"" + tag + "\"")

    def tag_delete(self, tag: str):
        del self.tags[tag]
        self.db.tag_delete(tag)
        util.log("Tag '" + tag + "' removed", util.LogLevel.Info)
        self.push_status("Removed Tag \"" + tag + "\"")

    def tag_rename(self, old, new):
        if old == new:
            return
        self.tags[new] = self.tags[old]
        del self.tags[old]
        self.db.tag_rename(old, new)
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

    def wants_new(self, name):
        """Add a empty wants list"""
        self.wants[name] = []
        self.db.wants_new(name)
        util.log("Want list  '" + name + "' created", util.LogLevel.Info)
        self.push_status("Created want list '" + name + "'")

    def wants_delete(self, name: str):
        """Delete an wants list an all cards in it"""
        del self.wants[name]
        self.db.wants_delete(name)
        util.log("Deleted Wants List '{}'".format(name), util.LogLevel.Info)
        self.push_status("Deleted Wants List '{}'".format(name))

    def wants_rename(self, old: str, new: str):
        if old == new:
            return
        self.wants[new] = self.wants[old]
        del self.wants[old]
        self.db.wants_rename(old, new)
        util.log("Want List '" + old + "' renamed to '" + new + "'", util.LogLevel.Info)

    def wants_card_add(self, list_name: str, card: 'mtgsdk.Card'):
        self.wants[list_name].append(card)
        self.db.wants_card_add(list_name, card.multiverse_id)
        util.log(card.name + " added to want list " + list_name, util.LogLevel.Info)

    def wants_card_remove(self, card: mtgsdk.Card, list: str):
        """Remove a card from a wants list"""
        l = self.wants[list]
        l.remove(card)
        self.db.wants_card_remove(list, card.multiverse_id)
        util.log("Removed '{}' from wants list '{}'".format(card.name, list), util.LogLevel.Info)

    def lib_card_add(self, card, tag=None):
        if tag is not None:
            self.tag_card(card, tag)
            self.db.tag_card_add(tag, card.multiverse_id)
        self.library[card.multiverse_id] = card
        self.db.lib_card_add(card)
        self.push_status(card.name + " added to library")

    def lib_card_add_bulk(self, cards: list, tag: str = None):
        for card in cards:
            if tag is not None:
                self.tag_card(card, tag)
                self.db.tag_card_add(tag, card.multiverse_id)
            self.lib_card_add(card, tag)
            self.db.lib_card_add(card)
        util.log("Added {} cards to library.".format(str(len(cards))), util.LogLevel.Info)
        self.push_status("Added {} cards to library.".format(str(len(cards))))

    def lib_card_remove(self, card):
        # Check if card is tagged
        is_tagged, tags = self.db.tag_card_check_tagged(card)
        if is_tagged:
            for tag in tags:
                self.tags[tag].remove(card.multiverse_id)
                self.db.tag_card_remove(tag, card.multiverse_id)

        del self.library[card.multiverse_id]
        self.db.lib_card_remove(card)
        util.log("Removed {} from library".format(card.name), util.LogLevel.Info)
        self.push_status(card.name + " removed from library")

    def override_user_data(self):
        """Called after import of user data. Overrides existing user data in database"""
        util.log("Clearing old user data", util.LogLevel.Info)
        self.db.db_clear_data_user()
        util.log("Attempt loading user data to database", util.LogLevel.Info)
        start = time.time()
        # Library
        for card in self.library.values():
            self.db.lib_card_add(card)
        # Tags
        for tag, card_ids in self.tags.items():
            self.db.tag_new(tag)
            for card_id in card_ids:
                self.db.tag_card_add(tag, card_id)
        # Wants
        for list_name, cards in self.wants.items():
            self.db.wants_new(list_name)
            for card in cards:
                self.db.wants_card_add(list_name, card.multiverse_id)
        end = time.time()
        util.log("Finished in {}s".format(str(round(end - start, 3))), util.LogLevel.Info)
        self.push_status("User data imported")

    def get_mana_icons(self, mana_string):
        if not mana_string:
            util.log("No mana string provided", util.LogLevel.Info)
            return
        icon_list = re.findall("{(.*?)}", mana_string.replace("/", "-"))
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
    Application()
    Gtk.main()
