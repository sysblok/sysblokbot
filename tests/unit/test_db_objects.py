import pytest

from src.db import db_objects
from src.db.db_objects import TeamMember


class FakeSheetItem:
    def __init__(self, values):
        self.values = values

    def get_field_value(self, field_name):
        return self.values.get(field_name)


def test_team_member_from_dict_parses_telegram_id():
    member = TeamMember.from_dict(
        {
            "id": "1",
            "name": "Name",
            "status": "в команде",
            "curator": "Curator",
            "manager": "Manager",
            "telegram": "@username",
            "trello": "@trello",
            "focalboard": "@focalboard",
            "telegram_id": "123456789",
        }
    )

    assert member.telegram_id == 123456789
    assert member.to_dict()["telegram_id"] == 123456789


def test_team_member_from_dict_treats_empty_telegram_id_as_none():
    member = TeamMember.from_dict({"id": "1", "telegram_id": ""})

    assert member.telegram_id is None


def test_team_member_from_sheetfu_item_parses_telegram_id(monkeypatch):
    columns = {
        "sheets__team__id": "ID",
        "sheets__team__name": "Как вас зовут?",
        "sheets__team__status": "Статус",
        "sheets__team__curator": "Куратор (как автора)",
        "sheets__team__manager": "Менеджер",
        "sheets__team__telegram": "Телеграм",
        "sheets__team__trello": "Трелло",
        "sheets__focalboard": "Focalboard",
        "sheets__team__telegram_id": "Telegram ID",
    }
    monkeypatch.setattr(db_objects, "load", lambda key: columns[key])

    member = TeamMember.from_sheetfu_item(
        FakeSheetItem(
            {
                "ID": "1",
                "Как вас зовут?": "Name",
                "Статус": "в команде",
                "Куратор (как автора)": "Curator",
                "Менеджер": "Manager",
                "Телеграм": "@username",
                "Трелло": "@trello",
                "Focalboard": "@focalboard",
                "Telegram ID": "123456789",
            }
        )
    )

    assert member.telegram_id == 123456789


def test_team_member_from_sheetfu_item_treats_empty_telegram_id_as_none(monkeypatch):
    columns = {
        "sheets__team__id": "ID",
        "sheets__team__name": "Как вас зовут?",
        "sheets__team__status": "Статус",
        "sheets__team__curator": "Куратор (как автора)",
        "sheets__team__manager": "Менеджер",
        "sheets__team__telegram": "Телеграм",
        "sheets__team__trello": "Трелло",
        "sheets__focalboard": "Focalboard",
        "sheets__team__telegram_id": "Telegram ID",
    }
    monkeypatch.setattr(db_objects, "load", lambda key: columns[key])

    member = TeamMember.from_sheetfu_item(
        FakeSheetItem(
            {
                "ID": "1",
                "Telegram ID": "",
            }
        )
    )

    assert member.telegram_id is None


def test_team_member_from_sheetfu_item_fails_on_invalid_telegram_id(monkeypatch):
    columns = {
        "sheets__team__id": "ID",
        "sheets__team__name": "Как вас зовут?",
        "sheets__team__status": "Статус",
        "sheets__team__curator": "Куратор (как автора)",
        "sheets__team__manager": "Менеджер",
        "sheets__team__telegram": "Телеграм",
        "sheets__team__trello": "Трелло",
        "sheets__focalboard": "Focalboard",
        "sheets__team__telegram_id": "Telegram ID",
    }
    monkeypatch.setattr(db_objects, "load", lambda key: columns[key])

    with pytest.raises(ValueError):
        TeamMember.from_sheetfu_item(FakeSheetItem({"ID": "1", "Telegram ID": "#N/A"}))
