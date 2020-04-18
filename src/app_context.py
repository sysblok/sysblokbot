import threading

from .sheets.sheets_client import GoogleSheetsClient
from .trello.trello_client import TrelloClient


# Avoid creating 2 singleton instances
lock = threading.Lock()


class AppContext:
    _instance = None
    def __new__(cls, *args, **kwargs):
        with lock:
            if cls._instance is None:
                cls._instance = super(AppContext, cls).__new__(cls)
                cls._instance._was_initialized = False
            return cls._instance

    def __init__(self, config=None):
        if self._was_initialized:
            return
        self._was_initialized = True
        self.config = config
        # TODO: Consider making them singletones too
        self.trello_client = TrelloClient(config=config['trello'])
        self.sheets_client = GoogleSheetsClient(
            api_key_path=config['sheets']['api_key_path'],
            curators_sheet_key=config['sheets']['curators_sheet_key'],
            authors_sheet_key=config['sheets']['authors_sheet_key']
        )
        # TODO: move that to db
        self.admin_chat_ids = config['telegram']['_tmp_']['admin_chat_ids']
        self.lists_config = config['trello']['_tmp_']['list_aliases']
