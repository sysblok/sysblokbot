import logging

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
    def __init__(self, config=None):
        if self.was_initialized():
            return

        self._drive_config = config
        self._update_from_config()
        logger.info('DriveClient successfully initialized')

    def _update_from_config(self):
        '''Update attributes according to current self._sheets_config'''
        self._credentials = ServiceAccountCredentials.from_json_keyfile_name(
            self._drive_config['api_key_path'], scopes=SCOPES)
        # https://developers.google.com/drive/api/v3/quickstart/python
        self.service = build('drive', 'v3', credentials=self._credentials)
        self.illustrations_folder_key = self._drive_config['illustrations_folder_key']

    def create_folder_for_card(self, trello_card: TrelloCard):
        existing = self._lookup_file_by_name(trello_card.name)
        if existing:
            return urljoin(BASE_URL, existing)
        file_metadata = {
            'name': trello_card.name,
            'description': trello_card.url,
            'parents': [self.illustrations_folder_key],
            'mimeType': 'application/vnd.google-apps.folder'
        }
        file = self.service.files().create(body=file_metadata, fields='id').execute()
        return urljoin(BASE_URL, file.get("id"))

    def _lookup_file_by_name(self, name: str):
        page_token = None
        results = self.service.files().list(
            q=f'name contains "{name}" and "{self.illustrations_folder_key}" in parents',
            pageSize=10,
            fields='nextPageToken, files(id, name)',
            pageToken=page_token
        ).execute()
        items = results.get('files', [])
        if len(items) == 0:
            return None
        logger.info(f'Found {len(items)} folders matching {name}.')
        return items[0].get('id')

    def _delete_file_by_id(self, file_id: str):
        self.service.files().delete(fileId=file_id).execute()
