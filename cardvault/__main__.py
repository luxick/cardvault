import sys

import os.path
path = os.path.realpath(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(path))

from cv_gtk3 import gtk_ui

if __name__ == '__main__':
    gtk_ui.main()