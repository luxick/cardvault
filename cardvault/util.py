import copy
import enum
import json
import os
import re
from urllib import request

import gi
import six.moves.cPickle as pickle
from PIL import Image as PImage
from gi.repository import GdkPixbuf

gi.require_version('Gtk', '3.0')

from mtgsdk import Set
from mtgsdk import MtgException

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

START_PAGE = "search"

LOG_LEVEL = 1

default_config = {
    "hide_duplicates_in_search": False,
    "start_page": "search",
    "log_level": 3,
    "legality_colors": {
        "Banned": "#C65642",
        "Restricted": "#D39F30",
        "Legal": "#62B62F"
    }
}

legality_colors ={
    "Banned": "#C65642",
    "Restricted": "#D39F30",
    "Legal": "#62B62F"
}

card_view_colors ={
    "unowned": "black",
    "wanted": "#D39F30",
    "owned": "#62B62F"
}

rarity_dict = {
    "special": 0,
    "common": 1,
    "uncommon": 2,
    "rare": 3,
    "mythic rare": 4
}
card_types = ["Creature", "Artifact", "Instant", "Enchantment", "Sorcery", "Land", "Planeswalker"]


class LogLevel(enum.Enum):
    Error = 1
    Warning = 2
    Info = 3


def log(message, log_level):
    if log_level.value <= LOG_LEVEL:
        level_string = "[" + log_level.name + "] "
        print(level_string + message)


def parse_config(filename, default):
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


def save_config(config_dict, filename):
    path = os.path.dirname(filename)
    if not os.path.isdir(path):
        os.mkdir(path)

    with open(filename, 'wb') as configfile:
        configfile.write(json.dumps(config_dict, sort_keys=True,
                  indent=4, separators=(',', ': ')).encode('utf-8'))


def get_root_filename(filename):
    return os.path.expanduser(os.path.join('~', '.cardvault', filename))

def get_ui_filename(filename):
    return os.path.expanduser(os.path.join(os.path.dirname(__file__), 'gui', filename))


def reload_image_cache(path):
    cache = {}
    if not os.path.isdir(path):
        os.mkdir(path)
    imagefiles = os.listdir(path)
    for imagefile in imagefiles:
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(path + imagefile)
            # Strip filename extension
            imagename = os.path.splitext(imagefile)[0]
            cache[imagename] = pixbuf
        except OSError as err:
            log("Error loading image: " + str(err), LogLevel.Error)
    return cache


def reload_preconstructed_icons(path):
    cache = {}
    if not os.path.exists(path):
        os.makedirs(path)

    iconfiles = os.listdir(path)
    for file in iconfiles:
        # Split filename into single icon names and remove extension
        without_ext = file.split(".")[0]
        list = without_ext.split("_")
        # Compute size of the finished icon
        pic_width = len(list) * 105
        pic_height = 105
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(ICON_CACHE_PATH + file)
            pixbuf = pixbuf.scale_simple(pic_width / 5, pic_height / 5, GdkPixbuf.InterpType.HYPER)
            # Set name for icon
            iconname = "_".join(list)
            cache[iconname] = pixbuf
        except OSError as err:
            log("Error loading image: " + str(err), LogLevel.Error)
    return cache


def load_mana_icons(path):
    if not os.path.exists(path):
        log("Directory for mana icons not found " + path, LogLevel.Error)
        return
    icons = {}
    filenames = os.listdir(path)
    for file in filenames:
        img = PImage.open(path + file)
        # Strip file extension
        name = os.path.splitext(file)[0]
        icons[name] = img
    return icons


def load_sets(filename):
    if not os.path.isfile(filename):
        # use mtgsdk api to retrieve al list of all sets
        try:
            sets = Set.all()
        except MtgException as err:
            log(str(err), LogLevel.Error)
            return
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


def import_library(path):
    try:
        imported = pickle.load(open(path, 'rb'))
    except pickle.UnpicklingError as err:
        log(str(err) + " while importing", LogLevel.Error)
        return
    # Parse imported file
    try:
        library = imported["library"]
        tags = imported["tags"]
    except KeyError as err:
        log("Invalid library format " + str(err), LogLevel.Error)
        library = {}
        tags = {}

    log("Library imported", LogLevel.Info)
    return (library, tags)


def save_file(path, file):
    # Serialize using cPickle
    try:
        pickle.dump(file, open(path, 'wb'))
    except OSError as err:
        log(str(err), LogLevel.Error)
        return
    log("Saved file " + path, LogLevel.Info)


def load_file(path):
    if not os.path.isfile(path):
        log(path + " does not exist", LogLevel.Warning)
        return
    try:
        loaded = pickle.load(open(path, 'rb'))
    except OSError as err:
        log(str(err), LogLevel.Error)
        return
    return loaded


def load_dummy_image(sizex, sizey):
    return GdkPixbuf.Pixbuf.new_from_file_at_size(os.path.dirname(__file__)
                                                  + '/resources/images/dummy.jpg', sizex, sizey)


def load_card_image_online(card, sizex, sizey):
    url = card.image_url
    if url is None:
        log("No Image URL for " + card.name, LogLevel.Warning)
        return load_dummy_image(sizex, sizey)
    filename = IMAGE_CACHE_PATH + str(card.multiverse_id) + ".png"
    request.urlretrieve(url, filename)
    return GdkPixbuf.Pixbuf.new_from_file_at_size(filename, sizex, sizey)


def create_mana_icons(icon_dict, mana_string):
    # Convert the string to a List
    safe_string = mana_string.replace("/", "-")
    list = re.findall("{(.*?)}", safe_string)
    if len(list) == 0:
        return
    # Compute horizontal size for the final image
    imagesize = len(list) * 105
    image = PImage.new("RGBA", (imagesize, 105))
    # incerment for each position of an icon (Workaround: 2 or more of the same icon will be rendered in the same poisition)
    poscounter = 0
    # Go through all entries an add the correspondent icon to the final image
    for icon in list:
        xpos = poscounter * 105
        try:
            loaded = icon_dict[icon]
        except KeyError as err:
            log("No icon file named '" + icon + "' found.", LogLevel.Warning)
            return
        image.paste(loaded, (xpos, 0))
        poscounter += 1
    # Save Icon file
    path = ICON_CACHE_PATH + "_".join(list) + ".png"
    image.save(path)
    try:
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
        pixbuf = pixbuf.scale_simple(image.width / 5, image.height / 5, GdkPixbuf.InterpType.HYPER)
    except:
        return
    return pixbuf

# endregion

