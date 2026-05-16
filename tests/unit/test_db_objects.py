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
