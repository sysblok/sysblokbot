import logging

from typing import List
from urllib.parse import urljoin

# https://developers.google.com/analytics/devguides/config/mgmt/v3/quickstart/service-py
from apiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

from ..trello.trello_objects import TrelloCard
from ..utils.singleton import Singleton


logger = logging.getLogger(__name__)
SCOPES = ['https://www.googleapis.com/auth/drive.file']
BASE_URL = 'https://drive.google.com/drive/u/1/folders/'


class GoogleDriveClient(Singleton):
    def __init__(self, drive_config=None):
        if self.was_initialized():
            return

        self._drive_config = drive_config
        self._update_from_config()
        logger.info('DriveClient successfully initialized')

    def update_config(self, new_drive_config: dict):
        """To be called after config automatic update"""
        self._drive_config = new_drive_config
        self._update_from_config()

    def _update_from_config(self):
        '''Update attributes according to current self._sheets_config'''
        self.illustrations_folder_key = self._drive_config['illustrations_folder_key']
        self._authorize()

    def _authorize(self):
        self._credentials = ServiceAccountCredentials.from_json_keyfile_name(
            self._drive_config['api_key_path'], scopes=SCOPES)
        # https://developers.google.com/drive/api/v3/quickstart/python
        self.service = build('drive', 'v3', credentials=self._credentials)

    def create_folder_for_card(self, trello_card: TrelloCard) -> str:
        existing = self._lookup_file_by_name(trello_card.name)
        if existing:
            return urljoin(BASE_URL, existing)
        return urljoin(BASE_URL, self._create_file(
            name=trello_card.name,
            description=trello_card.url,
            parents=[self.illustrations_folder_key],
        ))

    def _create_file(self, name: str, description: str, parents: List[str]) -> str:
        file_metadata = {
            'name': name,
            'description': description,
            'parents': parents,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        try:
            file = self.service.files().create(body=file_metadata, fields='id').execute()
        except Exception as e:
            logger.error(f'Failed to create a folder for {description} in Google drive: {e}')
            return None
        return file.get("id")

    def _lookup_file_by_name(self, name: str) -> str:
        page_token = None
        name = name.replace('"', '\\"')
        try:
            results = self.service.files().list(
                q=f'name contains "{name}" and "{self.illustrations_folder_key}" in parents',
                pageSize=10,
                fields='nextPageToken, files(id, name)',
                pageToken=page_token
            ).execute()
        except Exception as e:
            logger.error(f'Failed to query Google drive for existing folder {name}: {e}')
            return None
        items = results.get('files', [])
        if len(items) == 0:
            return None
        logger.info(f'Found {len(items)} folders matching {name}.')
        return items[0].get('id')
