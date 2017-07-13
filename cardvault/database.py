import sqlite3
import ast

from mtgsdk import Card
from cardvault import util


class CardVaultDB:
    """Data access class for sqlite3"""
    def __init__(self, db_file: str):
        self.db_file = db_file

    # Database operations ##############################################################################################

    def db_create(self):
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
            con.execute("CREATE TABLE IF NOT EXISTS tags ( tag TEXT, multiverseid INT )")
            con.execute("CREATE TABLE IF NOT EXISTS wants ( listName TEXT, multiverseid INT )")

    def db_card_insert(self, card: Card):
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

    def db_card_insert_bulk(self, card_list: list):
        for card in card_list:
            self.db_card_insert(card)

    def db_get_all(self):
        sql = 'SELECT * FROM cards'
        con = sqlite3.connect(self.db_file)
        cur = con.cursor()
        cur.row_factory = sqlite3.Row
        cur.execute(sql)
        rows = cur.fetchall()
        con.close()
        output = []
        for row in rows:
            card = self.table_to_card_mapping(row)
            output.append(card)
        return output

    def db_clear_data_card(self):
        """Delete all resource data from database"""
        self.db_operation("DELETE FROM cards")

    def db_clear_data_user(self):
        """Delete all user data from database"""
        self.db_operation('DELETE FROM library')
        self.db_operation('DELETE FROM wants')
        self.db_operation('DELETE FROM tags')

    # Library operations ###############################################################################################

    def lib_get_all(self) -> dict:
        """Load library from database"""
        con = sqlite3.connect(self.db_file)
        cur = con.cursor()
        cur.row_factory = sqlite3.Row
        cur.execute('SELECT * FROM `library` INNER JOIN `cards` ON library.multiverseid = cards.multiverseid')
        rows = cur.fetchall()
        con.close()

        return self.rows_to_card_dict(rows)

    def lib_card_add(self, card: Card):
        """Insert card into library"""
        self.db_operation("INSERT INTO `library` (`copies`, `multiverseid`) VALUES (?, ?)", (1, card.multiverse_id))

    def lib_card_remove(self, card: Card):
        """Remove a from the library"""
        self.db_operation("DELETE FROM `library` WHERE `multiverseid` = ?", (card.multiverse_id,))

    # Tag operations ###################################################################################################

    def tag_get_all(self) -> dict:
        """Loads a dict from database with all tags and the card ids tagged"""
        con = sqlite3.connect(self.db_file)
        cur = con.cursor()
        cur.row_factory = sqlite3.Row

        # First load all tags
        cur.execute("SELECT `tag` FROM tags GROUP BY `tag`")
        rows = cur.fetchall()
        tags = {}
        for row in rows:
            tags[row["tag"]] = []

        # Go trough all tags an load the card ids
        for tag in tags.keys():
            cur.execute('SELECT `multiverseid` FROM `tags` WHERE tags.tag = ? AND multiverseid NOT NULL', (tag,))
            rows = cur.fetchall()
            for row in rows:
                tags[tag].append(row["multiverseid"])
        return tags

    def tag_new(self, tag: str):
        """Add a new tag to the database"""
        self.db_operation("INSERT INTO `tags` VALUES (?, NULL)", (tag,))

    def tag_delete(self, tag: str):
        """Remove a tag with all entries"""
        self.db_operation("DELETE FROM `tags` WHERE `tag` = ?", (tag,))

    def tag_rename(self, name_old: str, name_new: str):
        """Rename a tag"""
        self.db_operation('UPDATE `tags` SET `tag`=? WHERE `tag` = ?;', (name_new, name_old))

    def tag_card_add(self, tag: str, card_id: int):
        """Add an entry for a tagged card"""
        self.db_operation("INSERT INTO `tags` VALUES (?, ?)", (tag, card_id))

    def tag_card_remove(self, tag: str, card_id: int):
        """Remove a card from a tag"""
        self.db_operation("DELETE FROM `tags` WHERE `tag` = ? AND `multiverseid` = ?", (tag, card_id))

    def tag_card_check_tagged(self, card) -> tuple:
        """Check if a card is tagged. Return True/False and a list of tags."""
        con = sqlite3.connect(self.db_file)
        cur = con.cursor()
        cur.row_factory = sqlite3.Row
        cur.execute('SELECT `tag` FROM `tags` WHERE tags.multiverseid = ? ', (card.multiverse_id,))
        rows = cur.fetchall()

        if len(rows) == 0:
            return False, []
        else:
            tags = []
            for row in rows:
                tags.append(row["tag"])
            return True, tags

    # Wants operations #################################################################################################

    def wants_get_all(self) -> dict:
        """Load all wants lists from database"""
        con = sqlite3.connect(self.db_file)
        cur = con.cursor()
        cur.row_factory = sqlite3.Row

        # First load all lists
        cur.execute("SELECT `listName` FROM wants GROUP BY `listName`")
        rows = cur.fetchall()
        wants = {}
        for row in rows:
            wants[row["listName"]] = []

        # Go trough all tags an load the card ids
        for list_name in wants.keys():
            cur.execute('SELECT * FROM '
                        '(SELECT `multiverseid` FROM `wants` WHERE `listName` = ? AND multiverseid NOT NULL) tagged '
                        'INNER JOIN `cards` ON tagged.multiverseid = cards.multiverseid', (list_name,))
            rows = cur.fetchall()
            for row in rows:
                wants[list_name].append(self.table_to_card_mapping(row))
        return wants

    def wants_new(self, name: str):
        """Add a new wants list to the database"""
        self.db_operation("INSERT INTO `wants` VALUES (?, NULL)", (name,))

    def wants_delete(self, name: str):
        """Remove a tag with all entries"""
        self.db_operation("DELETE FROM `wants` WHERE `listName` = ?", (name,))

    def wants_rename(self, name_old: str, name_new: str):
        """Rename a tag"""
        self.db_operation('UPDATE `wants` SET `listName`=? WHERE `listName` = ?;', (name_new, name_old))

    def wants_card_add(self, list_name: str, card_id: int):
        """Add a card entry to a wants list"""
        self.db_operation("INSERT INTO `wants` VALUES (?, ?)", (list_name, card_id))

    def wants_card_remove(self, list_name: str, card_id: int):
        """Remove a card from a want list """
        self.db_operation("DELETE FROM `wants` WHERE `listName` = ? AND `multiverseid` = ?", (list_name, card_id))

    # Query operations #################################################################################################

    def search_by_name_filtered(self, term: str, filters: dict, list_size: int) -> dict:
        """Search for cards based on the cards name with filter constrains"""
        filter_rarity = filters["rarity"]
        filer_type = filters["type"]
        filter_set = filters["set"]
        filter_mana = filters["mana"].split(',')

        sql = 'SELECT * FROM cards WHERE `name` LIKE ?'
        parameters = ['%' + term + '%']
        if filter_rarity != "":
            sql += ' AND `rarity` = ?'
            parameters.append(filter_rarity)
        if filer_type != "":
            sql += ' AND `types` LIKE ?'
            parameters.append('%' + filer_type + '%')
        if filter_set != "":
            sql += ' AND `set` = ?'
            parameters.append(filter_set)
        if len(filter_mana) != 0:
            for color in filter_mana:
                sql += ' AND `manaCost` LIKE ?'
                parameters.append('%' + color + '%')
        sql += ' LIMIT ?'
        parameters.append(list_size)

        con = sqlite3.connect(self.db_file)
        cur = con.cursor()
        cur.row_factory = sqlite3.Row
        cur.execute(sql, parameters)
        rows = cur.fetchall()
        con.close()

        output = {}
        for row in rows:
            card = self.table_to_card_mapping(row)
            output[card.multiverse_id] = card
        return output

    def search_by_name(self, term: str) -> dict:
        """Search for cards based on the cards name"""
        con = sqlite3.connect(self.db_file)
        cur = con.cursor()
        cur.row_factory = sqlite3.Row
        cur.execute("SELECT * FROM cards WHERE `name` LIKE ? LIMIT 50", ('%' + term + '%',))
        rows = cur.fetchall()
        con.close()

        return self.rows_to_card_dict(rows)

    # DB internal functions ############################################################################################

    def rows_to_card_dict(self, rows):
        """Convert database rows to a card dict"""
        output = {}
        for row in rows:
            card = self.table_to_card_mapping(row)
            output[card.multiverse_id] = card
        return output

    def db_operation(self, sql: str, parms: tuple=()):
        """Perform an arbitrary sql operation on the database"""
        con = sqlite3.connect(self.db_file)
        try:
            with con:
                con.execute(sql, parms)
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

    @staticmethod
    def table_to_card_mapping(row: sqlite3.Row):
        """Return card object representation of a table row"""
        card = Card()
        card.multiverse_id = row["multiverseid"]
        tmp = row["name"]
        card.name = tmp
        card.layout = row["layout"]
        card.mana_cost = row["manacost"]
        card.cmc = row["cmc"]
        card.colors = row["colors"]
        card.type = row["type"]
        card.rarity = row["rarity"]
        card.text = row["text"]
        card.flavor = row["flavor"]
        card.artist = row["artist"]
        card.number = row["number"]
        card.power = row["power"]
        card.toughness = row["toughness"]
        card.loyalty = row["loyalty"]
        card.watermark = row["watermark"]
        card.border = row["border"]
        card.hand = row["hand"]
        card.life = row["life"]
        card.release_date = row["releaseDate"]
        card.starter = row["starter"]
        card.original_text = row["originalText"]
        card.original_type = row["originalType"]
        card.source = row["source"]
        card.image_url = row["imageUrl"]
        card.set = row["set"]
        card.set_name = row["setName"]
        card.id = row["id"]

        # Bool attributes
        card.timeshifted = ast.literal_eval(row["timeshifted"])

        # List attributes
        card.names = ast.literal_eval(row["names"])
        card.supertypes = ast.literal_eval(row["supertypes"])
        card.subtypes = ast.literal_eval(row["subtypes"])
        card.types = ast.literal_eval(row["types"])
        card.printings = ast.literal_eval(row["printings"])
        card.variations = ast.literal_eval(row["variations"])

        # Dict attributes
        card.legalities = ast.literal_eval(row["legalities"])
        card.rulings = ast.literal_eval(row["rulings"])
        card.foreign_names = ast.literal_eval(row["foreignNames"])

        return card


    # def save_library(self, cards: dict):
    #     """Updates the library, adds new cards"""
    #     con = sqlite3.connect(self.db_file)
    #     try:
    #         with con:
    #             for multiverse_id in cards.keys():
    #                 con.execute('UPDATE `library` SET `copies`=?, `multiverseid`=? WHERE multiverseid = ?;',
    #                             (1, multiverse_id, multiverse_id))
    #                 con.execute('INSERT INTO `library` (`copies`, `multiverseid`) '
    #                             'SELECT ?,? WHERE (SELECT Changes() = 0);', (1, multiverse_id))
    #     except sqlite3.OperationalError as err:
    #         util.log("Database Error", util.LogLevel.Error)
    #         util.log(str(err), util.LogLevel.Error)
    #
    # def save_tags(self, tags: dict):
    #     """Updates the tags table"""
    #     con = sqlite3.connect(self.db_file)
    #     try:
    #         with con:
    #             for tag, id_list in tags.items():
    #                 for id in id_list:
    #                     con.execute('UPDATE `tags` SET `tag`=?, `multiverseid`=? WHERE tags.multiverseid = ?;',
    #                                 (tag, id, id))
    #                     con.execute('INSERT INTO `tags` (`tag`, `multiverseid`) '
    #                                 'SELECT ?,? WHERE (SELECT Changes() = 0);', (tag, id))
    #     except sqlite3.OperationalError as err:
    #         util.log("Database Error", util.LogLevel.Error)
    #         util.log(str(err), util.LogLevel.Error)
    #
    # def save_wants(self, wants: dict):
    #     """Updates the wants table"""
    #     con = sqlite3.connect(self.db_file)
    #     try:
    #         with con:
    #             for name, cards in wants.items():
    #                 for card in cards:
    #                     con.execute('UPDATE `wants` SET `listName`=?, `multiverseid`=? WHERE wants.multiverseid = ?;',
    #                                 (name, card.multiverse_id, card.multiverse_id))
    #                     con.execute('INSERT INTO `wants` (`listName`, `multiverseid`) '
    #                                 'SELECT ?,? WHERE (SELECT Changes() = 0);', (name, card.multiverse_id))
    #     except sqlite3.OperationalError as err:
    #         util.log("Database Error", util.LogLevel.Error)
    #         util.log(str(err), util.LogLevel.Error)
