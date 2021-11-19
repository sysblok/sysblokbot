import pytest

import os

from conftest import TRELLO_TEST_DIR
from utils.json_loader import JsonLoader


json_loader = JsonLoader(os.path.join(TRELLO_TEST_DIR, 'expected'))


def test_init(mock_trello):
    pass


def test_board(mock_trello):
    board = mock_trello.get_board()
    json_loader.assert_equal(board.to_dict(), 'board.json')


def test_lists(mock_trello):
    lists = mock_trello.get_lists()
    json_loader.assert_equal([lst.to_dict() for lst in lists], 'lists.json')


def test_cards(mock_trello):
    cards = mock_trello.get_cards(['list_1', 'list_2', 'list_4'])
    json_loader.assert_equal([card.to_dict() for card in cards], 'cards.json')


def test_board_custom_fields(mock_trello):
    custom_field_types = mock_trello.get_board_custom_field_types()
    json_loader.assert_equal(
        [typ.to_dict() for typ in custom_field_types], 'board_custom_fields.json'
    )


def test_card_custom_fields(mock_trello):
    custom_fields = mock_trello.get_card_custom_fields(1)
    json_loader.assert_equal([fld.to_dict() for fld in custom_fields], 'card_custom_fields.json')


def test_card_actions(mock_trello):
    custom_fields = mock_trello.get_action_update_card(1)
    json_loader.assert_equal([fld.to_dict() for fld in custom_fields], 'card_actions.json')


def test_members(mock_trello):
    members = mock_trello.get_members()
    json_loader.assert_equal([member.to_dict() for member in members], 'members.json')
