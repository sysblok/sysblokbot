import json
import logging
import requests

from datetime import datetime


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
        return f'Board<id={self.id}, name={self.name}, url={self.url}>'

    @classmethod
    def from_json(cls, data):
        board = cls()
        try:
            board.id = data['id']
            board.name = data['name']
            board.url = data['shortUrl']
        except:
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
        return f'List<id={self.id}, name={self.name}>'

    @classmethod
    def from_json(cls, data):
        trello_list = cls()
        try:
            trello_list.id = data['id']
            trello_list.name = data['name']
        except:
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
        return f'Card<id={self.id}, name={self.name}, url={self.url}>'

    @classmethod
    def from_json(cls, data):
        card = cls()
        try:
            card.id = data['id']
            card.name = data['name']
            card.labels = [label['name'] for label in data['labels']]
            card.url = data['shortUrl']
            card.due = datetime.strptime(data['due'], TIME_FORMAT) if data['due'] else None
        except:
            card._ok = False
            logger.error(f"Bad card json {data}")
        return card


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
        return isinstance(other, TrelloMember) and self.username == other.username
    
    def __lt__(self, other):
        return isinstance(other, TrelloMember) and self.username < other.username

    def __hash__(self):
        return hash(self.username)

    @classmethod
    def from_json(cls, data):
        member = cls()
        member.id = data['id']
        member.username = data['username']
        member.full_name = data['fullName']
        return member


class TrelloClient:
    def __init__(self, config):
        self._trello_config = config
        self._update_from_config()        

    def get_board(self):
        _, data = self._make_request(f'boards/{self.board_id}')
        return TrelloBoard.from_json(data)

    def get_lists(self):
        _, data = self._make_request(f'boards/{self.board_id}/lists')
        lists = [TrelloList.from_json(trello_list) for trello_list in data]
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
                        card.members.append(member.username)
                        break
                else:
                    logger.error(f"Member username not found for {card}")
            cards.append(card)
        return cards

    def get_members(self):
        _, data = self._make_request(f'boards/{self.board_id}/members')
        members = [TrelloMember.from_json(member) for member in data]
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
        response = requests.get(f'{BASE_URL}{uri}', params=self.default_payload)
        return response.status_code, response.json()
