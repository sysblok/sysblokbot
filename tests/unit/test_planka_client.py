import os

import pytest
from conftest import STATIC_TEST_DIR
from utils.json_loader import JsonLoader

from src.planka.planka_client import PlankaClient

PLANKA_TEST_DIR = os.path.join(STATIC_TEST_DIR, "planka")


class FakeDBClient:
    def __init__(self, focalboard_username):
        self.focalboard_username = focalboard_username
        self.telegram_username = None

    def find_focalboard_username_by_telegram_username(self, telegram_username):
        self.telegram_username = telegram_username
        return self.focalboard_username


@pytest.fixture(autouse=True)
def drop_planka_client():
    PlankaClient.drop_instance()
    yield
    PlankaClient.drop_instance()


@pytest.fixture
def planka_config():
    return {
        "url": "https://planka.example.com",
        "api_key": "stub-api-key",
        "board_id": "board_razvitie",
    }


@pytest.fixture
def mock_planka(monkeypatch, planka_config):
    loader = JsonLoader(PLANKA_TEST_DIR)
    requests = []

    def _make_request(_, uri, payload=None):
        requests.append(uri)
        if uri == "projects":
            return 200, loader.load_json("projects.json")
        if uri == "boards/board_razvitie":
            return 200, loader.load_json("board_razvitie.json")
        if uri == "boards/board_private":
            return 200, loader.load_json("board_private.json")
        raise AssertionError(f"Unexpected Planka request: {uri}")

    monkeypatch.setattr(PlankaClient, "_make_request", _make_request)
    client = PlankaClient(planka_config=planka_config)
    client.requests = requests
    return client


def test_init(planka_config):
    client = PlankaClient(planka_config=planka_config)

    assert client.url == "https://planka.example.com/"
    assert client.api_url == "https://planka.example.com/api/"
    assert client.headers["X-Api-Key"] == "stub-api-key"


def test_boards_for_user(mock_planka):
    boards = mock_planka.get_boards_for_user()

    assert [board.to_dict() for board in boards] == [
        {
            "id": "board_razvitie",
            "name": "Развитие",
            "url": "https://planka.example.com/boards/board_razvitie",
        },
        {
            "id": "board_private",
            "name": "Private board",
            "url": "https://planka.example.com/boards/board_private",
        },
    ]


def test_boards_for_telegram_user_filters_by_existing_focalboard_mapping(mock_planka):
    boards = mock_planka.get_boards_for_telegram_user(
        "tg_user", FakeDBClient("@manager")
    )

    assert [board.id for board in boards] == ["board_razvitie"]


def test_boards_for_telegram_user_returns_empty_without_mapping(mock_planka):
    boards = mock_planka.get_boards_for_telegram_user("tg_user", FakeDBClient(None))

    assert boards == []
    assert mock_planka.requests == []


def test_sorted_lists_include_active_lists_only(mock_planka):
    lists = mock_planka.get_lists(sorted=True)

    assert [item.to_dict() for item in lists] == [
        {"id": "list_first", "name": "First", "idBoard": "board_razvitie"},
        {"id": "list_second", "name": "Second", "idBoard": "board_razvitie"},
    ]


def test_get_list(mock_planka):
    trello_list = mock_planka.get_list("board_razvitie", "list_first")

    assert trello_list.to_dict() == {
        "id": "list_first",
        "name": "First",
        "idBoard": "board_razvitie",
    }


def test_get_list_raises_for_unknown_list(mock_planka):
    with pytest.raises(ValueError, match="List unknown not found"):
        mock_planka.get_list("board_razvitie", "unknown")


def test_cards_accept_single_list_id_string(mock_planka):
    cards = mock_planka.get_cards("list_first")

    assert [card.to_dict() for card in cards] == [
        {
            "id": "card_planka",
            "name": "Implement Planka",
            "labels": [
                {
                    "id": "label_feature",
                    "name": "Feature",
                    "color": "unknown",
                }
            ],
            "url": "https://planka.example.com/cards/card_planka",
            "due": "2026-05-09T10:15:00.000000Z",
            "list": {
                "id": "list_first",
                "name": "First",
                "idBoard": "board_razvitie",
            },
            "members": [
                {
                    "id": "user_manager",
                    "username": "manager",
                    "fullName": "Manager User",
                }
            ],
        }
    ]


def test_cards_accept_list_id_iterable(mock_planka):
    cards = mock_planka.get_cards(["list_first", "list_second"])

    assert [card.id for card in cards] == ["card_planka", "card_tests"]
    assert [card.lst.id for card in cards] == ["list_first", "list_second"]


def test_board_details_are_cached_for_current_job_loop(mock_planka):
    mock_planka.get_cards("list_first")
    mock_planka.get_cards("list_second")

    assert mock_planka.requests.count("boards/board_razvitie") == 1
