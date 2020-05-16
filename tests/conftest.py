import pytest

import json
import os

from deepdiff import DeepDiff
from typing import List, Dict


ROOT_TEST_DIR = os.path.abspath(os.path.dirname(__file__))
SHEETS_TEST_PATH = os.path.join(
    os.path.join(ROOT_TEST_DIR, 'static'), 'sheets')
TRELLO_TEST_PATH = os.path.join(
    os.path.join(ROOT_TEST_DIR, 'static'), 'trello')
EXPECTED_TEST_PATH = os.path.join(
    os.path.join(ROOT_TEST_DIR, 'static'), 'expected')


@pytest.fixture
def mock_trello():

    def _make_request(_, uri: str) -> (int, Dict):

        def load_json(filename: str) -> Dict:
            with open(os.path.join(TRELLO_TEST_PATH, filename), 'r') as fin:
                return json.loads(fin.read())

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
        elif uri.startswith('lists'):
            if uri.endswith('cards'):
                return 200, load_json('cards.json')

    return _make_request


@pytest.fixture
def assert_equal():

    def _assert_equal(response: Dict, expected_filename: str):

        def load_json(filename: str) -> Dict:
            with open(os.path.join(EXPECTED_TEST_PATH, filename), 'r') as fin:
                return json.loads(fin.read())

        expected_response = load_json(expected_filename)
        assert not DeepDiff(response, expected_response)

    return _assert_equal


def mock_sender(substring_list_to_check: List[str]):

    def send_to_chat_id(_, message_text: str, chat_id: int):
        for string in substring_list_to_check:
            assert string in message_text

    return send_to_chat_id


@pytest.fixture
def mock_config_manager():

    def get_latest_config(_):
        return {
            "telegram": {
                "token": "stub",
                "is_silent": False,
                "disable_web_page_preview": False,
                "admin_chat_ids": [],
                "manager_chat_ids": [],
                "important_events_recipients": [],
                "error_logs_recipients": []
            },
            "trello": {
                "api_key": "stub",
                "token": "stub",
                "board_id": "board_id"
            },
            "sheets": {
                "api_key_path": "stub",
                "authors_sheet_key": "authors_sheet_key",
                "curators_sheet_key": "curators_sheet_key",
                "post_registry_sheet_key": "post_registry_sheet_key",
                "rubrics_registry_sheet_key": "rubrics_registry_sheet_key"
            },
            "jobs": {}
        }

    return get_latest_config


@pytest.fixture
def mock_sheets_client(mock_config_manager):

    def _update_from_config(self):
        """Update attributes according to current self._sheets_config"""
        self._sheets_config = mock_config_manager(None)['sheets']
        self.authors_sheet_key = self._sheets_config['authors_sheet_key']
        self.curators_sheet_key = self._sheets_config['curators_sheet_key']
        self.post_registry_sheet_key = self._sheets_config['post_registry_sheet_key']
        self.rubrics_registry_sheet_key = self._sheets_config['rubrics_registry_sheet_key']

    def _parse_gs_res(_, title_key_map: Dict, sheet_key: str) -> List[Dict]:

        def load_json(filename: str) -> Dict:
            with open(os.path.join(SHEETS_TEST_PATH, filename), 'r') as fin:
                return json.loads(fin.read())

        if sheet_key == 'authors_sheet_key':
            return load_json('authors_sheet.json')
        elif sheet_key == 'curators_sheet_key':
            return load_json('curators_sheet.json')

    return _update_from_config, _parse_gs_res
