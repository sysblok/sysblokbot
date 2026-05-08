import builtins
import html
import logging
from datetime import datetime
from typing import Iterable, List, Optional, Set
from urllib.parse import urljoin

import requests
from cachetools import TTLCache

from ..consts import TrelloCardColor
from ..db import db_client
from ..trello import trello_objects as objects
from ..trello.trello_objects import TIME_FORMAT
from ..utils.singleton import Singleton

logger = logging.getLogger(__name__)


class PlankaClient(Singleton):
    def __init__(self, planka_config=None):
        if self.was_initialized():
            return

        self._planka_config = planka_config or {}
        self._update_from_config()
        logger.info("PlankaClient successfully initialized")

    def get_boards_for_user(self) -> List[objects.TrelloBoard]:
        _, data = self._make_request("projects")
        boards_data = data.get("included", {}).get("boards", [])
        boards = [self._board_from_planka_dict(board) for board in boards_data]
        logger.debug(f"get_boards_for_user: {boards}")
        return boards

    def get_boards_for_telegram_user(
        self,
        telegram_username: str,
        db_client: db_client.DBClient,
    ) -> List[objects.TrelloBoard]:
        raw_planka = db_client.find_focalboard_username_by_telegram_username(
            f"@{telegram_username}"
        )
        if not raw_planka:
            logger.warning(
                f"No Planka username found for telegram={telegram_username!r}. "
                "Accessible boards can't be determined. Managers should check and fill the table."
            )
            return []

        planka_username = raw_planka.strip().lstrip("@").lower()
        logger.debug(f"Normalized Planka username from DB = {planka_username!r}")

        accessible = []
        for board in self.get_boards_for_user():
            try:
                member_usernames = [
                    member.username.strip().lstrip("@").lower()
                    for member in self.get_members(board.id)
                    if member.username
                ]
                if planka_username in member_usernames:
                    accessible.append(board)
            except Exception as e:
                logger.error(f"Error fetching members for board {board.id}", exc_info=e)

        logger.info(
            f"Telegram user @{telegram_username} has access to {len(accessible)} boards: "
            f"{[board.name for board in accessible]}"
        )
        return accessible

    def get_lists(self, board_id=None, sorted=False):
        board_id = board_id or self.board_id
        data = self._get_board_data(board_id)
        lists_data = data.get("included", {}).get("lists", [])
        lists = [
            self._list_from_planka_dict(item)
            for item in lists_data
            if item.get("type") == "active"
        ]
        if sorted:
            lists = builtins.sorted(
                lists,
                key=lambda item: self._list_position(lists_data, item.id),
            )
        logger.debug(f"get_lists: {lists}")
        return lists

    def get_members(self, board_id) -> List[objects.TrelloMember]:
        data = self._get_board_data(board_id)
        included = data.get("included", {})
        users_by_id = {
            user["id"]: user for user in included.get("users", []) if "id" in user
        }
        members = []
        for membership in included.get("boardMemberships", []):
            if membership.get("boardId") != board_id:
                continue

            user = users_by_id.get(membership.get("userId"))
            if user:
                members.append(self._member_from_planka_dict(user))
        logger.debug(f"get_members: {members}")
        return members

    def get_cards(self, list_ids=None, board_id=None):
        board_id = board_id or self.board_id
        list_id_filter = self._normalize_list_ids(list_ids)
        data = self._get_board_data(board_id)
        included = data.get("included", {})

        lists_by_id = {lst.id: lst for lst in self.get_lists(board_id)}
        labels_by_id = {
            label["id"]: self._label_from_planka_dict(label)
            for label in included.get("labels", [])
            if "id" in label
        }
        users_by_id = {
            user["id"]: self._member_from_planka_dict(user)
            for user in included.get("users", [])
            if "id" in user
        }
        card_memberships = self._group_by_card_id(
            included.get("cardMemberships", []), "userId"
        )
        card_labels = self._group_by_card_id(included.get("cardLabels", []), "labelId")

        cards = []
        for card_data in included.get("cards", []):
            list_id = card_data.get("listId")
            if list_id_filter is not None and list_id not in list_id_filter:
                continue
            if list_id not in lists_by_id or card_data.get("isClosed"):
                continue

            card = self._card_from_planka_dict(card_data)
            card.lst = lists_by_id[list_id]
            card.labels = [
                labels_by_id[label_id]
                for label_id in card_labels.get(card.id, [])
                if label_id in labels_by_id
            ]
            card.members = [
                users_by_id[user_id]
                for user_id in card_memberships.get(card.id, [])
                if user_id in users_by_id
            ]
            cards.append(card)

        logger.debug(f"get_cards: {cards}")
        return cards

    def update_config(self, new_planka_config):
        """To be called after config automatic update."""
        self._planka_config = new_planka_config or {}
        self._update_from_config()

    def _update_from_config(self):
        """Update attributes according to current self._planka_config."""
        self.url = self._with_trailing_slash(self._planka_config.get("url", ""))
        self.api_url = urljoin(self.url, "api/")
        self.api_key = self._planka_config.get("api_key", "")
        self.board_id = self._planka_config.get("board_id")
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Api-Key": self.api_key,
        }
        self._board_cache = TTLCache(maxsize=1000, ttl=30)

    def _make_request(self, uri, payload=None):
        response = requests.get(
            urljoin(self.api_url, uri.lstrip("/")),
            params=payload or {},
            headers=self.headers,
        )
        logger.debug(f"{response.url}")
        return response.status_code, response.json()

    def _get_board_data(self, board_id):
        if board_id not in self._board_cache:
            _, data = self._make_request(f"boards/{board_id}")
            self._board_cache[board_id] = data
        return self._board_cache[board_id]

    def _board_from_planka_dict(self, data):
        board = objects.TrelloBoard()
        try:
            board.id = data["id"]
            board.name = html.escape(data["name"])
            board.url = urljoin(self.url, f"boards/{board.id}")
        except Exception as e:
            board._ok = False
            logger.error(f"Bad Planka board json {data}", exc_info=e)
        return board

    @staticmethod
    def _list_from_planka_dict(data):
        trello_list = objects.TrelloList()
        try:
            trello_list.id = data["id"]
            trello_list.name = html.escape(data.get("name") or "")
            trello_list.board_id = data["boardId"]
        except Exception as e:
            trello_list._ok = False
            logger.error(f"Bad Planka list json {data}", exc_info=e)
        return trello_list

    def _card_from_planka_dict(self, data):
        card = objects.TrelloCard()
        try:
            card.id = data["id"]
            card.name = html.escape(data["name"])
            card.url = urljoin(self.url, f"cards/{card.id}")
            card.due = self._parse_due_date(data.get("dueDate"))
        except Exception as e:
            card._ok = False
            logger.error(f"Bad Planka card json {data}", exc_info=e)
        return card

    @staticmethod
    def _label_from_planka_dict(data):
        label = objects.TrelloCardLabel()
        try:
            label.id = data["id"]
            label.name = html.escape(data.get("name") or "")
            label.color = TrelloCardColor.UNKNOWN
        except Exception as e:
            label._ok = False
            logger.error(f"Bad Planka label json {data}", exc_info=e)
        return label

    @staticmethod
    def _member_from_planka_dict(data):
        member = objects.TrelloMember()
        member.id = data["id"]
        member.username = data.get("username")
        member.full_name = data.get("name") or data.get("username")
        return member

    @staticmethod
    def _group_by_card_id(items, value_key):
        grouped = {}
        for item in items:
            card_id = item.get("cardId")
            value = item.get(value_key)
            if card_id and value:
                grouped.setdefault(card_id, []).append(value)
        return grouped

    @staticmethod
    def _normalize_list_ids(list_ids) -> Optional[Set[str]]:
        if list_ids is None:
            return None
        if isinstance(list_ids, str):
            return {list_ids}
        if isinstance(list_ids, Iterable):
            return set(list_ids)
        return {list_ids}

    @staticmethod
    def _parse_due_date(raw_due):
        if not raw_due:
            return None
        try:
            return datetime.strptime(raw_due, TIME_FORMAT)
        except ValueError:
            return datetime.fromisoformat(raw_due.replace("Z", "+00:00")).replace(
                tzinfo=None
            )

    @staticmethod
    def _with_trailing_slash(raw_url):
        if not raw_url or raw_url.endswith("/"):
            return raw_url
        return f"{raw_url}/"

    @staticmethod
    def _list_position(lists_data, list_id):
        for item in lists_data:
            if item.get("id") == list_id:
                return item.get("position") or 0
        return 0
