import pytest

from src.db.db_client import DBClient
from src.db.db_objects import TeamMember


@pytest.fixture(autouse=True)
def reset_db_client_singleton():
    DBClient.drop_instance()
    yield
    DBClient.drop_instance()


def test_init(mock_db_client):
    pass


def test_fetch_all(mock_db_client, mock_sheets_client):
    mock_db_client.fetch_all(mock_sheets_client)


def test_find_author_telegram_by_trello_reads_team_members(mock_db_client):
    session = mock_db_client.Session()
    session.add_all(
        [
            TeamMember(
                id="1",
                name="Trello Person",
                telegram="@TrelloTelegram",
                trello="@TrelloUser",
                focalboard="@DifferentFocalboardUser",
            ),
            TeamMember(
                id="2",
                name="Focalboard Person",
                telegram="@FocalboardTelegram",
                trello="@DifferentTrelloUser",
                focalboard="@FocalboardUser",
            ),
        ]
    )
    session.commit()

    assert (
        mock_db_client.find_author_telegram_by_trello(" trellouser ")
        == "@TrelloTelegram"
    )
    assert (
        mock_db_client.find_author_telegram_by_trello("@focalboarduser")
        == "@FocalboardTelegram"
    )
