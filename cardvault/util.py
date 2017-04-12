import os
import datetime
import gi
import re
import config
import network
from gi.repository import GdkPixbuf, Gtk
from PIL import Image as PImage
from urllib import request
import six.moves.cPickle as pickle
gi.require_version('Gtk', '3.0')


# Locally stored images for faster loading times
imagecache = {}
manaicons = {}
set_list = []
set_dict = {}

# Card library object
library = {}
# Dictionary for tagged cards
tags = {}

status_bar = None
app = None
unsaved_changes = False

rarity_dict = {
    "special": 0,
    "common": 1,
    "uncommon": 2,
    "rare": 3,
    "mythic rare": 4
}
card_types = ["Creature", "Artifact", "Instant", "Enchantment", "Sorcery", "Land", "Planeswalker"]

def export_library():
    dialog = Gtk.FileChooserDialog("Export Library", app.ui.get_object("mainWindow"),
                                   Gtk.FileChooserAction.SAVE,
                                   (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                    Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
    dialog.set_current_name("mtg_export-" + datetime.datetime.now().strftime("%Y-%m-%d"))
    dialog.set_current_folder(os.path.expanduser("~"))
    response = dialog.run()
    if response == Gtk.ResponseType.OK:
        try:
            pickle.dump(library, open(dialog.get_filename(), 'wb'))
        except:
            show_message("Error", "Error while saving library to disk")
        app.push_status("Library exported to \"" + dialog.get_filename() + "\"")
        print("Library exported to \"", dialog.get_filename() + "\"")
    dialog.destroy()


def import_library():
    dialog = Gtk.FileChooserDialog("Import Library", app.ui.get_object("mainWindow"),
                                   Gtk.FileChooserAction.OPEN,
                                   (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                    Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
    dialog.set_current_folder(os.path.expanduser("~"))
    response = dialog.run()
    if response == Gtk.ResponseType.OK:
        override_question = show_question_dialog("Import Library",
                                                 "Importing a library will override your current library. "
                                                 "Proceed?")
        if override_question == Gtk.ResponseType.YES:
            imported = pickle.load(open(dialog.get_filename(), 'rb'))
            library.clear()
            for id, card in imported.items():
                library[id] = card
            save_library()
            app.push_status("Library imported")
            print("Library imported")
    dialog.destroy()


def save_library():
    if not os.path.exists(config.cache_path):
        os.makedirs(config.cache_path)
    lib_path = config.cache_path + "library"
    tag_path = config.cache_path + "tags"

    # Serialize library object using pickle
    try:
        pickle.dump(library, open(lib_path, 'wb'))
        pickle.dump(tags, open(tag_path, 'wb'))
    except:
        show_message("Error", "Error while saving library to disk")
        return

    global unsaved_changes
    unsaved_changes = False
    app.push_status("Library saved.")


def load_library():
    lib_path = config.cache_path + "library"
    library.clear()

    if os.path.isfile(lib_path):
        # Deserialize using pickle
        try:
            library_loaded = pickle.load(open(lib_path, 'rb'))
            for id, card in library_loaded.items():
                library[id] = card
        except :
            show_message("Error", "Error while loading library from disk")
    else:
        save_library()
        print("No library file found, created new one")


def load_tags():
    tag_path = config.cache_path + "tags"
    tags.clear()
    if not os.path.isfile(tag_path):
        save_library()
        print("No tags file found, created new one")
    try:
        tags_loaded = pickle.load(open(tag_path, 'rb'))
        for tag, ids in tags_loaded.items():
            tags[tag] = ids
    except:
        show_message("Error", "Error while loading library from disk")


def load_sets():
    path = config.cache_path + "sets"
    if not os.path.isfile(path):
        # use mtgsdk api to retrieve al list of all sets
        new_sets = network.net_load_sets()
        if new_sets == "":
            show_message("API Error", "Could not retrieve Set infos")
            return
        # Serialize the loaded data to a file
        pickle.dump(new_sets, open(path, 'wb'))
    # Deserialize set data from local file
    sets = pickle.load(open(path, 'rb'))
    # Sort the loaded sets based on the sets name
    for set in sorted(sets, key=lambda x: x.name):
        set_list.append(set)
        set_dict[set.code] = set


def reload_image_cache():
    if not os.path.exists(config.image_cache_path):
        os.makedirs(config.image_cache_path)

    # return array of images
    imageslist = os.listdir(config.image_cache_path)
    imagecache.clear()
    for image in imageslist:
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(config.image_cache_path + image)
            imagecache[image] = pixbuf
        except OSError as err:
            print("Error loading image: " + str(err))

# endregion


def add_tag(tag):
    tags[tag] = {}
    app.push_status("Added Tag \"" + tag + "\"")
    global unsaved_changes
    unsaved_changes = True


def remove_tag(tag):
    tags[tag] = None
    app.push_status("Removed Tag \"" + tag + "\"")
    global unsaved_changes
    unsaved_changes = True


def add_card_to_lib(card):
    library[card.multiverse_id] = card
    app.push_status(card.name + " added to library")
    global unsaved_changes
    unsaved_changes = True


def remove_card_from_lib(card):
    del library[card.multiverse_id]
    app.push_status(card.name + " removed from library")
    global unsaved_changes
    unsaved_changes = True

def show_question_dialog(title, message):
    dialog = Gtk.MessageDialog(app.ui.get_object("mainWindow"), 0, Gtk.MessageType.QUESTION,
                               Gtk.ButtonsType.YES_NO, title)
    dialog.format_secondary_text(message)
    response = dialog.run()
    dialog.destroy()
    return response


def show_message(title, message):
    dialog = Gtk.MessageDialog(app.ui.get_object("mainWindow"), 0, Gtk.MessageType.INFO,
                               Gtk.ButtonsType.OK, title)
    dialog.format_secondary_text(message)
    dialog.run()
    dialog.destroy()


def load_mana_icons():
    path = os.path.dirname(__file__) + "/resources/mana/"
    if not os.path.exists(path):
        print("ERROR: Directory for mana icons not found")
        return
    # return array of icons
    imagelist = os.listdir(path)
    manaicons.clear()
    for image in imagelist:
        img = PImage.open(path + image)
        manaicons[os.path.splitext(image)[0]] = img


def load_dummy_image(sizex, sizey):
    return GdkPixbuf.Pixbuf.new_from_file_at_size(os.path.dirname(__file__)
                                                  + '/resources/images/dummy.jpg', sizex, sizey)


def load_card_image_online(card, sizex, sizey):
    url = card.image_url
    if url is None:
        print("No Image URL provided")
        return load_dummy_image(sizex, sizey)
    filename = config.image_cache_path + card.multiverse_id.__str__() + ".PNG"
    print("Loading image for " + card.name + "from: " + url)
    request.urlretrieve(url, filename)
    reload_image_cache()
    return GdkPixbuf.Pixbuf.new_from_file_at_size(filename, sizex, sizey)


def load_card_image(card, sizex, sizey):
    # Try loading from disk, if file exists
    filename = str(card.multiverse_id) + ".PNG"
    if imagecache.__contains__(filename):
        pixbuf = imagecache[filename]
        return pixbuf.scale_simple(sizex, sizey, GdkPixbuf.InterpType.BILINEAR)
    else:
        return load_card_image_online(card, sizex, sizey)


def create_mana_icons(mana_string):
    # Convert the string to a List
    list = re.findall("{(.*?)}", str(mana_string))
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
        loaded = manaicons.get(icon.replace("/", ""))
        if loaded is None:
            print("ERROR: No icon file named \"" + icon + "\" found.")
        else:
            image.paste(loaded, (xpos, 0))
        poscounter += 1
    filename = "icon.png"
    path = config.cache_path + filename
    image.save(path)
    try:
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
        pixbuf = pixbuf.scale_simple(image.width / 5, image.height / 5, GdkPixbuf.InterpType.HYPER)
    except:
        return
    # os.remove(path)
    return pixbuf
