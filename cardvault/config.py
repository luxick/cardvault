import gi
import os
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk


# Title of the Program Window
application_title = "Card Vault v0.5"

# Path of image cache
cache_path = os.path.dirname(__file__) + "/.cache/"
image_cache_path = os.path.dirname(__file__) + "/.cache/images/"
icon_cache_path = os.path.dirname(__file__) + "/.cache/icons/"

# Colors to use in the Application
green_color = Gdk.color_parse('#87ff89')
red_color = Gdk.color_parse('#ff6d6d')

# When True Search view will list a card multiple times for each set they appear in
show_from_all_sets = True

start_page = "search"

log_level = 3
