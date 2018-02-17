import re
import os
from gi.repository import GdkPixbuf
try:
    from PIL import Image as PImage
except ImportError as err:
    print('PIL imaging library is not installed')

from cv_engine.util import EngineConfig


class GTKUtilities:
    """ Access to image caches and utilities for use in the GTK application """
    # Loaded mana symbols Format: {'B': GDKPixbuf, '3': GDKPixbuf}
    mana_icons = {}
    # Cache for combined mana cost icons
    precon_icon_cache = {}

    @staticmethod
    def get_mana_icons(mana_string):
        """ Return the combined mana symbols for a mana string
        :param mana_string: String in the format '{3}{U}{B}'
        :return: GdkPixbuf containing the combined symbols
        """
        if not mana_string:
            return
        icon_list = re.findall("{(.*?)}", mana_string.replace("/", "-"))
        icon_name = "_".join(icon_list)
        try:
            icon = GTKUtilities.precon_icon_cache[icon_name]
        except KeyError:
            icon = GTKUtilities.create_mana_icons(mana_string)
            GTKUtilities.precon_icon_cache[icon_name] = icon
        return icon

    @staticmethod
    def create_mana_icons(mana_string):
        # Convert the string to a List
        glyphs = re.findall("{(.*?)}", mana_string)
        if len(glyphs) == 0:
            return
        # Compute horizontal size for the final image
        size = len(glyphs) * 105
        image = PImage.new("RGBA", (size, 105))
        for icon in glyphs:
            x_pos = glyphs.index(icon) * 105
            try:
                loaded = GTKUtilities.mana_icons[icon]
            except KeyError:
                return
            image.paste(loaded, (x_pos, 0))
        # Save pre build icon file
        path = os.path.join(EngineConfig.icon_cache_path, "_".join(glyphs) + ".png")
        image.save(path)
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
            pixbuf = pixbuf.scale_simple(image.width / 5, image.height / 5, GdkPixbuf.InterpType.HYPER)
        except Exception as err:
            print(err)
            return
        return pixbuf