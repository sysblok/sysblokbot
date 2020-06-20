import html
import logging

from datetime import datetime

from ..consts import TrelloCardColor, TrelloCustomFieldTypes


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
    def from_dict(cls, data):
        board = cls()
        try:
            board.id = data['id']
            board.name = html.escape(data['name'])
            board.url = data['shortUrl']
        except Exception as e:
            board._ok = False
            logger.error(f"Bad board json {data}: {e}")
        return board

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'url': self.url,
        }


class TrelloBoardLabel:
    def __init__(self):
        self.id = None
        self.name = None
        self.color = None

        self._ok = True

    def __bool__(self):
        return self._ok

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'BoardLabel<id={self.id}, name={self.name}, color={self.color}>'

    @classmethod
    def from_dict(cls, data):
        label = cls()
        try:
            label.id = data['id']
            label.name = html.escape(data['name'])
            label.color = data['color']
        except Exception as e:
            label._ok = False
            logger.error(f"Bad board label json {data}: {e}")
        return label

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color,
        }


class TrelloList:
    def __init__(self):
        self.id = None
        self.name = None
        self.board_id = None

        self._ok = True

    def __bool__(self):
        return self._ok

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'List<id={self.id}, name={self.name}>'

    @classmethod
    def from_dict(cls, data):
        trello_list = cls()
        try:
            trello_list.id = data['id']
            trello_list.name = html.escape(data['name'])
            trello_list.board_id = data['idBoard']
        except Exception as e:
            trello_list._ok = False
            logger.error(f"Bad list json {data}: {e}")
        return trello_list

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'idBoard': self.board_id,
        }


class TrelloCardLabel:
    def __init__(self):
        self.id = None
        self.name = None
        self.color = None

        self._ok = True

    def __bool__(self):
        return self._ok

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'CardLabel<name={self.name}, color={self.color}>'

    @classmethod
    def from_dict(cls, data):
        label = cls()
        try:
            label.id = data['id']
            label.name = html.escape(data['name'])
            label.color = TrelloCardColor(data['color'])
        except Exception as e:
            label._ok = False
            logger.error(f"Bad card label json {data}: {e}")
        return label

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color.value,
        }


class TrelloCard:
    def __init__(self):
        self.id = None
        self.name = None
        self.labels = []
        self.url = None
        self.due = None
        # TODO: move this to app state
        self.lst = None
        self.members = []

        self._ok = True

    def __bool__(self):
        return self._ok

    def __str__(self):
        return self.url

    def __repr__(self):
        return f'Card<id={self.id}, name={self.name}, url={self.url} members={self.members}>'

    @classmethod
    def from_dict(cls, data):
        card = cls()
        try:
            card.id = data['id']
            card.name = html.escape(data['name'])
            card.labels = [TrelloCardLabel.from_dict(label) for label in data['labels']]
            card.url = data['shortUrl']
            card.due = (datetime.strptime(data['due'], TIME_FORMAT)
                        if data['due'] else None)
        except Exception as e:
            card._ok = False
            logger.error(f"Bad card json {data}: {e}")
        return card

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'labels': [label.to_dict() for label in self.labels],
            'url': self.url,
            'due': datetime.strftime(self.due, TIME_FORMAT) if self.due else None,
            'list': self.lst.to_dict() if self.lst is not None else {},
            'members': [member.to_dict() for member in self.members],
        }


class TrelloCustomFieldType:
    def __init__(self):
        self.id = None
        self.name = None
        self.type = None
        self.options = None

        self._ok = True

    def __bool__(self):
        return self._ok

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'CustomFieldType<id={self.id}, name={self.name}, type={self.type}>'

    @classmethod
    def from_dict(cls, data):
        field_type = cls()
        try:
            field_type.id = data['id']
            field_type.name = html.escape(data['name'])
            field_type.type = TrelloCustomFieldTypes(data['type'])
            if field_type.type == TrelloCustomFieldTypes.LIST:
                field_type.options = {
                    option['id']: option['value']['text'] for option in data['options']
                }
        except Exception as e:
            field_type._ok = False
            logger.error(f"Bad field type json {data}: {e}")
        return field_type

    def to_dict(self):
        dct = {
            'id': self.id,
            'name': self.name,
            'type': self.type.value,
        }
        if self.type == TrelloCustomFieldTypes.LIST:
            dct['options'] = [
                {'id': idValue, 'value': {'text': value}}
                for idValue, value in self.options.items()
            ]
        return dct


