import os
import itertools

from cv_core.database import CardvaultDB
from cv_core.util import CoreConfig, CoreConstants, CoreUtilities


class CardvaultEngine:
    def __init__(self, config_file=False):
        """ Create a new cv_core instance
        :param config_file: File path of the configuration file
        """
        if config_file:
            CoreUtilities.apply_config(config_file)
        db_file_path = os.path.join(CoreConstants.config_path, CoreConfig.db_file)
        self.database = CardvaultDB(db_file_path)

    def get_card(self, card_id):
        """ Load a card object from database
        :param card_id: multiverse id of a card
        :return: an cv_core.model.Card object
        """
        return self.database.card_load(card_id)

    def get_library(self) -> list:
        """ Get the complete library of cards
        :return: Alphabetically ordered list of all cards in library
        """
        return self.database.lib_get_all()

    def get_all_categories(self) -> dict:
        """ Get all categories an the cards that are contained within them
        :return: A dict with the category names and cv_core.models.Card objects as values
        """
        categories = self.database.category_get_all()
        all_ids = set(itertools.chain.from_iterable(categories.values()))
        card_objects = {card_id: self.database.card_load(card_id) for card_id in all_ids}
        for _, card_id_list in categories:
            for card_id in card_id_list:
                card_id_list[card_id] = card_objects[card_id]
        return categories

    def search_by_name(self, search_term):
        """ Search database for cards witch contain the search string in their names
        :param search_term: Part of a card name
        :return: List of matched cards
        """
        return self.database.card_search_by_name(search_term)


if __name__ == "__main__":
    # Test code
    engine = CardvaultEngine()
