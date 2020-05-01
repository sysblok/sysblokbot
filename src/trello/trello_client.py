import logging
import requests


from . import trello_objects as objects
from ..utils.singleton import Singleton


logger = logging.getLogger(__name__)

BASE_URL = 'https://api.trello.com/1/'


class TrelloClient(Singleton):
    def __init__(self, config=None):
        if self.was_initialized():
            return

        self._trello_config = config
        self._update_from_config()
        logger.info('TrelloClient successfully initialized')

    def get_board(self):
        _, data = self._make_request(f'boards/{self.board_id}')
        return objects.TrelloBoard.from_dict(data)

    def get_lists(self):
        _, data = self._make_request(f'boards/{self.board_id}/lists')
        lists = [
            objects.TrelloList.from_dict(trello_list) for trello_list in data
        ]
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
            card = objects.TrelloCard.from_dict(card_dict)
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
                        card.members.append(member)
                if len(card.members) == 0:
                    logger.error(f"Member username not found for {card}")
            cards.append(card)
        logger.debug(f'get_cards: {cards}')
        return cards

    def get_board_custom_field_types(self):
        _, data = self._make_request(f'boards/{self.board_id}/customFields')
        custom_field_types = [
            objects.TrelloCustomFieldType.from_dict(custom_field_type)
            for custom_field_type in data
        ]
        logger.debug(f'get_board_custom_field_types: {custom_field_types}')
        return custom_field_types

    def get_card_custom_fields_dict(self, card_id):
        _, data = self._make_request(f'cards/{card_id}/customFieldItems')
        custom_fields_dict = {}
        for custom_field in data:
            custom_field = objects.TrelloCustomField.from_dict(custom_field)
            custom_fields_dict[custom_field.type_id] = custom_field
        logger.debug(f'get_card_custom_fields_dict: {custom_fields_dict}')
        return custom_fields_dict

    def get_members(self):
        _, data = self._make_request(f'boards/{self.board_id}/members')
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

    def _make_request(self, uri):
        response = requests.get(
            f'{BASE_URL}{uri}',
            params=self.default_payload
        )
        logger.debug(f'{response.url}')
        return response.status_code, response.json()
