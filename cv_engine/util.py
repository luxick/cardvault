import json
import os

from cv_engine.models import Card


class EngineConfig:
    """
    Configuration class for the Cardvault engine
    Defines default values for all settings
    Should be changed at runtime to load customized settings
    """
    # Should cv_engine show duplicate names in searches
    duplicate_names_in_search = True
    # Log level for cv_engine
    log_level = 0
    # Name of the database file
    db_file = 'cardvault.db'
    # Default path to store temporary files
    cache_path = os.path.join(os.path.expanduser('~'), '.cache', 'cardvault')
    # Icon cache path
    icon_cache_path = os.path.join(os.path.expanduser('~'), '.cache', 'cardvault', 'icons')


class EngineConstants:
    """
    Constants of cv_engine
    Contains version number, application infos, etc.
    """
    # Version of the cardvault engine
    engine_version = 0.1
    # Location of manual wiki
    manual_location = 'https://github.com/luxick/cardvault'
    # Default path of cardvault configuration file
    config_path = os.path.join(os.path.expanduser('~'), '.config', 'cardvault')


class GTKConstants:
    """
    Constants for the GTK Ui
    """
    # Directory in witch glade ui files are stored
    glade_files = '/gui'


class MTGConstants:
    """
    This class contains constants that can be used within the whole program
    Included are for example the the official color order or rarities
    """
    # Color order for mana symbols
    mana_order = ('W', 'U', 'B', 'R', 'G')
    # All card types that can be used by the application
    card_types = ("Creature", "Artifact", "Instant", "Enchantment", "Sorcery", "Land", "Planeswalker")
    # Order of card rarities
    rarities = ('special', 'common', 'uncommon', 'rare', 'mythic rare')
    # URL for card images. Insert card.multiverse_id.
    card_image_url_base = 'http://gatherer.wizards.com/Handlers/Image.ashx?multiverseid={}&type=card'
    # Abbreviated version of all card colors
    color_shorthands = {
        'White': 'W',
        'Blue': 'U',
        'Black': 'B',
        'Red': 'R',
        'Green': 'G'
    }


class Utilities:
    """
    The class offers methods for general usage thorough the program.
    """
    @staticmethod
    def apply_config(filename):
        """
        Load the supplied configuration and apply it to the EngineConfig class.
        :param filename: Path to a json formatted cardvault config file.
        """
        with open(filename) as config_file:
            config = json.load(config_file)
            for setting, value in config.items():
                EngineConfig.__dict__[setting] = value

    @staticmethod
    def parse_mtgjson_cards(json_data):
        """
        Parse a json object to
        :param json_data:
        """
        output = []
        for data in json_data.values():
            cards = []
            for raw in data["cards"]:
                c = Card(raw)
                c.image_url = MTGConstants.card_image_url_base.format(c.multiverse_id)
                c.set = data["code"]
                c.set_name = data["name"]
                cards.append(c)
            output = output + cards
        return output

    @staticmethod
    def expand_file_path(base_file, sub_dirs) -> str:
        """
        Get absolute file path relative to another file
        :param base_file: Current file from witch to expand
        :param sub_dirs: List of sub directories to desired file
        :return: Full file path of chosen file
        """
        return os.path.join(os.path.dirname(base_file), *sub_dirs)