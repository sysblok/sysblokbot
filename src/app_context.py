from .consts import TRELLO_CONFIG

from .sheets.sheets_client import GoogleSheetsClient
from .trello.trello_client import TrelloClient
from .utils.singleton import Singleton


class AppContext(Singleton):
    def __init__(self, config=None):
        if self.was_initialized():
            return

        self.config = config
        self.trello_client = TrelloClient(config=config[TRELLO_CONFIG])
        self.sheets_client = GoogleSheetsClient(
            api_key_path=config['sheets']['api_key_path'],
            curators_sheet_key=config['sheets']['curators_sheet_key'],
            authors_sheet_key=config['sheets']['authors_sheet_key']
        )
        # TODO: move that to db
        self.admin_chat_ids = config['telegram']['_tmp_']['admin_chat_ids']
        self.lists_config = config['trello']['_tmp_']['list_aliases']