class TrelloCustomField:
    def __init__(self):
        self.id = None
        self.value = None
        self.type_id = None

        self._ok = True
        self._custom_fields_type_config = None

    def __bool__(self):
        return self._ok

    def __str__(self):
        return self.value

    def __repr__(self):
        return f'CustomField<id={self.id}, value={self.value}, type_id={self.type_id}>'

    @classmethod
    def from_dict(cls, data, custom_fields_type_config):
        custom_field = cls()
        custom_field._custom_fields_type_config = custom_fields_type_config
        try:
            custom_field.id = data['id']
            custom_field.type_id = data['idCustomField']
            # TODO probably support other custom field value types
            if custom_fields_type_config[custom_field.type_id] == TrelloCustomFieldTypes.TEXT:
                custom_field.value = html.escape(data['value']['text'])
        except Exception as e:
            custom_field._ok = False
            logger.error(f"Bad custom field json {data}: {e}")
        return custom_field

    def to_dict(self):
        dct = {
            'id': self.id,
            'idCustomField': self.type_id,
        }
        # TODO probably support other custom field value types
        if self._custom_fields_type_config[self.type_id] == TrelloCustomFieldTypes.TEXT:
            dct['value'] = {'text': self.value}
        return dct


class TrelloActionCreateCard:
    def __init__(self):
        self.id = None
        self.date = None
        self.card_url = None
        self.list_id = None
        self.list_name = None

        self._ok = True

    def __bool__(self):
        return self._ok

    def __str__(self):
        return f'Card "{self.card_url}" created in {self.list_name}'

    def __repr__(self):
        return (
            f'ActionCreateCard<date={self.date}, card_url={self.card_url}, '
            f'list_id={self.list_id}>'
        )

    @classmethod
    def from_dict(cls, data):
        action = cls()
        try:
            assert data['type'] == 'createCard'
            action.id = data['id']
            action.date = datetime.strptime(data['date'], TIME_FORMAT)
            action.card_url = 'https://trello.com/c/' + data['data']['card']['shortLink']
            if 'list' in data['data']:
                action.list_id = data['data']['list'].get('id')
                action.list_name = data['data']['list'].get('name')
        except Exception as e:
            action._ok = False
            logger.error(f"Bad createCard action json {data}: {e}")
        return action

    def to_dict(self):
        return {
            'id': self.id,
            'date': datetime.strftime(self.date, TIME_FORMAT),
            'type': 'createCard',
            'data': {
                'card': {
                    'shortLink': self.card_url.split('/')[-1]
                },
                'list': {
                    'id': self.list_id,
                    'name': self.list_name,
                },
            }
        }


class TrelloActionUpdateCard:
    def __init__(self):
        self.id = None
        self.date = None
        # probably will update fields if need be
        self.card_url = None
        self.list_before_id = None
        self.list_before_name = None
        self.list_after_id = None
        self.list_after_name = None

        self._ok = True

    def __bool__(self):
        return self._ok

    def __str__(self):
        return f'Card "{self.card_url}" moved {self.list_before_name} -> {self.list_after_name}'

    def __repr__(self):
        return (
            f'ActionUpdateCard<date={self.date}, card_url={self.card_url}, '
            f'list_before_id={self.list_before_id}, list_after_name={self.list_after_id}>'
        )

    @classmethod
    def from_dict(cls, data):
        action = cls()
        try:
            assert data['type'] == 'updateCard'
            action.id = data['id']
            action.date = datetime.strptime(data['date'], TIME_FORMAT)
            action.card_url = 'https://trello.com/c/' + data['data']['card']['shortLink']
            if 'listBefore' in data['data']:
                action.list_before_id = data['data']['listBefore']['id']
                action.list_before_name = data['data']['listBefore']['name']
            if 'listAfter' in data['data']:
                action.list_after_id = data['data']['listAfter']['id']
                action.list_after_name = data['data']['listAfter']['name']
        except Exception as e:
            action._ok = False
            logger.error(f"Bad updateCard action json {data}: {e}")
        return action

    def to_dict(self):
        return {
            'id': self.id,
            'date': datetime.strftime(self.date, TIME_FORMAT),
            'type': 'updateCard',
            'data': {
                'card': {
                    'shortLink': self.card_url.split('/')[-1]
                },
                'listBefore': {
                    'id': self.list_before_id,
                    'name': self.list_before_name,
                },
                'listAfter': {
                    'id': self.list_after_id,
                    'name': self.list_after_name,
                }
            }
        }


class TrelloMember:
    def __init__(self):
        self.id = None
        self.username = None
        self.full_name = None

    def __str__(self):
        return self.username

    def __repr__(self):
        return f'Member<id={self.id}, name={self.username}, full name={self.full_name}>'

    def __eq__(self, other):
        return (isinstance(other, TrelloMember) and
                self.username == other.username)

    def __lt__(self, other):
        return (isinstance(other, TrelloMember) and
                self.username < other.username)

    def __hash__(self):
        return hash(self.username)

    @classmethod
    def from_dict(cls, data):
        member = cls()
        member.id = data['id']
        member.username = data['username']
        member.full_name = data['fullName']
        return member

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'fullName': self.full_name,
        }


class CardCustomFields:
    def __init__(self, card_id):
        self.card_id = card_id
        self.authors = None
        self.editors = None
        self.illustrators = None
        self.cover = None
        self.title = None
        self.google_doc = None
        self._data = None

    def __repr__(self):
        return f'CardCustomFields<id={self.card_id}, title={self.title}>'
