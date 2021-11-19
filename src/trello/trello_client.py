import json
import logging
import requests
from typing import List
from urllib.parse import quote, urljoin

from . import trello_objects as objects
from ..consts import TrelloListAlias, TrelloCustomFieldTypes, TrelloCustomFieldTypeAlias
from ..strings import load
from ..utils.singleton import Singleton

logger = logging.getLogger(__name__)

BASE_URL = 'https://api.trello.com/1/'


class TrelloClient(Singleton):
    def __init__(self, trello_config=None):
        if self.was_initialized():
            return

        self._trello_config = trello_config
        self._update_from_config()
        logger.info('TrelloClient successfully initialized')

    def get_board(self, board_id=None):
        if not board_id:
            board_id = self.board_id
        _, data = self._make_request(f'boards/{board_id}')
        return objects.TrelloBoard.from_dict(data)

    def get_board_by_url(self, board_url):
        # Safari may copy unquoted url with cyrillic symbols
        board_url = quote(board_url, safe=':/%')
        _, data = self._make_request(f'members/me/boards')
        for board in data:
            if board.get('url') == board_url:
                return objects.TrelloBoard.from_dict(board)
        raise ValueError(f'Board {board_url} not found!')

    def get_board_labels(self, board_id=None):
        if not board_id:
            board_id = self.board_id
        _, data = self._make_request(f'boards/{board_id}/labels')
        labels = [
            objects.TrelloBoardLabel.from_dict(label) for label in data
        ]
        logger.debug(f'get_board_labels: {labels}')
        return labels

    def get_boards_for_user(self, user_id=None):
        _, data = self._make_request(f'members/me/boards')
        boards = [
            objects.TrelloBoard.from_dict(label) for label in data
        ]
        logger.debug(f'get_boards_for_user: {boards}')
        return boards

    def get_lists(self, board_id=None):
        if not board_id:
            board_id = self.board_id
        _, data = self._make_request(f'boards/{board_id}/lists')
        lists = [
            objects.TrelloList.from_dict(trello_list) for trello_list in data
        ]
        logger.debug(f'get_lists: {lists}')
        return lists

    def get_list(self, list_id):
        _, data = self._make_request(f'lists/{list_id}')
        lst = objects.TrelloList.from_dict(data)
        logger.debug(f'get_list: {list}')
        return lst

    def get_cards(self, list_ids=None, board_id=None):
        if not board_id:
            board_id = self.board_id
        if list_ids is not None and len(list_ids) == 1:
            _, data = self._make_request(f'lists/{list_ids[0]}/cards')
        else:
            _, data = self._make_request(f'boards/{board_id}/cards')
            if list_ids:
                data = [
                    card_dict for card_dict in data
                    if card_dict['idList'] in list_ids
                ]
        cards = []
        # TODO: move this to app state
        members = self.get_members(board_id)
        lists = self.get_lists(board_id)
        for card_dict in data:
            card = objects.TrelloCard.from_dict(card_dict)
            # TODO: move this to app state
            for trello_list in lists:
                if trello_list.id == card_dict['idList']:
                    card.lst = trello_list
                    break
            else:
                logger.error(f"List name not found for {card}")
            # TODO: move this to app state
            if len(card_dict['idMembers']) > 0:
                for member in members:
                    if member.id in card_dict['idMembers']:
                        card.members.append(member)
                if len(card.members) == 0:
                    logger.error(f"Member username not found for {card}")
            cards.append(card)
        logger.debug(f'get_cards: {cards}')
        return cards

    def get_board_custom_field_types(self, board_id=None):
        if not board_id:
            board_id = self.board_id
        _, data = self._make_request(f'boards/{board_id}/customFields')
        custom_field_types = [
            objects.TrelloCustomFieldType.from_dict(custom_field_type)
            for custom_field_type in data
        ]
        logger.debug(f'get_board_custom_field_types: {custom_field_types}')
        return custom_field_types

    def get_card_custom_fields(self, card_id: str) -> List[objects.TrelloCustomField]:
        _, data = self._make_request(f'cards/{card_id}/customFieldItems')
        custom_fields = [
            objects.TrelloCustomField.from_dict(custom_field, self.custom_fields_type_config)
            for custom_field in data
        ]
        logger.debug(f'get_card_custom_fields: {custom_fields}')
        return custom_fields

    def get_card_custom_fields_dict(self, card_id):
        custom_fields = self.get_card_custom_fields(card_id)
        custom_fields_dict = {}
        for alias, type_id in self.custom_fields_config.items():
            suitable_fields = [fld for fld in custom_fields if fld.type_id == type_id]
            if len(suitable_fields) > 0:
                custom_fields_dict[alias] = suitable_fields[0]
        return custom_fields_dict

    def get_custom_fields(self, card_id: str) -> objects.CardCustomFields:
        # TODO: think about better naming
        card_fields_dict = self.get_card_custom_fields_dict(card_id)
        card_fields = objects.CardCustomFields(card_id)
        card_fields._data = card_fields_dict
        card_fields.authors = (
            [
                author.strip() for author in
                card_fields_dict[TrelloCustomFieldTypeAlias.AUTHOR].value.split(',')
            ]
            if TrelloCustomFieldTypeAlias.AUTHOR in card_fields_dict else []
        )
        card_fields.editors = (
            [
                editor.strip() for editor in
                card_fields_dict[TrelloCustomFieldTypeAlias.EDITOR].value.split(',')
                ]
            if TrelloCustomFieldTypeAlias.EDITOR in card_fields_dict else []
        )
        card_fields.illustrators = (
            [
                illustrator.strip() for illustrator in
                card_fields_dict[TrelloCustomFieldTypeAlias.ILLUSTRATOR].value.split(',')
            ]
            if TrelloCustomFieldTypeAlias.ILLUSTRATOR in card_fields_dict else []
        )
        card_fields.cover = (
            card_fields_dict[TrelloCustomFieldTypeAlias.COVER].value
            if TrelloCustomFieldTypeAlias.COVER in card_fields_dict else None
        )
        card_fields.google_doc = (
            card_fields_dict[TrelloCustomFieldTypeAlias.GOOGLE_DOC].value
            if TrelloCustomFieldTypeAlias.GOOGLE_DOC in card_fields_dict else None
        )
        card_fields.title = (
            card_fields_dict[TrelloCustomFieldTypeAlias.TITLE].value
            if TrelloCustomFieldTypeAlias.TITLE in card_fields_dict else None
        )
        return card_fields

    def set_card_custom_field(self, card_id, field_alias, value):
        data = {"value": {"text": value}}
        field_id = self.custom_fields_config[field_alias]
        code = self._make_put_request(
            f'cards/{card_id}/customField/{field_id}/item', data=data
        )
        logger.debug(f'set_card_custom_field: {code}')

    def get_action_create_card(self, card_id):
        _, data = self._make_request(
            f'cards/{card_id}/actions', payload={'filter': 'createCard'}
        )
        card_actions = [
            objects.TrelloActionCreateCard.from_dict(action)
            for action in data
            if action['type'] == 'createCard'
        ]
        logger.debug(f'get_action_create_card: {card_actions}')
        return card_actions

    def get_action_create_cards(self, card_ids):
        card_actions = {}
        for card_id in card_ids:
            card_actions[card_id] = self.get_action_create_card(card_id)
        return card_actions

    def get_action_update_card(self, card_id):
        _, data = self._make_request(
            f'cards/{card_id}/actions', payload={'filter': 'updateCard'}
        )
        card_actions = [
            objects.TrelloActionUpdateCard.from_dict(action)
            for action in data
            if action['type'] == 'updateCard'
        ]
        logger.debug(f'get_action_update_card: {card_actions}')
        return card_actions

    def get_action_update_cards(self, card_ids):
        card_actions = {}
        for card_id in card_ids:
            card_actions[card_id] = self.get_action_update_card(card_id)
        return card_actions

    def get_members(self, board_id=None) -> List[objects.TrelloMember]:
        if not board_id:
            board_id = self.board_id
        _, data = self._make_request(f'boards/{board_id}/members')
        members = [objects.TrelloMember.from_dict(member) for member in data]
        logger.debug(f'get_members: {members}')
        return members

    def update_config(self, new_trello_config):
        """To be called after config automatic update"""
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
        # TODO(alexeyqu): move to DB
        lists = self.get_lists()
        self.lists_config = self._fill_alias_id_map(lists, TrelloListAlias)
        custom_field_types = self.get_board_custom_field_types()
        self.custom_fields_type_config = self._fill_id_type_map(
            custom_field_types, TrelloCustomFieldTypes
        )
        self.custom_fields_config = self._fill_alias_id_map(
            custom_field_types, TrelloCustomFieldTypeAlias
        )

    def get_list_id_from_aliases(self, list_aliases):
        list_ids = [
            self.lists_config[alias] for alias in list_aliases if alias in self.lists_config
        ]
        if len(list_ids) != len(list_aliases):
            logger.error(
                f'list_ids not found for aliases: '
                f'{[alias for alias in list_aliases if alias not in self.lists_config]}'
            )
        return list_ids

    def _fill_alias_id_map(self, items, item_enum):
        result = {}
        for alias in item_enum:
            suitable_items = [item for item in items if item.name.startswith(load(alias.value))]
            if len(suitable_items) > 1:
                raise ValueError(f'Enum {item_enum.__name__} name {alias.value} is ambiguous!')
            if len(suitable_items) > 0:
                result[alias] = suitable_items[0].id
        return result

    def _fill_id_type_map(self, items, item_enum):
        result = {}
        for item in items:
            result[item.id] = TrelloCustomFieldTypes(item.type)
        return result

    def _make_request(self, uri, payload={}):
        payload.update(self.default_payload)
        response = requests.get(
            urljoin(BASE_URL, uri),
            params=payload,
        )
        logger.debug(f'{response.url}')
        return response.status_code, response.json()

    def _make_put_request(self, uri, data={}):
        response = requests.put(
            urljoin(BASE_URL, uri),
            params=self.default_payload,
            data=json.dumps(data),
            headers={'Content-Type': 'application/json'},
        )
        logger.debug(f'{response.url}')
        return response.status_code
