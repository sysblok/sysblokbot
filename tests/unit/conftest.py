import pytest

import json
import os

from deepdiff import DeepDiff
from typing import List, Dict

from utils.json_loader import JsonLoader

from src.config_manager import ConfigManager
from src.db.db_client import DBClient
from src.drive.drive_client import GoogleDriveClient
from src.sheets.sheets_client import GoogleSheetsClient
from src.tg.sender import TelegramSender
from src.trello.trello_client import TrelloClient


ROOT_TEST_DIR = os.path.abspath(os.path.dirname(__file__))
STATIC_TEST_DIR = os.path.join(ROOT_TEST_DIR, 'static')
SHEETS_TEST_DIR = os.path.join(STATIC_TEST_DIR, 'sheets')
TRELLO_TEST_DIR = os.path.join(STATIC_TEST_DIR, 'trello')

CONFIG_PATH = os.path.join(STATIC_TEST_DIR, 'config.json')
CONFIG_OVERRIDE_PATH = os.path.join(STATIC_TEST_DIR, 'config_override.json')


@pytest.fixture
def mock_config_manager(monkeypatch):
    config_manager = ConfigManager(CONFIG_PATH, CONFIG_OVERRIDE_PATH)
    config_manager.load_config_with_override()
    return config_manager


@pytest.fixture
def mock_trello(monkeypatch, mock_config_manager):

    def _make_request(_, uri: str, payload={}) -> (int, Dict):

        load_json = JsonLoader(TRELLO_TEST_DIR).load_json

        if uri.startswith('boards'):
            if uri.endswith('lists'):
                return 200, load_json('lists.json')
            elif uri.endswith('cards'):
                return 200, load_json('cards.json')
            elif uri.endswith('members'):
                return 200, load_json('members.json')
            elif uri.endswith('customFields'):
                return 200, load_json('board_custom_fields.json')
            else:
                return 200, load_json('board.json')
        elif uri.startswith('cards'):
            if uri.endswith('customFieldItems'):
                return 200, load_json('card_custom_fields.json')
            if uri.endswith('actions'):
                return 200, load_json('card_actions.json')
        elif uri.startswith('lists'):
            if uri.endswith('cards'):
                return 200, load_json('cards.json')

    monkeypatch.setattr(TrelloClient, '_make_request', _make_request)

    return TrelloClient(trello_config=mock_config_manager.get_trello_config())


@pytest.fixture
def mock_sheets_client(monkeypatch, mock_config_manager):

    def _authorize(self):
        pass

    def _parse_gs_res(_, title_key_map: Dict, sheet_key: str) -> List[Dict]:

        load_json = JsonLoader(SHEETS_TEST_DIR).load_json

        if sheet_key == 'authors_sheet_key':
            return load_json('authors.json')
        elif sheet_key == 'curators_sheet_key':
            return load_json('curators.json')
        elif sheet_key == 'rubrics_registry_sheet_key':
            return load_json('rubrics.json')
        elif sheet_key == 'strings_sheet_key':
            return load_json('strings.json')

    monkeypatch.setattr(GoogleSheetsClient, '_authorize', _authorize)
    monkeypatch.setattr(GoogleSheetsClient, '_parse_gs_res', _parse_gs_res)

    return GoogleSheetsClient(sheets_config=mock_config_manager.get_sheets_config())


@pytest.fixture
def mock_drive_client(monkeypatch, mock_config_manager):

    def _authorize(self):
        pass

    def _create_file(self, name: str, description: str, parents: List[str]) -> str:
        pass

    def _lookup_file_by_name(self, name: str) -> str:
        pass

    monkeypatch.setattr(GoogleDriveClient, '_authorize', _authorize)
    monkeypatch.setattr(GoogleDriveClient, '_create_file', _create_file)
    monkeypatch.setattr(GoogleDriveClient, '_lookup_file_by_name', _lookup_file_by_name)

    return GoogleDriveClient(drive_config=mock_config_manager.get_drive_config())


@pytest.fixture
def mock_telegram_bot(monkeypatch, mock_config_manager):
    return {}


@pytest.fixture
def mock_sender(monkeypatch, mock_config_manager, mock_telegram_bot):

    def send_to_chat_id(self, message_text: str, chat_id: int, **kwargs):
        pass

    monkeypatch.setattr(TelegramSender, 'send_to_chat_id', send_to_chat_id)

    return TelegramSender(
        bot=mock_telegram_bot, tg_config=mock_config_manager.get_telegram_config()
    )


@pytest.fixture
def mock_db_client(mock_config_manager):
    return DBClient(db_config=mock_config_manager.get_db_config())
