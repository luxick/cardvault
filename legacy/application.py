import gi
import os
import copy
import re
import mtgsdk
import time

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject, Pango
from typing import Type, Dict, List
from cardvault import handlers
from cardvault import util
from cardvault import database


class Application:
    # ---------------------------------Initialize the Application----------------------------------------------
    def __init__(self):
        # Load configuration file
        self.config = self.load_config()
        util.LOG_LEVEL = self.config["log_level"]
        util.log("Start using config file: '{}'".format(util.get_root_filename("config.json")), util.LogLevel.Info)

        self.ui = Gtk.Builder()
        self.ui.add_from_file(util.get_ui_filename("mainwindow.glade"))
        self.ui.add_from_file(util.get_ui_filename("overlays.glade"))
        self.ui.add_from_file(util.get_ui_filename("search.glade"))
        self.ui.add_from_file(util.get_ui_filename("library.glade"))
        self.ui.add_from_file(util.get_ui_filename("wants.glade"))
        self.ui.add_from_file(util.get_ui_filename("dialogs.glade"))

        self.current_page = None
        self.current_lib_tag = "Untagged"

        self.db = database.CardVaultDB(util.get_root_filename(util.DB_NAME))
        # Create database tables if they do not exist
        self.db.db_create()

        not_found = self.ui.get_object("pageNotFound")
        self.pages = {
            "search": self.ui.get_object("searchView"),
            "library": self.ui.get_object("libraryView"),
            "wants": self.ui.get_object("wantsView")
        }

        # Load data from cache path
        util.log("Loading image cache...", util.LogLevel.Info)
        self.image_cache = util.reload_image_cache(util.CACHE_PATH + "images/")
        self.precon_icons = util.reload_preconstructed_icons(util.CACHE_PATH + "icons/")
        self.mana_icons = util.load_mana_icons(os.path.dirname(__file__) + "/resources/mana/")

        self.library = Dict[str, Type[mtgsdk.Card]]
        self.tags = Dict[str, str]
        self.wants = Dict[str, List[Type[mtgsdk.Card]]]
        self.load_user_data()

        self.ui.get_object('statusbar_icon').set_from_icon_name(util.online_icons[self.is_online()],
                                                                Gtk.IconSize.BUTTON)
        self.ui.get_object('statusbar_icon').set_tooltip_text(util.online_tooltips[self.is_online()])

        self.handlers = handlers.Handlers(self)
        self.ui.connect_signals(self.handlers)

        self.ui.get_object("mainWindow").connect('delete-event', Gtk.main_quit)
        self.ui.get_object("mainWindow").show_all()
        self.push_status("Card Vault ready.")

        view_menu = self.ui.get_object("viewMenu")
        view = self.config["start_page"] if not self.config["start_page"] == "dynamic" else self.config["last_viewed"]
        start_page = [page for page in view_menu.get_children() if page.get_name() == view]
        start_page[0].activate()

        util.log("Launching Card Vault version {}".format(util.VERSION), util.LogLevel.Info)

        if self.config.get('first_run'):
            ref = '<a href="' + util.MANUAL_LOCATION + '">' + util.MANUAL_LOCATION + '</a>'
            s = "Welcome to Card Vault.\n\nIf you need help using the application please refer to the manual at\n{}\n\n" \
                "To increase search performance and to be able to search while offline it is advised to use the " \
                "offline mode.\nDo you want to start the download?".format(ref)
            response = self.show_dialog_yn("Welcome", s)
            if response == Gtk.ResponseType.YES:
                self.handlers.do_download_card_data(Gtk.MenuItem())
                self.config['first_run'] = False
                self.save_config()

    def push_status(self, msg):
        status_bar = self.ui.get_object("statusBar")
        status_bar.pop(0)
        status_bar.push(0, msg)

    def show_card_details(self, card):
        builder = Gtk.Builder()
        builder.add_from_file(util.get_ui_filename("detailswindow.glade"))
        builder.add_from_file(util.get_ui_filename("overlays.glade"))
        window = builder.get_object("cardDetails")
        window.set_title(card.get('name'))
        # Card Image
        container = builder.get_object("imageContainer")
        pixbuf = util.load_card_image(card, 63 * 5, 88 * 5, self.image_cache)
        image = Gtk.Image().new_from_pixbuf(pixbuf)
        container.add(image)
        # Name
        builder.get_object("cardName").set_text(card.get('name'))
        # Types
        supertypes = ""
        if card.get('subtypes'):
            supertypes = " - " + " ".join(card.get('subtypes'))
        types = " ".join(card.get('types')) + supertypes
        builder.get_object("cardTypes").set_text(types)
        # Rarity
        builder.get_object("cardRarity").set_text(card.get('rarity') or "")
        # Release
        builder.get_object("cardReleaseDate").set_text(card.get('release_date') or "")
        # Set
        builder.get_object("cardSet").set_text(card.get('set_name'))
        # Printings
        all_sets = self.get_all_sets()
        prints = [all_sets[set_name].get('name') for set_name in card.get('printings')]
        builder.get_object("cardPrintings").set_text(", ".join(prints))
        # Legalities
        grid = builder.get_object("legalitiesGrid")
        rows = 1
        for legality in card.get('legalities') or {}:
            date_label = Gtk.Label()
            date_label.set_halign(Gtk.Align.END)
            text_label = Gtk.Label()
            text_label.set_line_wrap_mode(Pango.WrapMode.WORD)
            text_label.set_line_wrap(True)
            text_label.set_halign(Gtk.Align.END)
            color = util.LEGALITY_COLORS[legality["legality"]]
            date_label.set_markup("<span fgcolor=\"" + color + "\">" + legality["format"] + ":" + "</span>")
            text_label.set_markup("<span fgcolor=\"" + color + "\">" + legality["legality"] + "</span>")
            grid.attach(date_label, 0, rows + 2, 1, 1)
            grid.attach(text_label, 1, rows + 2, 1, 1)

            rows += 1
        grid.show_all()

        # Rulings
        if card.get('rulings'):
            store = builder.get_object("rulesStore")
            for rule in card.get('rulings'):
                store.append([rule["date"], rule["text"]])
        else:
            builder.get_object("ruleBox").set_visible(False)

        window.show_all()

        def eval_key_pressed(widget, event):
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
        self.ui.get_object("ync_label").set_markup(message)
        response = dialog.run()
        dialog.hide()
        return response

    def show_dialog_yn(self, title: str, message: str) -> Gtk.ResponseType:
        """Display a simple Yes/No Question dialog and return the result"""
        dialog = self.ui.get_object("yn_dialog")
        dialog.set_transient_for(self.ui.get_object("mainWindow"))
        dialog.set_title(title)
        self.ui.get_object("yn_label").set_markup(message)
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
        dialog = self.ui.get_object("nameEnterDialog")  # type: Gtk.Dialog
        dialog.set_transient_for(self.ui.get_object("mainWindow"))
        dialog.set_title(title)
        entry = self.ui.get_object("nameEnterEntry")
        entry.set_text(value)
        entry.grab_focus()

        result = dialog.run()
        dialog.hide()

        if result == Gtk.ResponseType.OK:
            return entry.get_text()
        else:
            return value

    def show_preferences_dialog(self):
        """Show a dialog to adjust user preferences"""
        dialog = self.ui.get_object("pref_dialog")  # type: Gtk.Dialog
        dialog.set_transient_for(self.ui.get_object("mainWindow"))

        store = Gtk.ListStore(str, str)
        for page in self.pages.keys():
            store.append([page.title(), page])
        store.append(["Continue where you left", "dynamic"])
        page_map = {"search": 0,
                    "library": 1,
                    "decks": 2,
                    "wants": 3,
                    "dynamic": 4}
        self.ui.get_object("pref_start_view_combo").set_model(store)
        self.ui.get_object("pref_start_view_combo").set_active(page_map[self.config["start_page"]])

        self.ui.get_object("pref_show_all_check").set_active(self.config["show_all_in_search"])

        result = dialog.run()
        dialog.hide()

        if not result == Gtk.ResponseType.OK:
            return

        tree_iter = self.ui.get_object("pref_start_view_combo").get_active_iter()
        value = self.ui.get_object("pref_start_view_combo").get_model().get_value(tree_iter, 1)
        self.config["start_page"] = value

        self.config["show_all_in_search"] = self.ui.get_object("pref_show_all_check").get_active()

        self.save_config()
        self.config = self.load_config()

    def unsaved_changes(self) -> bool:
        """Check if database is in transaction"""
        return self.db.db_unsaved_changes()

    def save_config(self):
        cf = util.get_root_filename("config.json")
        util.save_config(self.config, cf)

    @staticmethod
    def load_config() -> dict:
        configfile = util.get_root_filename("config.json")
        return util.parse_config(configfile, util.DEFAULT_CONFIG)

    def save_data(self):
        util.log("Saving Data to database", util.LogLevel.Info)
        start = time.time()
        self.db.db_save_changes()
        end = time.time()
        util.log("Finished in {}s".format(str(round(end - start, 3))), util.LogLevel.Info)
        self.push_status("All data saved.")
        pass

    def load_user_data(self):
        util.log("Loading User Data from form '{}'".format(util.get_root_filename(util.DB_NAME)), util.LogLevel.Info)
        start = time.time()
        self.library = self.db.lib_get_all()
        self.tags = self.db.tag_get_all()
        self.wants = self.db.wants_get_all()
        end = time.time()
        util.log("Finished in {}s".format(str(round(end - start, 3))), util.LogLevel.Info)
        self.push_status("All data loaded.")

    def set_online(self, status: bool):
        """Online status of the application. True if no local card data is present."""
        self.ui.get_object('statusbar_icon').set_from_icon_name(util.online_icons[status], Gtk.IconSize.BUTTON)
        self.ui.get_object('statusbar_icon').set_tooltip_text(util.online_tooltips[status])
        self.config['local_db'] = not status
        self.save_config()

    def is_online(self) -> bool:
        """Return the online status of the application. True if no local data present."""
        return not self.config['local_db']

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

    def get_wanted_card_ids(self) -> List[str]:
        all_ids = []
        for cards in self.wants.values():
            next_ids = [card['multiverse_id'] for card in cards]
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

    def db_override_user_data(self):
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

    def db_delete_card_data(self):
        """Called before before rebuilding local data storage"""
        util.log("Clearing local card data", util.LogLevel.Info)
        self.db.db_clear_data_card()
        self.set_online(True)
        util.log("Done", util.LogLevel.Info)

    def db_delete_user_data(self):
        """Delete all user data"""
        util.log("Clearing all user data", util.LogLevel.Info)
        self.db.db_clear_data_user()
        util.log("Done", util.LogLevel.Info)

    def get_all_sets(self) -> dict:
        if not self.is_online():
            out = {s['code']: s for s in self.db.set_get_all()}
        else:
            out = util.load_sets(util.get_root_filename('sets'))
        return out

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
    GObject.threads_init()
    Application()
    Gtk.main()
