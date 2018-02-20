import sqlite3
import ast

from cv_core.models import Card, Set
from cv_core.util import MTGConstants


class CardvaultDB:
    """Data access class for sqlite3"""

    def __init__(self, db_file: str):
        self.db_file = db_file
        self.connection = sqlite3.connect(self.db_file)
        self.db_create()

    # Database operations ##############################################################################################

    def db_create(self):
        """Create initial database"""
        con = sqlite3.connect(self.db_file)

        with con:
            # Create library table
            con.execute('CREATE TABLE IF NOT EXISTS cards ('
                        'multiverseid INT, name TEXT, layout TEXT, manaCost TEXT, fcolor TEXT, cmc INT, '
                        'rarity TEXT, text TEXT, flavor TEXT, artist TEXT, number INTEGER, power TEXT, '
                        'toughness TEXT, loyalty INT, watermark TEXT, border TEXT, timeshifted INT, '
                        'hand TEXT, life TEXT, releaseDate TEXT, starter TEXT, originalText TEXT, originalType TEXT, '
                        'source TEXT, imageUrl TEXT, `set` TEXT, setName TEXT, id TEXT)')

            con.execute("CREATE TABLE IF NOT EXISTS library ( multiverseid INT PRIMARY KEY, copies INT )")
            con.execute("CREATE TABLE IF NOT EXISTS tags ( tag TEXT, multiverseid INT )")
            con.execute("CREATE TABLE IF NOT EXISTS wants ( listName TEXT, multiverseid INT )")
            con.execute("CREATE TABLE IF NOT EXISTS sets ( code TEXT PRIMARY KEY , name TEXT, type TEXT, border TEXT, "
                        "mkmid INT, mkmname TEXT, releasedate TEXT, gatherercode TEXT, magiccardsinfocode TEXT, "
                        "booster TEXT, oldcode TEXT)")

            con.execute('CREATE TABLE IF NOT EXISTS card_names ('
                        'multiverseid INT NOT NULL,'
                        'name TEXT)')

            con.execute('CREATE TABLE IF NOT EXISTS card_types ('
                        'multiverseid INT NOT NULL,'
                        'type TEXT)')

            con.execute('CREATE TABLE IF NOT EXISTS card_subtypes ('
                        'multiverseid INT NOT NULL,'
                        'subtype TEXT)')

            con.execute('CREATE TABLE IF NOT EXISTS card_supertypes ('
                        'multiverseid INT NOT NULL,'
                        'supertype TEXT)')

            con.execute('CREATE TABLE IF NOT EXISTS card_printings ('
                        'multiverseid INT NOT NULL,'
                        'code TEXT)')

            con.execute('CREATE TABLE IF NOT EXISTS card_variations ('
                        'multiverseid INT NOT NULL,'
                        'variation INT)')

            con.execute('CREATE TABLE IF NOT EXISTS card_colors ('
                        'multiverseid INT NOT NULL,'
                        'color TEXT)')

            con.execute('CREATE TABLE IF NOT EXISTS card_rulings ('
                        'multiverseid INT NOT NULL,'
                        'date TEXT,'
                        '`text` TEXT)')

            con.execute('CREATE TABLE IF NOT EXISTS card_legalities ('
                        'multiverseid INT NOT NULL,'
                        'format TEXT,'
                        'legality TEXT)')

            con.execute('CREATE TABLE IF NOT EXISTS card_foreign_names ('
                        'multiverseid INT NOT NULL,'
                        'language TEXT,'
                        'name TEXT)')

    def db_get_all(self):
        """Return data of all cards in database"""
        sql = 'SELECT * FROM cards'
        cur = self.connection.cursor()
        cur.row_factory = sqlite3.Row
        cur.execute(sql)
        rows = cur.fetchall()
        output = []
        for row in rows:
            card = self.map_row_to_card(row)
            output.append(card)
        return output

    def db_all_multiverse_ids(self) -> list:
        """
        Load all multiverse_ids from the database
        :return: list of integers
        """
        cur = self.connection.cursor()
        cur.row_factory = sqlite3.Row
        cur.execute('SELECT multiverseid FROM cards')
        return [x['multiverseid'] for x in cur.fetchall()]

    def db_clear_data_card(self):
        """Delete all resource data from database"""
        con = sqlite3.connect(self.db_file)
        try:
            with con:
                tables = ['cards', 'sets', 'card_colors', 'card_foreign_names', 'card_legalities', 'card_names',
                          'card_printings', 'card_rulings', 'card_subtypes', 'card_supertypes', 'card_types',
                          'card_variations']
                for table in tables:
                    con.execute("DELETE FROM {}".format(table))
        except Exception as e:
            print(e)

    def db_clear_data_user(self):
        """Delete all user data from database"""
        self.db_operation('DELETE FROM library')
        self.db_operation('DELETE FROM wants')
        self.db_operation('DELETE FROM tags')

    # Card operations ##################################################################################################

    def card_insert_many(self, card_list: list):
        """
        Shorthand for inserting many cards at once
        Uses a single database connection for all commits
        :param card_list: list of cv_core.models.Card objects
        """
        con = sqlite3.connect(self.db_file)
        with con:
            for card in card_list:
                self.card_insert(card, con)

    def card_insert(self, card, connection=None):
        """
        Insert a single card into the database
        :param card: An cv_core.models.Card object
        :param connection: (Optional) supply a database connection to use. It will not be closed after the function
        ends
        """
        if not card.multiverse_id:
            return
        if not connection:
            con = sqlite3.connect(self.db_file)
        else:
            con = connection
        try:
            # List attributes of card object are written in connection tables
            mapping = {'card_names': card.names, 'card_types': card.types, 'card_subtypes': card.subtypes,
                       'card_supertypes': card.supertypes, 'card_printings': card.printings,
                       'card_variations': card.variations, 'card_colors': card.colors}

            for table_name, values in mapping.items():
                if not values:
                    continue
                db_values = [(card.multiverse_id, value) for value in values]
                sql_string = "INSERT INTO {} VALUES (?, ?)".format(table_name)
                con.executemany(sql_string, db_values)

            # Insert dict attributes into separate tables
            mapping = {'card_rulings': [card.rulings, 'date', 'text'],
                       'card_legalities': [card.legalities, 'format', 'legality'],
                       'card_foreign_names': [card.foreign_names, 'language', 'name']}

            for table_name, data in mapping.items():
                if not data[0]:
                    continue
                db_values = [(card.multiverse_id, x.get(data[1]), x.get(data[2])) for x in data[0]]
                sql_string = "INSERT INTO {} VALUES (?, ?, ?)".format(table_name)
                con.executemany(sql_string, db_values)

            # Write card attributes to database
            card_row = self.map_card_to_row(card)
            sql_string = "INSERT INTO cards VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,"\
                         "?, ?, ?, ?, ?, ?, ?)"
            con.execute(sql_string, card_row)
        except sqlite3.OperationalError as e:
            print(e)
        except sqlite3.IntegrityError as e:
            print(e)
        finally:
            if not connection:
                con.close()

    def card_load(self, card_id: int):
        """
        Load a single card from database
        :param card_id: multiverse_id of the card
        :return: an cv_core.models.Card object
        """
        cur = self.connection.cursor()
        cur.row_factory = sqlite3.Row

        # Fetch card row
        cur.execute('SELECT * FROM `cards` WHERE `multiverseid` = ?', (card_id,))
        card_dict = dict(cur.fetchall()[0])

        # Fetch list attributes of card
        attrs_list = {'card_names', 'card_types', 'card_subtypes', 'card_supertypes', 'card_printings',
                      'card_variations', 'card_colors'}
        for attr in attrs_list:
            cur.execute('SELECT * FROM {} WHERE `multiverseid` = ?'.format(attr), (card_id,))
            rows = cur.fetchall()
            card_dict[attr.split('_')[1]] = [row[1] for row in rows]

        # Fetch dict attributes of card
        attrs_list = {'card_rulings': ['date', 'text'],
                      'card_legalities': ['format', 'legality'],
                      'card_foreign_names': ['language', 'name']}
        for table_name, attrs in attrs_list.items():
            cur.execute('SELECT {}, {} FROM {} WHERE `multiverseid` = ?'.format(attrs[0], attrs[1], table_name),
                        (card_id,))
            rows = cur.fetchall()
            attr_name = '_'.join(table_name.split('_')[1:])
            card_dict[attr_name] = {row[0]: row[1] for row in rows}
        return Card(card_dict)

    def card_search_by_name(self, search_term):
        """
        Search for card by their name.
        Search results are limited to 50 results.
        :param search_term: Search String
        :return: List of 'cv_core.models.Card' objects
        """
        cur = self.connection.cursor()
        cur.row_factory = sqlite3.Row
        cur.execute("SELECT `multiverseid` FROM `cards` WHERE `name` LIKE ? LIMIT 50", ('%' + search_term + '%',))
        return [self.card_load(row[0]) for row in cur.fetchall()]

    # Library operations ###############################################################################################

    def lib_get_all(self) -> list:
        """
        Load all cards in library from database in alphabetical order
        :return: A list containing all cards in library as 'cv_core.models.Card'
        """
        cur = self.connection.cursor()
        cur.row_factory = sqlite3.Row
        cur.execute('SELECT * FROM `library` INNER JOIN `cards` ON library.multiverseid = cards.multiverseid')
        rows = cur.fetchall()
        return sorted([self.map_row_to_card(row) for row in rows], key=lambda x: x.name)

    def lib_card_add(self, card: Card):
        """Insert card into library"""
        self.db_operation("INSERT INTO `library` (`copies`, `multiverseid`) VALUES (?, ?)", (1, card.multiverse_id))

    def lib_card_remove(self, card: Card):
        """Remove a from the library"""
        self.db_operation("DELETE FROM `library` WHERE `multiverseid` = ?", (card.multiverse_id,))

    # Category operations ##############################################################################################

    def category_get_all(self) -> dict:
        """Loads a dict from database with all categories and the card ids they contain"""
        cur = self.connection.cursor()
        cur.row_factory = sqlite3.Row

        # First load all tags
        cur.execute("SELECT `tag` FROM tags GROUP BY `tag`")
        # Create dict with the fetched categories as key
        cats = {row['tag']: [] for row in cur.fetchall()}

        # Go trough all categories an load the card ids
        for cat in cats.keys():
            cur.execute('SELECT `multiverseid` FROM `tags` WHERE tags.tag = ? AND multiverseid NOT NULL', (cat,))
            rows = cur.fetchall()
            for row in rows:
                cats[cat].append(row["multiverseid"])
        return cats

    def category_new(self, name: str):
        """Add a new category to the database"""
        self.db_operation("INSERT INTO `tags` VALUES (?, NULL)", (name,))

    def category_delete(self, name: str):
        """Remove a category with all entries"""
        self.db_operation("DELETE FROM `tags` WHERE `tag` = ?", (name,))

    def category_rename(self, name_old: str, name_new: str):
        """Rename a category"""
        self.db_operation('UPDATE `tags` SET `tag`=? WHERE `tag` = ?;', (name_new, name_old))

    def category_card_add(self, name: str, card_id: int):
        """Add an entry for a categorized card"""
        self.db_operation("INSERT INTO `tags` VALUES (?, ?)", (name, card_id))

    def category_card_remove(self, name: str, card_id: int):
        """Remove a card from a category"""
        self.db_operation("DELETE FROM `tags` WHERE `tag` = ? AND `multiverseid` = ?", (name, card_id))

    def category_get_for_card(self, card) -> list:
        """Return a list with all categories that contain the supplied card."""
        cur = self.connection.cursor()
        cur.row_factory = sqlite3.Row
        cur.execute('SELECT `tag` FROM `tags` WHERE tags.multiverseid = ? ', (card.multiverse_id,))
        rows = cur.fetchall()
        return [row['tag'] for row in rows]

    # Wants operations #################################################################################################

    def wants_get_all(self) -> dict:
        """Load all wants lists from database"""
        cur = self.connection.cursor()
        cur.row_factory = sqlite3.Row

        # First load all lists
        cur.execute("SELECT `listName` FROM wants GROUP BY `listName`")
        wants = {row['listName']: [] for row in cur.fetchall()}

        # Go trough all tags an load the card ids
        for list_name in wants.keys():
            cur.execute('SELECT * FROM '
                        '(SELECT `multiverseid` FROM `wants` WHERE `listName` = ? AND multiverseid NOT NULL) tagged '
                        'INNER JOIN `cards` ON tagged.multiverseid = cards.multiverseid', (list_name,))
            rows = cur.fetchall()
            for row in rows:
                wants[list_name].append(self.map_row_to_card(row))
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

    def search_by_name_filtered(self, term: str, filters: dict, list_size: int) -> list:
        """Search for cards based on the cards name with filter constrains"""
        filter_rarity = filters["rarity"]
        filer_type = filters["type"]
        filter_set = filters["set"]
        filter_mana = filters["mana"]
        filter_mana.sort(key=lambda x: MTGConstants.mana_order.index(x))

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
            sql += ' AND `fcolor` = ?'
            parameters.append(self.filter_colors_list(filter_mana))
        sql += ' LIMIT ?'
        parameters.append(str(list_size))

        con = sqlite3.connect(self.db_file)
        cur = con.cursor()
        cur.row_factory = sqlite3.Row
        cur.execute(sql, parameters)
        rows = cur.fetchall()
        con.close()

        output = []
        for row in rows:
            card = self.map_row_to_card(row)
            output.append(card)
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

    def set_get_all(self):
        con = sqlite3.connect(self.db_file)
        cur = con.cursor()
        cur.row_factory = sqlite3.Row

        cur.execute("SELECT * FROM sets")
        rows = cur.fetchall()
        sets = []
        for row in rows:
            sets.append(self.map_row_to_set(row))

        return sets

    # DB internal functions ############################################################################################

    def rows_to_card_dict(self, rows):
        """Convert database rows to a card dict"""
        output = {}
        for row in rows:
            card = self.map_row_to_card(row)
            output[card.multiverse_id] = card
        return output

    def db_operation(self, sql: str, args: tuple = ()):
        """Perform an arbitrary sql operation on the database"""
        cur = self.connection.cursor()
        try:
            cur.execute(sql, args)
        except sqlite3.OperationalError:
            # TODO Log
            pass

    def db_save_changes(self):
        try:
            self.connection.commit()
        except sqlite3.Error:
            self.connection.rollback()
            # TODO Log
            pass

    def db_unsaved_changes(self) -> bool:
        """Checks if database is currently in transaction"""
        return self.connection.in_transaction

    @staticmethod
    def filter_colors_list(mana) -> str:
        symbols = set(mana)
        output = [s for s in symbols if (s in MTGConstants.mana_order)]
        return "-".join(output)

    @staticmethod
    def filter_colors(card) -> str:
        """Extracts the colors of a card for filtering."""
        output = []
        if card.colors is not None:
            for color in card.colors:
                output.append(MTGConstants.color_shorthands[color])
        else:
            output.append("C")
        # TODO extract symbols from card text

        return "-".join(output)

    def map_card_to_row(self, card):
        """Return the database representation of a card object"""
        return (card.multiverse_id, card.name, card.layout, card.mana_cost, self.filter_colors(card), card.cmc,
                card.rarity, card.text, card.flavor, card.artist, card.number, card.power, card.toughness, card.loyalty,
                card.watermark, card.border, card.timeshifted, card.hand, card.life, card.release_date, card.starter,
                card.original_text, card.original_type, card.source, card.image_url, card.set, card.set_name, card.id)

    @staticmethod
    def map_row_to_card(row):
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

        # # Bool attributes
        # card.timeshifted = ast.literal_eval(row["timeshifted"])
        #
        # # List attributes
        # card.names = ast.literal_eval(row["names"])
        # card.supertypes = ast.literal_eval(row["supertypes"])
        # card.subtypes = ast.literal_eval(row["subtypes"])
        # card.types = ast.literal_eval(row["types"])
        # card.printings = ast.literal_eval(row["printings"])
        # card.variations = ast.literal_eval(row["variations"])
        #
        # # Dict attributes
        # card.legalities = ast.literal_eval(row["legalities"])
        # card.rulings = ast.literal_eval(row["rulings"])
        # card.foreign_names = ast.literal_eval(row["foreignNames"])

        return card

    @staticmethod
    def map_set_to_row(set):
        """Convert Set object to a table row"""
        return (set.code, set.name, set.type, set.border, set.mkm_id, set.mkm_name, set.release_date, set.gatherer_code,
                set.magic_cards_info_code, str(set.booster), set.old_code)

    @staticmethod
    def map_row_to_set(row):
        """Return Set object representation of a table row"""
        set = Set()
        set.code = row['code']
        set.name = row['name']
        set.type = row['type']
        set.border = row['border']
        set.mkm_id = row['mkmid']
        set.mkm_name = row['mkmname']
        set.release_date = row['releasedate']
        set.gatherer_code = row['gatherercode']
        set.magic_cards_info_code = row['magiccardsinfocode']
        set.booster = ast.literal_eval(row['booster'])
        set.old_code = row['oldcode']
        return set
