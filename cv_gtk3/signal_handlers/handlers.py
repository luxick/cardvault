from cv_gtk3.signal_handlers.menu_bar import MenuBarHandlers
from cv_gtk3.signal_handlers.search import SearchPageHandlers


class Handlers(MenuBarHandlers, SearchPageHandlers):
    """ Class containing all signal handlers for the GTK GUI """
    def __init__(self, app):
        """ Initialize handler class
        :param app: reference to an CardvaultGTK object
        """
        self.app = app
        # Call constructors of superclasses
        MenuBarHandlers.__init__(self, self.app)
        SearchPageHandlers.__init__(self, self.app)
