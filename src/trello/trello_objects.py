import logging

from datetime import datetime


logger = logging.getLogger(__name__)

TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'


class TrelloBoard:
    def __init__(self):
        self.id = None
        self.name = None
        self.url = None

        self._ok = True

    def __bool__(self):
        return self._ok

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'Board<id={self.id}, name={self.name}, url={self.url}>'

    @classmethod
    def from_json(cls, data):
        board = cls()
        try:
            board.id = data['id']
            board.name = data['name']
            board.url = data['shortUrl']
        except Exception:
            board._ok = False
            logger.error(f"Bad board json {data}")
        return board


class TrelloList:
    def __init__(self):
        self.id = None
        self.name = None

        self._ok = True

    def __bool__(self):
        return self._ok

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'List<id={self.id}, name={self.name}>'

    @classmethod
    def from_json(cls, data):
        trello_list = cls()
        try:
            trello_list.id = data['id']
            trello_list.name = data['name']
        except Exception:
            trello_list._ok = False
            logger.error(f"Bad list json {data}")
        return trello_list


class TrelloCard:
    def __init__(self):
        self.id = None
        self.name = None
        self.labels = []
        self.url = None
        self.due = None
        # TODO: move this to app state
        self.list_name = None
        self.members = []

        self._ok = True

    def __bool__(self):
        return self._ok

    def __str__(self):
        return self.url

    def __repr__(self):
        return f'Card<id={self.id}, name={self.name}, url={self.url} \
members={self.members}>'

    @classmethod
    def from_json(cls, data):
        card = cls()
        try:
            card.id = data['id']
            card.name = data['name']
            card.labels = [label['name'] for label in data['labels']]
            card.url = data['shortUrl']
            card.due = (datetime.strptime(data['due'], TIME_FORMAT)
                        if data['due'] else None)
        except Exception:
            card._ok = False
            logger.error(f"Bad card json {data}")
        return card


class TrelloCustomFieldType:
    def __init__(self):
        self.id = None
        self.name = None

        self._ok = True

    def __bool__(self):
        return self._ok

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'CustomFieldType<id={self.id}, name={self.name}>'

    @classmethod
    def from_json(cls, data):
        field_type = cls()
        try:
            field_type.id = data['id']
            field_type.name = data['name']
        except Exception:
            field_type._ok = False
            logger.error(f"Bad field type json {data}")
        return field_type


class TrelloCustomField:
    def __init__(self):
        self.id = None
        self.value = None
        self.type_id = None

        self._ok = True

    def __bool__(self):
        return self._ok

    def __str__(self):
        return self.value

    def __repr__(self):
        return f'CustomField<id={self.id}, value={self.value}, \
type_id={self.type_id}>'

    @classmethod
    def from_json(cls, data):
        custom_field = cls()
        try:
            custom_field.id = data['id']
            custom_field.value = data['value']['text']
            custom_field.type_id = data['idCustomField']
        except Exception:
            custom_field._ok = False
            logger.error(f"Bad custom field json {data}")
        return custom_field


class TrelloMember:
    def __init__(self):
        self.id = None
        self.username = None
        self.full_name = None

    def __str__(self):
        return self.username

    def __repr__(self):
        return f'Member<id={self.id}, name={self.username}, \
            full name={self.full_name}>'

    def __eq__(self, other):
        return (isinstance(other, TrelloMember) and
                self.username == other.username)

    def __lt__(self, other):
        return (isinstance(other, TrelloMember) and
                self.username < other.username)

    def __hash__(self):
        return hash(self.username)

    @classmethod
    def from_json(cls, data):
        member = cls()
        member.id = data['id']
        member.username = data['username']
        member.full_name = data['fullName']
        return member