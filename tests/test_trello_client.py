import pytest

from datetime import datetime
import json
import os

from src import config_manager
from src.trello.trello_client import TrelloClient



# TODO check milliseconds :)
TIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'


def test_board(monkeypatch, mock_trello):
    monkeypatch.setattr(TrelloClient, '_make_request', mock_trello)

    # TODO: check api keys etc
    trello = TrelloClient({
        'api_key': 'api_key',
        'token': 'token',
        'board_id': 'board_1'
    })
    board = trello.get_board()
    assert board
    assert board.id == 'board_1'
    assert board.name == 'Редакция (тест)'
    assert board.url == 'https://trello.com/b/test_board_url'


def test_lists(monkeypatch, mock_trello):
    monkeypatch.setattr(TrelloClient, '_make_request', mock_trello)

    # TODO: check api keys etc
    trello = TrelloClient({
        'api_key': 'api_key',
        'token': 'token',
        'board_id': 'board_1'
    })
    lists = trello.get_lists()
    assert len(lists) == 3
    for trello_list in lists:
        assert trello_list
        assert trello_list.id.startswith('list_')


def test_cards(monkeypatch, mock_trello):
    monkeypatch.setattr(TrelloClient, '_make_request', mock_trello)

    # TODO: check api keys etc
    trello = TrelloClient({
        'api_key': 'api_key',
        'token': 'token',
        'board_id': 'board_1'
    })
    cards = trello.get_cards(['list_1', 'list_2', 'list_4'])
    assert len(cards) == 2
    print(cards[0], cards[1]._ok)
    assert cards[0] and cards[1]
    cards.sort(key=lambda card: card.id)

    card = cards[0]
    assert card.__dict__ == None
    assert card.id == 'card_1'
    assert card.name == 'Open Memory Map'
    assert card.labels == ['История']
    assert card.url == 'https://trello.com/c/card_1'
    assert datetime.strftime(card.due, TIME_FORMAT) == '2020-06-18T09:00:00Z'
    assert card.list_name == 'Готовая тема'
    assert len(card.members) == 0

    card = cards[1]
    assert card.id == 'card_2'
    assert card.name == 'тестовая карточка'
    assert len(card.labels) == 0
    assert card.url == 'https://trello.com/c/card_2'
    assert card.due is None
    assert card.list_name == 'Редактору'
    assert card.members == ['Paulin Matavina']


def test_board_custom_fields(monkeypatch, mock_trello):
    monkeypatch.setattr(TrelloClient, '_make_request', mock_trello)

    # TODO: check api keys etc
    trello = TrelloClient({
        'api_key': 'api_key',
        'token': 'token',
        'board_id': 'board_1'
    })
    custom_field_types = trello.get_board_custom_field_types()
    # TODO: better checks -- e.g. match with response json?
    assert len(custom_field_types) == 5
    for i, custom_field in enumerate(sorted(custom_field_types,
                                            key=lambda field: field.id)):
        assert custom_field.id == f'type_{i}'


def test_card_custom_fields(monkeypatch, mock_trello):
    monkeypatch.setattr(TrelloClient, '_make_request', mock_trello)

    # TODO: check api keys etc
    trello = TrelloClient({
        'api_key': 'api_key',
        'token': 'token',
        'board_id': 'board_1'
    })
    custom_fields = trello.get_card_custom_fields_dict(1)
    # TODO: better checks -- e.g. match with response json?
    assert len(custom_fields) == 3
    for i, custom_field in enumerate(sorted(custom_fields.values(),
                                            key=lambda field: field.id)):
        assert custom_field.id == f'field_{i}'


def test_members(monkeypatch, mock_trello):
    monkeypatch.setattr(TrelloClient, '_make_request', mock_trello)

    # TODO: check api keys etc
    trello = TrelloClient({
        'api_key': 'api_key',
        'token': 'token',
        'board_id': 'board_1'
    })
    members = trello.get_members()
    assert len(members) == 1
    member = members[0]
    assert member
    assert member.id == 'member_1'
    assert member.username == 'paulinmatavina'
    assert member.full_name == 'Paulin Matavina'
