import logging

from .analytics.api_facebook_analytics import ApiFacebookAnalytics
from .analytics.api_instagram_analytics import ApiInstagramAnalytics
from .config_manager import ConfigManager
from .db.db_client import DBClient
from .drive.drive_client import GoogleDriveClient
from .facebook.facebook_client import FacebookClient
from .focalboard.focalboard_client import FocalboardClient
from .instagram.instagram_client import InstagramClient
from .roles.role_manager import RoleManager
from .sheets.sheets_client import GoogleSheetsClient
from .strings import StringsDBClient
from .tg.tg_client import TgClient
from .trello.trello_client import TrelloClient
from .utils.singleton import Singleton

logger = logging.getLogger(__name__)


class AppContext(Singleton):
    """
    Stores client references in one place,
    so that they can be easily used in jobs.
    """

    def __init__(
        self, config_manager: ConfigManager = None, skip_db_update: bool = False
    ):
        if self.was_initialized():
            return

        self.config_manager = config_manager
        self.sheets_client = GoogleSheetsClient(
            sheets_config=config_manager.get_sheets_config()
        )
        self.strings_db_client = StringsDBClient(
            strings_db_config=config_manager.get_strings_db_config()
        )
        self.drive_client = GoogleDriveClient(
            drive_config=config_manager.get_drive_config()
        )
        self.db_client = DBClient(db_config=config_manager.get_db_config())
        self.role_manager = RoleManager(self.db_client)

        if not skip_db_update:
            self.strings_db_client.fetch_strings_sheet(self.sheets_client)
            self.db_client.fetch_all(self.sheets_client)
            self.role_manager.calculate_db_roles()

        self.trello_client = TrelloClient(
            trello_config=config_manager.get_trello_config()
        )
        self.focalboard_client = FocalboardClient(
            focalboard_config=config_manager.get_focalboard_config()
        )
        self.facebook_client = FacebookClient(
            facebook_config=config_manager.get_facebook_config()
        )
        self.instagram_client = InstagramClient(
            facebook_config=config_manager.get_facebook_config()
        )
        self.facebook_analytics = ApiFacebookAnalytics(self.facebook_client)
        self.instagram_analytics = ApiInstagramAnalytics(self.instagram_client)

        self.tg_client = TgClient(tg_config=config_manager.get_telegram_config())

        # TODO: move that to db
        tg_config = config_manager.get_telegram_config()
        self.set_access_rights(tg_config)

    def set_access_rights(self, tg_config: dict):
        self.admin_chat_ids = set(tg_config["admin_chat_ids"])
        self.manager_chat_ids = set(tg_config["manager_chat_ids"])
