from cv_gtk3.setting import GUISettings


class MainWindowFunctions:
    """
    Class for holding general functions of the main window container
    such as controlling the status and menu bar .
    """
    def __init__(self, ui):
        self.ui = ui

    def hide_initial_widgets(self):
        self.ui.get_object('statusbar_spinner').set_visible(False)
        self.ui.get_object('statusbar_label').set_visible(False)

    def show_status(self, message):
        """
        Display a massage in the status bar alon with an animated spinner
        :param message: The text to display
        """
        spinner = self.ui.get_object('statusbar_spinner')
        label = self.ui.get_object('statusbar_label')
        spinner.set_visible(True)
        label.set_visible(True)
        label.set_text(message)

    def clear_status(self):
        """
        Hides the message an spinner in the status bar
        """
        self.ui.get_object('statusbar_spinner').set_visible(False)
        self.ui.get_object('statusbar_label').set_visible(False)

    def switch_page(self, page):
        """
        Switch active page
        :param page: name of the new page
        """
        container = self.ui.get_object("contentPage")
        new_page = GUISettings.pages[page]
        if GUISettings.current_page:
            container.remove(GUISettings.current_page)
        GUISettings.current_page = new_page
        container.pack_start(GUISettings.current_page, True, True, 0)
        container.show_all()
        GUISettings.current_page.emit('show')
        app_title = GUISettings.current_page.get_name() + " - " +GUISettings.application_title
        self.ui.get_object("mainWindow").set_title(app_title)