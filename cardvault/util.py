import copy
import enum
import json
import os
import re
import sys
import six.moves.cPickle as pickle
from time import localtime, strftime, time
from PIL import Image as PImage
import urllib.request
from urllib import request
from mtgsdk import Set, Card, MtgException

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GdkPixbuf, GLib


# Title of the Program Window
APPLICATION_TITLE = "Card Vault"

# Program version
VERSION = "0.5.0"

# Path of image cache
CACHE_PATH = os.path.expanduser('~') + "/.cardvault/"
IMAGE_CACHE_PATH = os.path.expanduser('~') + "/.cardvault/images/"
ICON_CACHE_PATH = os.path.expanduser('~') + "/.cardvault/icons/"

# When True Search view will list a card multiple times for each set they appear in
SHOW_FROM_ALL_SETS = True

# First page to show after startup
START_PAGE = "search"

# Log level of the application
# 1 Info
# 2 Warning
# 3 Error
LOG_LEVEL = 1

# Name of the database
DB_NAME = "cardvault.db"

ALL_NUM_URL = 'https://api.magicthegathering.io/v1/cards?page=0&pageSize=100'

ALL_SETS_JSON_URL = 'https://mtgjson.com/json/AllSets-x.json'

# URL for card images. Insert card.multiverse_id.
CARD_IMAGE_URL = 'http://gatherer.wizards.com/Handlers/Image.ashx?multiverseid={}&type=card'

# Colors for card rows in search view
SEARCH_TREE_COLORS = {
    "unowned": "black",
    "wanted": "#D39F30",
    "owned": "#62B62F"
}

# Colors for card rows in every default view
GENERIC_TREE_COLORS = {
    "unowned": "black",
    "wanted": "black",
    "owned": "black"
}

default_config = {
    "hide_duplicates_in_search": False,
    "start_page": "search",
    "local_db": False,
    "log_level": 3,
    "legality_colors": {
        "Banned": "#C65642",
        "Restricted": "#D39F30",
        "Legal": "#62B62F"
    }
}

legality_colors = {
    "Banned": "#C65642",
    "Restricted": "#D39F30",
    "Legal": "#62B62F"
}

card_colors = {
            'White': 'W',
            'Blue': 'U',
            'Black': 'B',
            'Red': 'R',
            'Green': 'G'
        }

color_sort_order = {
    'W': 0,
    'U': 1,
    'B': 2,
    'R': 3,
    'G': 4
}

rarity_dict = {
    "special": 0,
    "common": 1,
    "uncommon": 2,
    "rare": 3,
    "mythic rare": 4
}
card_types = ["Creature", "Artifact", "Instant", "Enchantment", "Sorcery", "Land", "Planeswalker"]

online_icons = {
    True: 'network-wired',
    False: 'drive-harddisk'
}

online_tooltips = {
    True: 'Using online card data',
    False: 'Using card data from local database.'
}


class LogLevel(enum.Enum):
    Error = 1
    Warning = 2
    Info = 3


class TerminalColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def log(msg: str, ll: LogLevel):
    if ll.value <= LOG_LEVEL:
        lv = "[" + ll.name + "] "
        if ll.value == 2:
            c = TerminalColors.WARNING
        elif ll.value == 1:
            c = TerminalColors.BOLD + TerminalColors.FAIL
        else:
            c = ""
        tc = strftime("%H:%M:%S ", localtime())
        print(c + lv + tc + msg + TerminalColors.ENDC)


def parse_config(filename: str, default: dict):
    config = copy.copy(default)
    try:
        with open(filename) as configfile:
            loaded_config = json.load(configfile)
            if 'legality_colors' in config and 'legality_colors' in loaded_config:
                # Need to prevent nested dict from being overwritten with an incomplete dict
                config['legality_colors'].update(loaded_config['legality_colors'])
                loaded_config['legality_colors'] = config['legality_colors']
            config.update(loaded_config)
    except IOError:
        # Will just use the default config
        # and create the file for manual editing
        save_config(config, filename)
    except ValueError:
        # There's a syntax error in the config file
        log("Syntax error wihle parsing config file", LogLevel.Error)
        return
    return config


