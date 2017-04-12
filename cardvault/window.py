import config
import handlers
import util
import search_funct
import gi
from gi.repository import Gtk
gi.require_version('Gtk', '3.0')


class MainWindow:
    def __init__(self):

        self.ui = Gtk.Builder()
        self.ui.add_from_file("gui/mainwindow.glade")
        self.ui.add_from_file("gui/overlays.glade")
        self.ui.add_from_file("gui/search.glade")
        window = self.ui.get_object("mainWindow")
        self.current_page = None
        util.app = self
        not_found = self.ui.get_object("pageNotFound")

        self.pages = {
            "search": self.ui.get_object("searchView"),
            "library": not_found,
            "decks": not_found
        }

        # Load local image Data
        util.reload_image_cache()
        util.load_mana_icons()

        util.load_sets()
        util.load_library()
        util.load_tags()

        self.handlers = handlers.Handlers(self)
        self.ui.connect_signals(self.handlers)

        search_funct.init_search_view(self)

        window.connect('delete-event', Gtk.main_quit)
        window.show_all()
        self.push_status("Card Vault ready.")

        view_menu = self.ui.get_object("viewMenu")
        start_page = [page for page in view_menu.get_children() if page.get_name() == config.start_page]
        start_page[0].activate()

    def push_status(self, msg):
        status_bar = self.ui.get_object("statusBar")
        status_bar.pop(0)
        status_bar.push(0, msg)

    def show_card_details(self, card):
        builder = Gtk.Builder()
        builder.add_from_file("gui/detailswindow.glade")
        builder.add_from_file("gui/overlays.glade")
        window = builder.get_object("cardDetails")
        window.set_title(card.name)
        # Card Image
        container = builder.get_object("imageContainer")
        pixbuf = util.load_card_image(card, 63 * 5, 88 * 5)
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
            prints.append(util.set_dict[set].name)

        builder.get_object("cardPrintings").set_text(", ".join(prints))
        # Legalities
        #builder.get_object("cardLegalities").set_text(", ".join(card.legalities))
        window.show_all()


win = MainWindow()
Gtk.main()
