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
    def load_icon_cache(path):
        icons = {}
        if not os.path.isdir(path):
            os.mkdir(path)
        files = os.listdir(path)
        for file in files:
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(os.path.join(path, file))
                # Strip filename extension
                icon_name = os.path.splitext(file)[0]
                icons[icon_name] = pixbuf
            except Exception as ex:
                print('Error while loading icon file "{}"'.format(ex))
        return icons

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
        # Scale icon for display
        if icon:
            icon = icon.scale_simple(icon.get_width() / 5, icon.get_height() / 5, GdkPixbuf.InterpType.HYPER)
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
        for index, icon in enumerate(glyphs):
            x_pos = index * 105
            try:
                # Try loading mana icon and converting to PIL.Image for combining
                loaded = GTKUtilities.pixbuf_to_image(GTKUtilities.mana_icons[icon])
            except KeyError:
                print('Mana icon "{}" is not loaded.'.format(icon))
                return
            image.paste(loaded, (x_pos, 0))
        # Save pre build icon file
        path = os.path.join(EngineConfig.icon_cache_path, "_".join(glyphs) + ".png")
        image.save(path)
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
        except Exception as err:
            print(err)
            return
        return pixbuf

    @staticmethod
    def pixbuf_to_image(pix):
        """Convert gdkpixbuf to PIL image"""
        data = pix.get_pixels()
        w = pix.props.width
        h = pix.props.height
        stride = pix.props.rowstride
        mode = "RGB"
        if pix.props.has_alpha:
            mode = "RGBA"
        im = PImage.frombytes(mode, (w, h), data, "raw", mode, stride)

        return im