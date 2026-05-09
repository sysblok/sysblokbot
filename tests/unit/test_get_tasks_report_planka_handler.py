from types import SimpleNamespace

import src.tg.handlers.get_tasks_report_handler as handler
from src.trello.trello_objects import TrelloBoard, TrelloCard, TrelloList, TrelloMember


class FakePlankaClient:
    def __init__(self):
        self.board_calls = []
        self.list_calls = []
        self.card_calls = []

    def get_boards_for_telegram_user(self, telegram_username, db_client):
        self.board_calls.append((telegram_username, db_client))
        return [_make_board("board_1", "Развитие")]

    def get_list(self, board_id, list_id):
        self.list_calls.append((board_id, list_id))
        return _make_list(list_id, "Selected list")

    def get_cards(self, list_id, board_id):
        self.card_calls.append((list_id, board_id))
        return [_make_card("card_1", "Card 1", ["manager"])]


class FakeAppContext:
    def __init__(self, planka_client):
        self.planka_client = planka_client
        self.db_client = SimpleNamespace()


def test_get_task_report_base_sets_planka_backend(monkeypatch):
    planka_client = FakePlankaClient()
    app_context = FakeAppContext(planka_client)
    replies = []

    monkeypatch.setattr(handler, "AppContext", lambda: app_context)
    monkeypatch.setattr(
        handler, "reply", lambda message, update: replies.append(message)
    )
    monkeypatch.setattr(
        handler,
        "load",
        lambda string_id, **kwargs: f"{string_id}:{kwargs.get('lists', '')}",
    )

    update = SimpleNamespace(effective_user=SimpleNamespace(username="tg_user"))
    tg_context = SimpleNamespace(chat_data={})

    handler._get_task_report_base(update, tg_context, advanced=False, use_planka=True)

    assert planka_client.board_calls == [("tg_user", app_context.db_client)]
    assert tg_context.chat_data["use_planka"] is True
    assert tg_context.chat_data["use_focalboard"] is False
    assert tg_context.chat_data["lists"] == [
        {"id": "board_1", "name": "Развитие", "url": None}
    ]
    assert replies == ["get_tasks_report_handler__choose_trello_board:1) Развитие"]


def test_generate_report_messages_uses_planka_client(monkeypatch):
    planka_client = FakePlankaClient()
    app_context = FakeAppContext(planka_client)

    monkeypatch.setattr(handler, "AppContext", lambda: app_context)
    monkeypatch.setattr(
        handler,
        "load",
        lambda string_id, **kwargs: _fake_load(string_id, **kwargs),
    )
    monkeypatch.setattr(
        handler,
        "paragraphs_to_messages",
        lambda paragraphs: ["\n".join(paragraphs)],
    )

    messages = handler.generate_report_messages(
        "board_1",
        "list_1",
        "Intro",
        add_labels=False,
        use_focalboard=False,
        use_planka=True,
    )

    assert planka_client.list_calls == [("board_1", "list_1")]
    assert planka_client.card_calls == [("list_1", "board_1")]
    assert messages == [
        "<b>Selected list</b>\nIntro\nmember:Manager (manager)\ncard:Card 1"
    ]


def _fake_load(string_id, **kwargs):
    if string_id == "common__bold_wrapper":
        return f"<b>{kwargs['arg']}</b>"
    if string_id == "get_tasks_report_handler__member":
        return f"member:{kwargs['username']}"
    if string_id == "get_tasks_report_handler__card":
        return f"card:{kwargs['name']}"
    if string_id == "get_tasks_report_handler__misc":
        return "misc"
    if string_id == "get_tasks_report_handler__card_deadline":
        return kwargs["due"]
    return string_id


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
    member.full_name = username.title()
    return member
