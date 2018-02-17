import json
import os
import itertools

from cv_engine.database import CardvaultDB
from cv_engine.util import EngineConfig, EngineConstants, Utilities


class CardvaultEngine:
    def __init__(self, config_file=False):
        """
        Create a new cv_engine instance
        :param config_file: File path of the configuration file
        """
        if config_file:
            Utilities.apply_config(config_file)
        db_file_path = os.path.join(EngineConstants.config_path, EngineConfig.db_file)
        self.database = CardvaultDB(db_file_path)

    def get_card(self, card_id):
        """
        Load a card object from database
        :param card_id: multiverse id of a card
        :return: an cv_engine.model.Card object
        """
        return self.database.card_load(card_id)

    def get_library(self) -> list:
        """
        Get the complete library of cards
        :return: Alphabetically ordered list of all cards in library
        """
        return self.database.lib_get_all()

    def get_all_categories(self) -> dict:
        """
        Get all categories an the cards that are contained within them
        :return: A dict with the category names and cv_engine.models.Card objects as values
        """
        categories = self.database.category_get_all()
        all_ids = set(itertools.chain.from_iterable(categories.values()))
        card_objects = {card_id: self.database.card_load(card_id) for card_id in all_ids}
        for _, card_id_list in categories:
            for card_id in card_id_list:
                card_id_list[card_id] = card_objects[card_id]
        return categories


if __name__ == "__main__":
    engine = CardvaultEngine()

    # Insert Data into Datasbase
    # print("Database insert test:")
    # engine.database.db_clear_data_card()
    # cards = Utilities.parse_mtgjson_cards(json.load(open("/home/luxick/Downloads/AllSets-x.json")))
    # engine.database.card_insert_many(cards)

    # Compare JSON Data to Data in Database
    # for card in Utilities.parse_mtgjson_cards(json.load(open("/home/luxick/Downloads/AllSets-x.json"))):
    #     if card.multiverse_id:
    #         print('From JSON: {}'.format(card.names))
    #         print('From DB: {}\n'.format(engine.database.card_load(card.multiverse_id).names))

    # Search test
    # term = 'fire'
    # for result in engine.database.card_search_by_name(term):
    #     print(str(result), end='\n\n')
    # Fast load test
    # engine.database.card_fast_load()
    # all_ids = engine.database.db_all_multiverse_ids()
    # print('Loaded IDs: {}'.format(len(all_ids)))
