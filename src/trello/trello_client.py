import json
import requests


# class TrelloCard:
#     def __init__(self, json):



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
        return requests.get(f'https://api.trello.com/1/boards/{self.board_id}', params=self.default_payload)

    def get_lists(self):
        return requests.get(f'https://api.trello.com/1/boards/{self.board_id}/lists', params=self.default_payload)

    def get_cards(self, list_id):
        return requests.get(f'https://api.trello.com/1/lists/{list_id}/cards', params=self.default_payload)
