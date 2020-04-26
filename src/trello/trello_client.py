import json
import logging
import requests

from datetime import datetime


from ..utils.singleton import Singleton


logger = logging.getLogger(__name__)

BASE_URL = 'https://api.trello.com/1/'
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


class TrelloClient(Singleton):
    def __init__(self, config=None):
        if self.was_initialized():
            return

        self._trello_config = config
        self._update_from_config()

    def get_board(self):
        _, data = self._make_request(f'boards/{self.board_id}')
        return TrelloBoard.from_json(data)

    def get_board_custom_fields(self):
        _, data = self._make_request(f'boards/{self.board_id}/customFields')
        custom_field_types = [
            TrelloCustomFieldType.from_json(custom_field_type)
            for custom_field_type in data
        ]
        logger.debug(f'get_board_custom_fields: {custom_field_types}')
        return custom_field_types

    def get_lists(self):
        _, data = self._make_request(f'boards/{self.board_id}/lists')
        lists = [TrelloList.from_json(trello_list) for trello_list in data]
        logger.debug(f'get_lists: {lists}')
        return lists

    def get_cards(self, list_ids=None):
        if list_ids is not None and len(list_ids) == 1:
            _, data = self._make_request(f'lists/{list_ids[0]}/cards')
        else:
            _, data = self._make_request(f'boards/{self.board_id}/cards')
            if list_ids:
                data = [
                    card_dict for card_dict in data
                    if card_dict['idList'] in list_ids
                ]
        cards = []
        # TODO: move this to app state
        members = self.get_members()
        lists = self.get_lists()
        for card_dict in data:
            card = TrelloCard.from_json(card_dict)
            # TODO: move this to app state
            for trello_list in lists:
                if trello_list.id == card_dict['idList']:
                    card.list_name = trello_list.name
                    break
            else:
                logger.error(f"List name not found for {card}")
            # TODO: move this to app state
            if len(card_dict['idMembers']) > 0:
                for member in members:
                    if member.id in card_dict['idMembers']:
                        card.members.append(member.full_name)
                if len(card.members) == 0:
                    logger.error(f"Member username not found for {card}")
            cards.append(card)
        logger.debug(f'get_cards: {cards}')
        return cards

    def get_card_custom_fields(self, card_id):
        _, data = self._make_request(f'cards/{card_id}/customFieldItems')
        custom_fields = [
            TrelloCustomField.from_json(custom_field) for custom_field in data
        ]
        logger.debug(f'get_card_custom_fields: {custom_fields}')
        return custom_fields

    def get_members(self):
        _, data = self._make_request(f'boards/{self.board_id}/members')
        members = [TrelloMember.from_json(member) for member in data]
        logger.debug(f'get_members: {members}')
        return members

    def update_config(self, new_trello_config):
        """
        To be called after config automatic update.
        """
        self._trello_config = new_trello_config
        self._update_from_config()

    def _update_from_config(self):
        """Update attributes according to current self._trello_config"""
        self.api_key = self._trello_config['api_key']
        self.token = self._trello_config['token']
        self.board_id = self._trello_config['board_id']
        self.default_payload = {
            'key': self.api_key,
            'token': self.token,
        }

    def _make_request(self, uri):
        response = requests.get(
            f'{BASE_URL}{uri}',
            params=self.default_payload
        )
        logger.debug(f'{response.url}')
        return response.status_code, response.json()
