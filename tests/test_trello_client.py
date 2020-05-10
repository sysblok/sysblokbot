import pytest

from datetime import datetime
import json
import os

from src import config_manager
from src.trello.trello_client import TrelloClient


# TODO check milliseconds :)
TIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'


def test_board(monkeypatch, mock_trello, assert_equal):
    monkeypatch.setattr(TrelloClient, '_make_request', mock_trello)

    # TODO: check api keys etc
    trello = TrelloClient({
        'api_key': 'api_key',
        'token': 'token',
        'board_id': 'board_1'
    })
    board = trello.get_board()
    assert_equal(board.to_dict(), 'board.json')


def test_lists(monkeypatch, mock_trello, assert_equal):
    monkeypatch.setattr(TrelloClient, '_make_request', mock_trello)

    # TODO: check api keys etc
    trello = TrelloClient({
        'api_key': 'api_key',
        'token': 'token',
        'board_id': 'board_1'
    })
    lists = trello.get_lists()
    assert_equal([lst.to_dict() for lst in lists], 'lists.json')


def test_cards(monkeypatch, mock_trello, assert_equal):
    monkeypatch.setattr(TrelloClient, '_make_request', mock_trello)

    # TODO: check api keys etc
    trello = TrelloClient({
        'api_key': 'api_key',
        'token': 'token',
        'board_id': 'board_1'
    })
    cards = trello.get_cards(['list_1', 'list_2', 'list_4'])
    assert_equal([card.to_dict() for card in cards], 'cards.json')


def test_board_custom_fields(monkeypatch, mock_trello, assert_equal):
    monkeypatch.setattr(TrelloClient, '_make_request', mock_trello)

    # TODO: check api keys etc
    trello = TrelloClient({
        'api_key': 'api_key',
        'token': 'token',
        'board_id': 'board_1'
    })
    custom_field_types = trello.get_board_custom_field_types()
    assert_equal([typ.to_dict() for typ in custom_field_types], 'board_custom_fields.json')


def test_card_custom_fields(monkeypatch, mock_trello, assert_equal):
    monkeypatch.setattr(TrelloClient, '_make_request', mock_trello)

    # TODO: check api keys etc
    trello = TrelloClient({
        'api_key': 'api_key',
        'token': 'token',
        'board_id': 'board_1'
    })
    custom_fields = trello.get_card_custom_fields(1)
    assert_equal([fld.to_dict() for fld in custom_fields], 'card_custom_fields.json')


def test_members(monkeypatch, mock_trello, assert_equal):
    monkeypatch.setattr(TrelloClient, '_make_request', mock_trello)

    # TODO: check api keys etc
    trello = TrelloClient({
        'api_key': 'api_key',
        'token': 'token',
        'board_id': 'board_1'
    })
    members = trello.get_members()
    assert_equal([member.to_dict() for member in members], 'members.json')
