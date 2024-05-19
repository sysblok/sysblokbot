import ast
import json
import logging
from typing import List
from urllib.parse import quote, urljoin

import requests

from ..consts import TrelloCustomFieldTypeAlias, TrelloCustomFieldTypes, TrelloListAlias
from ..strings import load
from ..trello import trello_objects as objects
from ..utils.singleton import Singleton

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

    def get_lists(self, board_id=None, sorted=False):
        if board_id is None:
            # default board
            board_id = self.board_id
        # TODO make it more efficient
        # essentially all list information is already passed via boards handler
        _, data = self._make_request("api/v2/teams/0/boards")
        list_data = [
            prop
            for prop in [board for board in data if board["id"] == board_id][0][
                "cardProperties"
            ]
            if prop["name"] == "List"
        ][0]
        lists_data = list_data["options"]
        lists = [
            objects.TrelloList.from_focalboard_dict(trello_list, board_id)
            for trello_list in lists_data
        ]
        if sorted:
            # we need to get sorting order from the view, which is currently not efficient
            try:
                _, data = self._make_request(
                    f"api/v2/boards/{board_id}/blocks?all=true"
                )
                view = [card_dict for card_dict in data if card_dict["type"] == "view"][
                    0
                ]
                order = view["fields"]["visibleOptionIds"]
                sorted_lists = []
                for list_id in order:
                    this_list = [lst for lst in lists if lst.id == list_id][0]
                    sorted_lists.append(this_list)
                lists = sorted_lists
            except Exception as e:
                logger.error("can't sort focalboard lists", exc_info=e)
        logger.debug(f"get_lists: {lists}")
        return lists

    def get_list(self, board_id, list_id):
        _, data = self._make_request("api/v2/teams/0/boards")
        lists_data = [
            prop
            for prop in [board for board in data if board["id"] == board_id][0][
                "cardProperties"
            ]
            if prop["name"] == "List"
        ][0]["options"]
        lst = [
            objects.TrelloList.from_focalboard_dict(trello_list, board_id)
            for trello_list in lists_data
            if trello_list["id"] == list_id
        ][0]
        logger.debug(f"get_list: {lst}")
        return lst

    def get_labels(self, board_id=None):
        if board_id is None:
            # default board
            board_id = self.board_id
        _, data = self._make_request("api/v2/teams/0/boards")
        label_data = [
            prop
            for prop in [board for board in data if board["id"] == board_id][0][
                "cardProperties"
            ]
            if prop["name"] == "Label"
        ][0]
        labels_data = label_data["options"]
        labels = [
            objects.TrelloBoardLabel.from_focalboard_dict(label)
            for label in labels_data
        ]
        return labels

    def _get_list_property(self, board_id):
        _, data = self._make_request("api/v2/teams/0/boards")
        return [
            prop
            for prop in [board for board in data if board["id"] == board_id][0][
                "cardProperties"
            ]
            if prop["name"] == "List"
        ][0]["id"]

    def _get_label_property(self, board_id=None):
        if board_id is None:
            # default board
            board_id = self.board_id
        _, data = self._make_request("api/v2/teams/0/boards")
        return [
            prop
            for prop in [board for board in data if board["id"] == board_id][0][
                "cardProperties"
            ]
            if prop["name"] == "Label"
        ][0]["id"]

    def _get_due_property(self, board_id=None):
        if board_id is None:
            # default board
            board_id = self.board_id
        _, data = self._make_request("api/v2/teams/0/boards")
        return [
            prop
            for prop in [board for board in data if board["id"] == board_id][0][
                "cardProperties"
            ]
            if prop["name"] == "Due"
        ][0]["id"]

    def get_card_due(self, card_id: str):
        _, data = self._make_request(f"api/v2/cards/{card_id}")
        due_id = self._get_due_property()
        due_value = None

        fields = data["properties"]
        for type_id, value in fields.items():
            if type_id == due_id:
                due_value = value
        due_value_dict = ast.literal_eval(due_value)
        return due_value_dict.get("from", [])

    def _get_member_property(self, board_id):
        _, data = self._make_request("api/v2/teams/0/boards")
        return [
            prop
            for prop in [board for board in data if board["id"] == board_id][0][
                "cardProperties"
            ]
            if prop["name"] == "Assignee"
        ][0]["id"]

    def get_list_id_from_aliases(self, list_aliases):
        list_ids = [
            self.lists_config[alias]
            for alias in list_aliases
            if alias in self.lists_config
        ]
        if len(list_ids) != len(list_aliases):
            logger.error(
                f"list_ids not found for aliases: "
                f"{[alias for alias in list_aliases if alias not in self.lists_config]}"
            )
        return list_ids

    def _fill_alias_id_map(self, items, item_enum):
        result = {}
        for alias in item_enum:
            suitable_items = [
                item for item in items if item.name.startswith(load(alias.value))
            ]
            if len(suitable_items) > 1:
                raise ValueError(
                    f"Enum {item_enum.__name__} name {alias.value} is ambiguous!"
                )
            if len(suitable_items) > 0:
                result[alias] = suitable_items[0].id
        return result

    def _fill_id_type_map(self, items, item_enum):
        result = {}
        for item in items:
            result[item.id] = TrelloCustomFieldTypes(item.type)
        return result

    def get_board_custom_field_types(self):
        board_id = self.board_id
        _, data = self._make_request(f"api/v2/boards/{board_id}")
        custom_field_types = [
            objects.TrelloCustomFieldType.from_focalboard_dict(custom_field_type)
            for custom_field_type in data["cardProperties"]
        ]
        logger.debug(f"get_board_custom_field_types: {custom_field_types}")
        return custom_field_types

    def get_username(self, user_id: str):
        _, data = self._make_request(f"api/v2/users/{user_id}")
        username = data["username"]
        return username

    def get_custom_fields(self, card_id: str) -> objects.CardCustomFields:
        card_fields = objects.CardCustomFields(card_id)
        board_labels = self.get_labels()
        card_fields_dict = {}
        card_labels_ids = []
        card_labels = []
        _, data = self._make_request(f"api/v2/cards/{card_id}")
        fields = data["properties"]
        for alias, type_id in self.custom_fields_config.items():
            if type_id in fields:
                changed_alias = alias.name.split(".")[-1].lower()
                card_fields_dict[changed_alias] = fields[type_id]

        board_label_id = self._get_label_property()

        for type_id, value in fields.items():
            if type_id == board_label_id:
                card_labels_ids = value

        for card_label_id in card_labels_ids:
            for board_label in board_labels:
                if card_label_id == board_label.id:
                    card_labels.append(board_label)

        card_fields.authors = [
            self.get_username(author.strip())
            for author in card_fields_dict.get("author", [])
        ]
        card_fields.editors = [
            self.get_username(editor.strip())
            for editor in card_fields_dict.get("editor", [])
        ]
        card_fields.illustrators = [
            self.get_username(illustrator.strip())
            for illustrator in card_fields_dict.get("illustrator", [])
        ]
        card_fields.cover = (
            card_fields_dict["cover"] if "cover" in card_fields_dict else None
        )
        card_fields.google_doc = (
            card_fields_dict["google_doc"] if "google_doc" in card_fields_dict else None
        )
        card_fields.title = (
            card_fields_dict["title"] if "title" in card_fields_dict else None
        )

        card_fields._data = card_labels
        return card_fields

    def get_members(self, board_id) -> List[objects.TrelloMember]:
        _, data = self._make_request(f"api/v2/boards/{board_id}/members")
        members = []
        for member in data:
            _, data = self._make_request(f"api/v2/users/{member['userId']}")
            members.append(objects.TrelloMember.from_focalboard_dict(data))
        logger.debug(f"get_members: {members}")
        return members

    def get_cards(self, list_ids, board_id=None):
        if board_id is None:
            board_id = self.board_id
        _, data = self._make_request(f"api/v2/boards/{board_id}/blocks?all=true")
        cards = []
        # TODO: move this to app state
        members = self.get_members(board_id)
        lists = self.get_lists(board_id=board_id)
        list_prop = self._get_list_property(board_id)
        member_prop = self._get_member_property(board_id)
        view_id = [card_dict for card_dict in data if card_dict["type"] == "view"][0][
            "id"
        ]
        data = [
            card_dict
            for card_dict in data
            if card_dict["type"] == "card"
            and card_dict["fields"]["properties"].get(list_prop, "") in list_ids
        ]
        for card_dict in data:
            card = objects.TrelloCard.from_focalboard_dict(card_dict)
            card.url = urljoin(self.url, f"{board_id}/{view_id}/{card.id}")
            # TODO: move this to app state
            for trello_list in lists:
                if trello_list.id == card_dict["fields"]["properties"].get(
                    list_prop, ""
                ):
                    card.lst = trello_list
                    break
            else:
                logger.error(f"List name not found for {card}")
            # TODO: move this to app state
            if len(card_dict["fields"]["properties"].get(member_prop, [])) > 0:
                for member in members:
                    if member.id in card_dict["fields"]["properties"].get(
                        member_prop, []
                    ):
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
        self.board_id = self._focalboard_config["board_id"]
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
            "X-Requested-With": "XMLHttpRequest",
        }
        try:
            lists = self.get_lists()
            self.lists_config = self._fill_alias_id_map(lists, TrelloListAlias)
            custom_field_types = self.get_board_custom_field_types()
            self.custom_fields_type_config = self._fill_id_type_map(
                custom_field_types, TrelloCustomFieldTypes
            )
            self.custom_fields_config = self._fill_alias_id_map(
                custom_field_types, TrelloCustomFieldTypeAlias
            )
        except Exception as e:
            # TODO remove this when main board is migrated
            logger.error(
                "something went wrong when setting up focalboard client", exc_info=e
            )
            pass

    def _make_request(self, uri, payload={}):
        response = requests.get(
            urljoin(self.url, uri), params=payload, headers=self.headers
        )
        logger.debug(f"{response.url}")
        return response.status_code, response.json()