def save_config(config: dict, filename: str):
    path = os.path.dirname(filename)
    if not os.path.isdir(path):
        os.mkdir(path)

    with open(filename, 'wb') as configfile:
        configfile.write(json.dumps(config, sort_keys=True,
                                    indent=4, separators=(',', ': ')).encode('utf-8'))


def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def get_root_filename(filename: str) -> str:
    return os.path.expanduser(os.path.join('~', '.cardvault', filename))


def get_ui_filename(filename: str) -> str:
    return os.path.join(os.path.dirname(__file__), 'gui', filename)


def reload_image_cache(path: str) -> dict:
    cache = {}
    if not os.path.isdir(path):
        os.mkdir(path)
    imagefiles = os.listdir(path)
    for imagefile in imagefiles:
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(path + imagefile)
            # Strip filename extension
            imagename = os.path.splitext(imagefile)[0]
            cache[int(imagename)] = pixbuf
        except OSError as err:
            log("Error loading image: " + str(err), LogLevel.Error)
        except GLib.GError as err:
            log("Error loading image: " + str(err), LogLevel.Error)
    return cache


def reload_preconstructed_icons(path: str) -> dict:
    cache = {}
    if not os.path.exists(path):
        os.makedirs(path)

    files = os.listdir(path)
    for file in files:
        # Split filename into single icon names and remove extension
        without_ext = file.split(".")[0]
        names = without_ext.split("_")
        # Compute size of the finished icon
        pic_width = len(names) * 105
        pic_height = 105
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(ICON_CACHE_PATH + file)
            pixbuf = pixbuf.scale_simple(pic_width / 5, pic_height / 5, GdkPixbuf.InterpType.HYPER)
            # Set name for icon
            iconname = "_".join(names)
            cache[iconname] = pixbuf
        except OSError as err:
            log("Error loading image: " + str(err), LogLevel.Error)
    return cache


def load_mana_icons(path: str) -> dict:
    if not os.path.exists(path):
        log("Directory for mana icons not found " + path, LogLevel.Error)
        return {}
    icons = {}
    files = os.listdir(path)
    for file in files:
        img = PImage.open(path + file)
        # Strip file extension
        name = os.path.splitext(file)[0]
        icons[name] = img
    return icons


def net_all_cards_mtgjson() -> dict:
    with urllib.request.urlopen(ALL_SETS_JSON_URL) as url:
        data = json.loads(url.read().decode())
        return data


def net_load_set_list() -> dict:
    """ Load the list of all MTG sets from the Gather"""
    try:
        start = time()
        sets = Set.all()
        stop = time()
        log("Fetched set list in {}s".format(round(stop - start, 3)), LogLevel.Info)
    except MtgException as err:
        log(str(err), LogLevel.Error)
        return {}
    return sets


def load_sets(filename: str) -> dict:
    """
    Load sets from local file if possible.
    Called by: Application if in online mode
    """
    if not os.path.isfile(filename):
        # use mtgsdk api to retrieve al list of all sets
        sets = net_load_set_list()
        # Serialize the loaded data to a file
        pickle.dump(sets, open(filename, 'wb'))
    # Deserialize set data from local file
    sets = pickle.load(open(filename, 'rb'))
    # Sort the loaded sets based on the sets name
    output = {}
    for set in sorted(sets, key=lambda x: x.name):
        output[set.code] = set
    return output


def export_library(path, file):
    try:
        pickle.dump(file, open(path, 'wb'))
        log("Library exported to \"" + path + "\"", LogLevel.Info)
    except OSError as err:
        log(str(err), LogLevel.Error)


