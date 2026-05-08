from types import SimpleNamespace

import pytest

import src.jobs.board_my_cards_razvitie_job as job_module
from src.jobs.board_my_cards_razvitie_job import BoardMyCardsRazvitieJob
from src.trello.trello_objects import TrelloBoard, TrelloCard, TrelloList, TrelloMember


class FakeDBClient:
    def __init__(self, planka_username):
        self.planka_username = planka_username
        self.lookup_calls = []

    def find_focalboard_username_by_telegram_username(self, telegram_username):
        self.lookup_calls.append(telegram_username)
        return self.planka_username


class FakePlankaClient:
    def __init__(self, boards, lists, cards_by_list):
        self.boards = boards
        self.lists = lists
        self.cards_by_list = cards_by_list
        self.board_calls = []
        self.list_calls = []
        self.card_calls = []

    def get_boards_for_telegram_user(self, telegram_username, db_client):
        self.board_calls.append((telegram_username, db_client))
        return self.boards

    def get_lists(self, board_id, sorted=False):
        self.list_calls.append((board_id, sorted))
        return self.lists

    def get_cards(self, list_id, board_id):
        self.card_calls.append((list_id, board_id))
        return self.cards_by_list.get(list_id, [])


class FocalboardShouldNotBeUsed:
    def __getattr__(self, name):
        raise AssertionError(f"Focalboard client should not be used: {name}")


class FakeSend:
    def __init__(self, username):
        self.messages = []
        self.update = SimpleNamespace(
            message=SimpleNamespace(chat=SimpleNamespace(username=username))
        )

    def __call__(self, message):
        self.messages.append(message)


@pytest.fixture(autouse=True)
def patch_text_helpers(monkeypatch):
    def fake_make_cards_text(cards, need_label, app_context):
        return [f"card:{card.name}" for card in cards]

    def fake_load(string_id, **kwargs):
        assert string_id == "focalboard__my_cards_razvitie_job__text"
        return f"REPORT\n{kwargs['data']}"

    monkeypatch.setattr(job_module, "_make_cards_text", fake_make_cards_text)
    monkeypatch.setattr(job_module, "load", fake_load)


def test_execute_uses_planka_and_filters_manager_cards():
    db_client = FakeDBClient("@Manager")
    lists = [
        _make_list("list_start", "Список задач"),
        _make_list("list_planned", "Запланировано"),
        _make_list("list_doing", "В работе"),
        _make_list("list_end", "Разделитель"),
        _make_list("list_after", "После разделителя"),
    ]
    manager_card = _make_card("card_manager", "Manager card", ["manager"])
    other_card = _make_card("card_other", "Other card", ["other"])
    planka_client = FakePlankaClient(
        boards=[
            _make_board("board_other", "Другая"),
            _make_board("board_1", "СБъ. Развитие"),
        ],
        lists=lists,
        cards_by_list={
            "list_planned": [manager_card, other_card],
            "list_doing": [other_card],
            "list_after": [manager_card],
        },
    )
    app_context = SimpleNamespace(
        db_client=db_client,
        planka_client=planka_client,
        focalboard_client=FocalboardShouldNotBeUsed(),
    )
    send = FakeSend("tg_user")

    BoardMyCardsRazvitieJob._execute(app_context, send, called_from_handler=True)

    assert db_client.lookup_calls == ["@tg_user"]
    assert planka_client.board_calls == [("tg_user", db_client)]
    assert planka_client.list_calls == [("board_1", True)]
    assert planka_client.card_calls == [
        ("list_planned", "board_1"),
        ("list_doing", "board_1"),
    ]
    assert send.messages == ["REPORT\n📜 <b>Запланировано</b>\ncard:Manager card\n"]


def test_execute_raises_when_planka_username_is_missing():
    app_context = SimpleNamespace(
        db_client=FakeDBClient(None),
        planka_client=FakePlankaClient([], [], {}),
        focalboard_client=FocalboardShouldNotBeUsed(),
    )
    send = FakeSend("tg_user")

    with pytest.raises(ValueError, match="Planka username not found"):
        BoardMyCardsRazvitieJob._execute(app_context, send, called_from_handler=True)


def test_execute_raises_when_status_list_sentinel_is_missing():
    app_context = SimpleNamespace(
        db_client=FakeDBClient("manager"),
        planka_client=FakePlankaClient(
            boards=[_make_board("board_1", "СБъ. Развитие")],
            lists=[
                _make_list("list_start", "Список задач"),
                _make_list("list_planned", "Запланировано"),
            ],
            cards_by_list={},
        ),
        focalboard_client=FocalboardShouldNotBeUsed(),
    )
    send = FakeSend("tg_user")

    with pytest.raises(ValueError, match="Разделитель"):
        BoardMyCardsRazvitieJob._execute(app_context, send, called_from_handler=True)


def _make_board(board_id, name):
    board = TrelloBoard()
    board.id = board_id
    board.name = name
    return board


def _make_list(list_id, name):
    trello_list = TrelloList()
    trello_list.id = list_id
    trello_list.name = name
    trello_list.board_id = "board_1"
    return trello_list


def _make_card(card_id, name, usernames):
    card = TrelloCard()
    card.id = card_id
    card.name = name
    card.url = f"https://planka.example.com/cards/{card_id}"
    card.members = [_make_member(username) for username in usernames]
    return card


def _make_member(username):
    member = TrelloMember()
    member.id = username
    member.username = username
    member.full_name = username
    return member
