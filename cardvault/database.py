import sqlite3
from mtgsdk import Card

from cardvault import util


class CardVaultDB:
    """Data access class for sqlite3"""
    def __init__(self, db_file: str):
        self.db_file = db_file

    def create_database(self):
        """Create initial database"""
        con = sqlite3.connect(self.db_file)

        with con:
            # Create library table
            con.execute("CREATE TABLE IF NOT EXISTS `cards` "
                        "( `name` TEXT, `layout` TEXT, `manaCost` TEXT, `cmc` INTEGER, "
                        "`colors` TEXT, `names` TEXT, `type` TEXT, `supertypes` TEXT, "
                        "`subtypes` TEXT, `types` TEXT, `rarity` TEXT, `text` TEXT, "
                        "`flavor` TEXT, `artist` TEXT, `number` INTEGER, `power` TEXT, "
                        "`toughness` TEXT, `loyalty` INTEGER, `multiverseid` INTEGER UNIQUE , "
                        "`variations` TEXT, `watermark` TEXT, `border` TEXT, `timeshifted` "
                        "TEXT, `hand` TEXT, `life` TEXT, `releaseDate` TEXT, `starter` TEXT, "
                        "`printings` TEXT, `originalText` TEXT, `originalType` TEXT, "
                        "`source` TEXT, `imageUrl` TEXT, `set` TEXT, `setName` TEXT, `id` TEXT, "
                        "`legalities` TEXT, `rulings` TEXT, `foreignNames` TEXT, "
                        "PRIMARY KEY(`multiverseid`) )")
            con.execute("CREATE TABLE IF NOT EXISTS library ( multiverse_id INT PRIMARY KEY, copies INT )")

    def insert_card(self, card: Card):
        # Connect to database
        con = sqlite3.connect(self.db_file)
        try:
            with con:
                # Map card object to database tables
                db_values = self.card_to_table_mapping(card)
                sql_string = "INSERT INTO `cards` VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
                # Insert into database
                con.execute(sql_string, db_values)
        except sqlite3.OperationalError as err:
            util.log("Database Error", util.LogLevel.Error)
            util.log(str(err), util.LogLevel.Error)
        except sqlite3.IntegrityError:
            pass

    def bulk_insert_card(self, card_list: list):
        for card in card_list:
            self.insert_card(card)

    def clear_card_data(self):
        con = sqlite3.connect(self.db_file)
        try:
            with con:
                con.execute("DELETE FROM cards")
        except sqlite3.OperationalError as err:
            util.log("Database Error", util.LogLevel.Error)
            util.log(str(err), util.LogLevel.Error)

    @staticmethod
    def card_to_table_mapping(card: Card):
        """Return the database representation of a card object"""
        return (str(card.name), str(card.layout), str(card.mana_cost), card.cmc, str(card.colors), str(card.names),
                str(card.type), str(card.supertypes), str(card.subtypes), str(card.types), str(card.rarity),
                str(card.text),
                str(card.flavor), str(card.artist), str(card.number), str(card.power), str(card.toughness),
                str(card.loyalty),
                card.multiverse_id, str(card.variations), str(card.watermark), str(card.border),
                str(card.timeshifted),
                str(card.hand), str(card.life), str(card.release_date), str(card.starter), str(card.printings),
                str(card.original_text),
                str(card.original_type), str(card.source), str(card.image_url), str(card.set), str(card.set_name),
                str(card.id),
                str(card.legalities), str(card.rulings), str(card.foreign_names))
