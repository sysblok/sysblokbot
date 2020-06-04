import logging

# https://developers.google.com/analytics/devguides/config/mgmt/v3/quickstart/service-py
from apiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

from ..trello.trello_objects import TrelloCard
from ..utils.singleton import Singleton


logger = logging.getLogger(__name__)
SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly']


class GoogleDriveClient(Singleton):
    def __init__(self, config=None):
        if self.was_initialized():
            return

        self._drive_config = config
        self._update_from_config()
        logger.info('DriveClient successfully initialized')

    def _update_from_config(self):
        """Update attributes according to current self._sheets_config"""
        self._credentials = ServiceAccountCredentials.from_json_keyfile_name(
            self._drive_config['api_key_path'], scopes=SCOPES)
        # https://developers.google.com/drive/api/v3/quickstart/python
        self.service = build('drive', 'v3', credentials=self._credentials)
        self.illustrations_folder_key = self._drive_config['illustrations_folder_key']

    def create_folder_for_card(self, trello_card: TrelloCard):
        pass
