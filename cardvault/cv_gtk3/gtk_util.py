import os
import re

from gi.repository import GdkPixbuf
from zipfile import ZipFile

try:
    from PIL import Image
except ImportError as err:
    print('PIL imaging library is not installed')

from cv_core.util import CoreConfig


class GTKUtilities:
    """ Access to image caches and utilities for use in the GTK application """
    # Loaded mana symbols Format: {'B': GDKPixbuf, '3': GDKPixbuf}
    mana_icons = {}
    # Cache for combined mana cost icons
    precon_icon_cache = {}
    # Path of Gtk resources relative to cardvault base package
    resources_path = os.path.join('cv_gtk3', 'resources')

    @staticmethod
    def get_path_from_base_dir(*dirs):
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), *dirs)

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
        image = Image.new("RGBA", (size, 105))
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
        path = os.path.join(CoreConfig.icon_cache_path, "_".join(glyphs) + ".png")
        image.save(path)
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
        except Exception as ex:
            print(ex)
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
        im = Image.frombytes(mode, (w, h), data, "raw", mode, stride)

        return im

    @staticmethod
    def load_ui_resource(resource_name):
        """ Load GUI resource depending on the execution mode (from a directory or from a zip file)
        :param resource_name: Name of the glade file
        :return: String content of the resource file
        """
        if os.path.isdir(os.path.dirname(__file__)):
            return GTKUtilities.load_ui_resource_file(os.path.join(GTKUtilities.resources_path, 'gui',  resource_name))
        else:
            zip_path = os.path.dirname(os.path.dirname(__file__))
            return GTKUtilities.load_ui_resource_zip(zip_path,
                                                     os.path.join(GTKUtilities.resources_path, 'gui',  resource_name))

    @staticmethod
    def load_ui_resource_file(resource_path):
        """ LOad GUI resource from file path
        :param resource_path: Relative path of the resource based on the cardvault base package
        :return: String content of the resource file
        """
        full_path = GTKUtilities.get_path_from_base_dir(resource_path)
        with open(full_path, 'r') as file:
            return file.read()

    @staticmethod
    def load_ui_resource_zip(archive_file, resource_path):
        """ Load GUI resource from a zip archive (for usage in release mode)
        :param archive_file: Full path of the archive file
        :param resource_path: Path of the resources within the archive
        :return: String representation of the file content
        """
        with ZipFile(archive_file, 'r') as archive:
            return archive.read(resource_path).decode('utf-8')

    @staticmethod
    def load_icon_cache(icon_path):
        """ Get a dictionary with all available mana icons
        :param icon_path: Relative path of icon resource files
        :return: Dict with icon names and Gdkpixbuf objects
        """
        if os.path.isdir(GTKUtilities.get_path_from_base_dir(icon_path)):
            return GTKUtilities.load_icon_cache_file(GTKUtilities.get_path_from_base_dir(icon_path))
        else:
            zip_path = os.path.dirname(os.path.dirname(__file__))
            return GTKUtilities.load_icon_cache_zip(zip_path)

    @staticmethod
    def load_icon_cache_file(icon_path):
        """ Load icon cache from absolute paths at file system
        :param icon_path: Relative path of icon resource files
        :return: Dict with icon names and Gdkpixbuf object
        """
        icons = {}
        files = os.listdir(icon_path)
        for file in files:
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(os.path.join(icon_path, file))
                # Strip filename extension
                icon_name = os.path.splitext(file)[0]
                icons[icon_name] = pixbuf
            except Exception as ex:
                print('Error while loading icon file "{}"'.format(ex))
        return icons

    @staticmethod
    def load_icon_cache_zip(zip_path):
        """ Load icon cache from zipped archive
        :param zip_path: Full path of the zip archive
        :return: Dict with icon names and Gdkpixbuf object
        """
        with ZipFile(zip_path, 'r') as archive:
            icon_path = os.path.join('cv_gtk3', 'resources', 'mana')
            files = [path for path in archive.namelist() if os.path.isfile(path.startswith(icon_path))]
            icons = {}
            for file in files:
                with archive.open(file) as data:
                    try:
                        loader = GdkPixbuf.PixbufLoader()
                        loader.write(data.read())
                        pixbuf = loader.get_pixbuf()
                        loader.close()
                        # Strip filename extension
                        icon_name = os.path.splitext(file)[0]
                        icons[icon_name] = pixbuf
                    except Exception as ex:
                        print('Error while loading icon file "{0}"\n{1}'.format(file, ex))
            return icons

