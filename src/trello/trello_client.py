import json
import logging
import requests

from datetime import datetime


logger = logging.getLogger(__name__)


class TrelloBoard:
    def __init__(self):
        self.id = None
        self.name = None
        self.url = None

    def __str__(self):
        return f'Board<id={self.id}, name={self.name}, url={self.url}>'

    @classmethod
    def from_json(cls, data):
        board = cls()
        board.id = data['id']
        board.name = data['name']
        board.url = data['shortUrl']
        return board


class TrelloList:
    def __init__(self):
        self.id = None
        self.name = None

    def __str__(self):
        return f'List<id={self.id}, name={self.name}>'

    @classmethod
    def from_json(cls, data):
        trello_list = cls()
        trello_list.id = data['id']
        trello_list.name = data['name']
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

    def __str__(self):
        return f'Card<id={self.id}, name={self.name}, url={self.url}>'

    @classmethod
    def from_json(cls, data):
        card = cls()
        card.id = data['id']
        card.name = data['name']
        card.labels = [label['name'] for label in data['labels']]
        card.url = data['shortUrl']
        card.due = datetime.strptime(data['due'], '%Y-%m-%dT%H:%M:%S.%fZ') if data['due'] else None
        return card


class TrelloMember:
    def __init__(self):
        self.id = None
        self.username = None
        self.full_name = None

    def __str__(self):
        return f'Member<id={self.id}, name={self.username}, full name={self.full_name}>'

    @classmethod
    def from_json(cls, data):
        member = cls()
        member.id = data['id']
        member.username = data['username']
        member.full_name = data['fullName']
        return member


class TrelloClient:
    def __init__(self, config):
        self.api_key = config['api_key']
        self.token = config['token']
        self.board_id = config['board_id']
        self.default_payload = {
            'key': self.api_key,
            'token': self.token,
        }

    def get_board(self):
        req = requests.get(f'https://api.trello.com/1/boards/{self.board_id}', params=self.default_payload)
        return TrelloBoard.from_json(req.json())

    def get_lists(self):
        req = requests.get(f'https://api.trello.com/1/boards/{self.board_id}/lists', params=self.default_payload)
        lists = [TrelloList.from_json(l) for l in req.json()]
        return lists

    def get_cards(self, list_id=None):
        if list_id:
            req = requests.get(f'https://api.trello.com/1/lists/{list_id}/cards', params=self.default_payload)
        else:
            req = requests.get(f'https://api.trello.com/1/boards/{self.board_id}/cards', params=self.default_payload)
        cards = []
        # TODO move this to app state
        members = self.get_members()
        lists = self.get_lists()
        for c in req.json():
            card = TrelloCard.from_json(c)
            print(card)
            # TODO move this to app state
            for l in lists:
                if l.id == c['idList']:
                    card.list_name = l.name
                    break
            else:
                logger.error(f"List name not found for {card}")
            if len(c['idMembers']) > 0:
                print(c['idMembers'])
                for m in members:
                    if m.id in c['idMembers']:
                        card.members.append(m.username)
                        break
                else:
                    logger.error(f"Member username not found for {card}")
            cards.append(card)
        return cards

    def get_members(self):
        req = requests.get(f'https://api.trello.com/1/boards/{self.board_id}/members', params=self.default_payload)
        members = [TrelloMember.from_json(m) for m in req.json()]
        return members
