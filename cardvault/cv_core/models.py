import pprint

class Card:
    """
    Model for an MTG card
    """
    def __init__(self, card_dict={}):
        self.name = card_dict.get('name')
        self.layout = card_dict.get('layout')
        self.mana_cost = card_dict.get('manaCost')
        self.cmc = card_dict.get('cmc')
        self.colors = card_dict.get('colors')
        self.color_identity = card_dict.get('colorIdentity')
        self.names = card_dict.get('names')
        self.type = card_dict.get('type')
        self.supertypes = card_dict.get('supertypes')
        self.subtypes = card_dict.get('subtypes')
        self.types = card_dict.get('types')
        self.rarity = card_dict.get('rarity')
        self.text = card_dict.get('text')
        self.flavor = card_dict.get('flavor')
        self.artist = card_dict.get('artist')
        self.number = card_dict.get('number')
        self.power = card_dict.get('power')
        self.toughness = card_dict.get('toughness')
        self.loyalty = card_dict.get('loyalty')
        self.multiverse_id = card_dict.get('multiverseid')
        self.variations = card_dict.get('variations')
        self.watermark = card_dict.get('watermark')
        self.border = card_dict.get('border')
        self.timeshifted = card_dict.get('timeshifted')
        self.hand = card_dict.get('hand')
        self.life = card_dict.get('life')
        self.release_date = card_dict.get('releaseDate')
        self.starter = card_dict.get('starter')
        self.printings = card_dict.get('printings')
        self.original_text = card_dict.get('originalText')
        self.original_type = card_dict.get('originalType')
        self.source = card_dict.get('source')
        self.image_url = card_dict.get('imageUrl')
        self.set = card_dict.get('set')
        self.set_name = card_dict.get('setName')
        self.id = card_dict.get('id')
        self.legalities = card_dict.get('legalities')
        self.rulings = card_dict.get('rulings')
        self.foreign_names = card_dict.get('foreign_names')


class Set:
    """
    Model for an MTG expansion set
    """
    def __init__(self, set_dict={}):
        self.code = set_dict.get('code')
        self.name = set_dict.get('name')
        self.type = set_dict.get('type')
        self.border = set_dict.get('border')
        self.mkm_id = set_dict.get('mkm_id')
        self.mkm_name = set_dict.get('mkm_name')
        self.release_date = set_dict.get('releaseDate')
        self.gatherer_code = set_dict.get('gathererCode')
        self.magic_cards_info_code = set_dict.get('magicCardsInfoCode')
        self.booster = set_dict.get('booster')
        self.old_code = set_dict.get('oldCode')
        self.block = set_dict.get('block')
        self.online_only = set_dict.get('onlineOnly')