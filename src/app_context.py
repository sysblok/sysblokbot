from .consts import TRELLO_CONFIG

from .sheets.sheets_client import GoogleSheetsClient
from .tg.sender import TelegramSender
from .trello.trello_client import TrelloClient
from .utils.singleton import Singleton


class AppContext(Singleton):
    """
    Stores client references in one place,
    so that they can be easily used in jobs.
    """
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
        # must be properly reinitialized after SysBlokInstance ready
        self.telegram_sender = TelegramSender(should_initialize=False)

        # TODO: move that to db
        self.admin_chat_ids = config['telegram']['_tmp_']['admin_chat_ids']
        self.lists_config = config['trello']['_tmp_']['list_aliases']
