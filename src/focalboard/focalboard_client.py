import json
import logging
from typing import List
from urllib.parse import quote, urljoin

import requests

from ..strings import load
from ..utils.singleton import Singleton
from ..trello import trello_objects as objects

logger = logging.getLogger(__name__)


class FocalboardClient(Singleton):
    def __init__(self, focalboard_config=None):
        if self.was_initialized():
            return

        self._focalboard_config = focalboard_config
        self._update_from_config()
        logger.info("FocalboardClient successfully initialized")

    def get_boards_for_user(self, user_id=None):
        _, data = self._make_request("api/v2/teams/0/boards")
        boards = [objects.TrelloBoard.from_focalboard_dict(board) for board in data]
        logger.debug(f"get_boards_for_user: {boards}")
        return boards

    def get_lists(self, board_id):
        # if not board_id:
        #     board_id = self.board_id
        # TODO make it more efficient
        # essentially all list information is already passed via boards handler
        _, data = self._make_request(f"api/v2/teams/0/boards")
        list_data = [
            prop for prop in [board for board in data if board["id"] == board_id][0]["cardProperties"]
            if prop["name"] == "List"
        ][0]
        lists_data = list_data["options"]
        lists = [objects.TrelloList.from_focalboard_dict(trello_list, board_id) for trello_list in lists_data]
        logger.debug(f"get_lists: {lists}")
        return lists

    def get_list(self, board_id, list_id):
        _, data = self._make_request(f"api/v2/teams/0/boards")
        lists_data = [
            prop for prop in [board for board in data if board["id"] == board_id][0]["cardProperties"]
            if prop["name"] == "List"
        ][0]["options"]
        lst = [objects.TrelloList.from_focalboard_dict(trello_list, board_id) for trello_list in lists_data if trello_list["id"] == list_id][0]
        logger.debug(f"get_list: {lst}")
        return lst

    def _get_list_property(self, board_id):
        _, data = self._make_request(f"api/v2/teams/0/boards")
        return [
            prop for prop in [board for board in data if board["id"] == board_id][0]["cardProperties"]
            if prop["name"] == "List"
        ][0]["id"]

    def _get_member_property(self, board_id):
        _, data = self._make_request(f"api/v2/teams/0/boards")
        return [
            prop for prop in [board for board in data if board["id"] == board_id][0]["cardProperties"]
            if prop["name"] == "Assignee"
        ][0]["id"]

    def get_members(self, board_id) -> List[objects.TrelloMember]:
        _, data = self._make_request(f"api/v2/boards/{board_id}/members")
        members = []
        for member in data:
            _, data = self._make_request(f"api/v2/users/{member['userId']}")
            members.append(objects.TrelloMember.from_focalboard_dict(data))
        logger.debug(f"get_members: {members}")
        return members

    def get_cards(self, list_ids, board_id):
        _, data = self._make_request(f"api/v2/boards/{board_id}/blocks?all=true")
        cards = []
        # TODO: move this to app state
        members = self.get_members(board_id)
        lists = self.get_lists(board_id)
        list_prop = self._get_list_property(board_id)
        member_prop = self._get_member_property(board_id)
        view_id = [
            card_dict for card_dict in data 
            if card_dict["type"] == "view"
        ][0]["id"]
        data = [
            card_dict for card_dict in data 
            if card_dict["type"] == "card" and card_dict["fields"]["properties"].get(list_prop, '') in list_ids
        ]
        for card_dict in data:
            card = objects.TrelloCard.from_focalboard_dict(card_dict)
            card.url = urljoin(self.url, f"{board_id}/{view_id}/{card.id}")
            print(card.url)
            # TODO: move this to app state
            for trello_list in lists:
                if trello_list.id == card_dict["fields"]["properties"].get(list_prop, ''):
                    card.lst = trello_list
                    break
            else:
                logger.error(f"List name not found for {card}")
            # TODO: move this to app state
            if len(card_dict["fields"]["properties"].get(member_prop, [])) > 0:
                for member in members:
                    if member.id in card_dict["fields"]["properties"].get(member_prop, []):
                        card.members.append(member)
                if len(card.members) == 0:
                    logger.error(f"Member username not found for {card}")
            cards.append(card)
        logger.debug(f"get_cards: {cards}")
        return cards

    def update_config(self, new_focalboard_config):
        """To be called after config automatic update"""
        self._focalboard_config = new_focalboard_config
        self._update_from_config()

    def _update_from_config(self):
        """Update attributes according to current self._focalboard_config"""
        self.token = self._focalboard_config["token"]
        self.url = self._focalboard_config["url"]
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.token}',
            'X-Requested-With': 'XMLHttpRequest',
        }

    def _make_request(self, uri, payload={}):
        response = requests.get(
            urljoin(self.url, uri),
            params=payload,
            headers=self.headers
        )
        logger.debug(f"{response.url}")
        return response.status_code, response.json()
