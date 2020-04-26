from .consts import TRELLO_CONFIG

from .config_manager import ConfigManager
from .sheets.sheets_client import GoogleSheetsClient
from .tg.sender import TelegramSender
from .trello.trello_client import TrelloClient
from .utils.singleton import Singleton


class AppContext(Singleton):
    """
    Stores client references in one place,
    so that they can be easily used in jobs.
    """
    def __init__(self, config_manager: ConfigManager = None):
        if self.was_initialized():
            return

        self.config_manager = config_manager
        self.trello_client = TrelloClient(
            config=config_manager.get_trello_config()
        )
        sheets_config = config_manager.get_sheets_config()
        self.sheets_client = GoogleSheetsClient(
            api_key_path=sheets_config['api_key_path'],
            curators_sheet_key=sheets_config['curators_sheet_key'],
            authors_sheet_key=sheets_config['authors_sheet_key']
        )

        # TODO: move that to db
        tg_config = config_manager.get_telegram_config()
        trello_config = config_manager.get_trello_config()
        self.admin_chat_ids = tg_config['_tmp_']['admin_chat_ids']
        self.lists_config = trello_config['_tmp_']['list_aliases']