def import_library(path: str) -> ():
    try:
        imported = pickle.load(open(path, 'rb'))
    except pickle.UnpicklingError as err:
        log(str(err) + " while importing", LogLevel.Error)
        return
    # Parse imported file
    try:
        library = imported["library"]
        tags = imported["tags"]
        wants = imported["wants"]
    except KeyError as err:
        log("Invalid library format " + str(err), LogLevel.Error)
        library = {}
        tags = {}
        wants = {}

    log("Library imported", LogLevel.Info)
    return library, tags, wants


def save_file(path, file):
    # Serialize using cPickle
    try:
        pickle.dump(file, open(path, 'wb'))
    except OSError as err:
        log(str(err), LogLevel.Error)
        return
    log("Saved file " + path, LogLevel.Info)


def load_file(path: str):
    if not os.path.isfile(path):
        log(path + " does not exist", LogLevel.Warning)
        return
    try:
        loaded = pickle.load(open(path, 'rb'))
    except OSError as err:
        log(str(err), LogLevel.Error)
        return
    return loaded


def load_dummy_image(size_x: int, size_y: int) -> GdkPixbuf:
    return GdkPixbuf.Pixbuf.new_from_file_at_size(os.path.dirname(__file__)
                                                  + '/resources/images/dummy.jpg', size_x, size_y)


def load_card_image(card: Card, size_x: int, size_y: int, cache: dict) -> GdkPixbuf:
    """ Retrieve an card image from cache or alternatively load from gatherer"""
    try:
        image = cache[card.multiverse_id]
    except KeyError:
        log("No local image for " + card.name + ". Loading from " + card.image_url, LogLevel.Info)
        filename, image = net_load_card_image(card, size_x, size_y)
        cache[card.multiverse_id] = image
    return image


def net_load_card_image(card, size_x: int, size_y: int) -> (str, GdkPixbuf):
    url = card.image_url
    if url is None:
        log("No Image URL for " + card.name, LogLevel.Warning)
        return load_dummy_image(size_x, size_y)
    filename = IMAGE_CACHE_PATH + str(card.multiverse_id) + ".png"
    request.urlretrieve(url, filename)
    return filename, GdkPixbuf.Pixbuf.new_from_file_at_size(filename, size_x, size_y)


def create_mana_icons(icons: dict, mana_string: str) -> GdkPixbuf:
    # Convert the string to a List
    safe_string = mana_string.replace("/", "-")
    glyphs = re.findall("{(.*?)}", safe_string)
    if len(glyphs) == 0:
        return
    # Compute horizontal size for the final image
    size = len(glyphs) * 105
    image = PImage.new("RGBA", (size, 105))
    # Increment for each position of an icon
    # (Workaround: 2 or more of the same icon will be rendered in the same position)
    c = 0
    # Go through all entries an add the correspondent icon to the final image
    for icon in glyphs:
        x_pos = c * 105
        try:
            loaded = icons[icon]
        except KeyError:
            log("No icon file named '" + icon + "' found.", LogLevel.Warning)
            return
        image.paste(loaded, (x_pos, 0))
        c += 1
    # Save Icon file
    path = ICON_CACHE_PATH + "_".join(glyphs) + ".png"
    image.save(path)
    try:
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
        pixbuf = pixbuf.scale_simple(image.width / 5, image.height / 5, GdkPixbuf.InterpType.HYPER)
    except:
        return
    return pixbuf


def unique_list(seq):
    seen = set()
    seen_add = seen.add
    return [x for x in seq if not (x in seen or seen_add(x))]


def sizeof_fmt(num, suffix='B'):
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def get_all_cards_num() -> int:
    req = urllib.request.Request(ALL_NUM_URL, headers={'User-Agent': 'Mozilla/5.0'})
    response = urllib.request.urlopen(req)
    headers = response.info()._headers
    for header, value in headers:
        if header == 'Total-Count':
            return int(value)
