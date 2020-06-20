import pytest


def test_init(mock_db_client):
    pass


def test_fetch_all(mock_db_client, mock_sheets_client):
    mock_db_client.fetch_all(mock_sheets_client)


def test_find_author_telegram_by_trello(mock_db_client, mock_sheets_client):
    mock_db_client.fetch_all(mock_sheets_client)
    assert mock_db_client.find_author_telegram_by_trello('@merwanrim') == '@rim'


def test_find_curators_by_author_trello(mock_db_client, mock_sheets_client):
    mock_db_client.fetch_all(mock_sheets_client)
    curators = mock_db_client.find_curators_by_author_trello('@merwanrim')
    assert len(curators) == 1
    assert curators[0].telegram == '@flo'


def test_find_curators_by_trello_label(mock_db_client, mock_sheets_client):
    mock_db_client.fetch_all(mock_sheets_client)
    curators = mock_db_client.find_curators_by_trello_label('Классицизм')
    assert len(curators) == 1
    assert curators[0].telegram == '@flo'