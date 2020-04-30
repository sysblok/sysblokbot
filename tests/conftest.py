import pytest

import json
import os

from deepdiff import DeepDiff


ROOT_TEST_DIR = os.path.abspath(os.path.dirname(__file__))
TRELLO_TEST_PATH = os.path.join(
    os.path.join(ROOT_TEST_DIR, 'static'), 'trello')
EXPECTED_TEST_PATH = os.path.join(
    os.path.join(ROOT_TEST_DIR, 'static'), 'expected')


@pytest.fixture
def mock_trello():

    def _make_request(_, uri):

        def load_json(filename):
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

    return _make_request


@pytest.fixture
def assert_equal():

    def _assert_equal(response, expected_filename):

        def load_json(filename):
            with open(os.path.join(EXPECTED_TEST_PATH, filename), 'r') as fin:
                return json.loads(fin.read())
        
        expected_response = load_json(expected_filename)
        assert not DeepDiff(response, expected_response)

    return _assert_equal
