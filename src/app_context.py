import logging

from .consts import TRELLO_CONFIG

from .config_manager import ConfigManager
from .db.db_client import DBClient
from .drive.drive_client import GoogleDriveClient
from .sheets.sheets_client import GoogleSheetsClient
from .tg.sender import TelegramSender
from .trello.trello_client import TrelloClient
from .utils.singleton import Singleton


logger = logging.getLogger(__name__)


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
        try:
            self.sheets_client = GoogleSheetsClient(
                config=config_manager.get_sheets_config()
            )
        except Exception as e:
            self.sheets_client = None
            logger.critical(f'Could not initialize GoogleSheetsClient: {e}')
        try:
            self.drive_client = GoogleDriveClient(
                config=config_manager.get_drive_config()
            )
        except Exception as e:
            self.drive_client = None
            logger.critical(f'Could not initialize GoogleDriveClient: {e}')


        try:
            self.db_client = DBClient(config=config_manager.get_db_config())
        except Exception as e:
            self.db_client = None
            logger.critical(f'Could not initialize DBClient: {e}')

        if self.sheets_client and self.db_client:
            self.db_client.fetch_all(self.sheets_client)

        # TODO: move that to db
        tg_config = config_manager.get_telegram_config()
        trello_config = config_manager.get_trello_config()

        self.set_access_rights(tg_config)

    def set_access_rights(self, tg_config: dict):
        self.admin_chat_ids = set(tg_config['admin_chat_ids'])
        self.manager_chat_ids = set(tg_config['manager_chat_ids'])
