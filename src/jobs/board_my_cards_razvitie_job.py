import logging
from typing import Callable, Iterable, List

from ..app_context import AppContext
from ..strings import load
from ..tg.handlers.get_tasks_report_handler import _make_cards_text
from ..trello.trello_objects import TrelloCard
from .base_job import BaseJob

logger = logging.getLogger(__name__)

RAZVITIE_BOARD_NAME = "СБъ. Развитие"
TASKS_START_LIST_NAME = "Список задач"
TASKS_END_LIST_NAME = "Разделитель"


class BoardMyCardsRazvitieJob(BaseJob):
    @staticmethod
    def _execute(
        app_context: AppContext,
        send: Callable[[str], None],
        called_from_handler=False,
        *args,
        **kwargs,
    ):
        """Job returning my cards on Razvitie board."""
        assert called_from_handler, "This job should be called from handler"
        tg_username = send.update.message.chat.username

        planka_username = (
            app_context.db_client.find_focalboard_username_by_telegram_username(
                f"@{tg_username}"
            )
        )

        if not planka_username:
            raise ValueError(
                f"Planka username not found for Telegram user @{tg_username}"
            )

        planka_username = BoardMyCardsRazvitieJob._normalize_username(planka_username)

        boards = app_context.planka_client.get_boards_for_telegram_user(
            tg_username,
            app_context.db_client,
        )
        board_id = next(
            (board.id for board in boards if RAZVITIE_BOARD_NAME == board.name), None
        )

        if not board_id:
            raise ValueError(
                f"Не удалось найти доску 'Развитие' для пользователя @{tg_username}"
            )

        board_all_lists = app_context.planka_client.get_lists(board_id, sorted=True)
        board_lists = BoardMyCardsRazvitieJob._get_status_lists(board_all_lists)
        paragraphs = []
        for board_list in board_lists:
            cards: List[TrelloCard] = app_context.planka_client.get_cards(
                board_list.id, board_id
            )
            my_cards = [
                card
                for card in cards
                if planka_username
                in [
                    BoardMyCardsRazvitieJob._normalize_username(member.username)
                    for member in card.members
                    if member.username
                ]
            ]
            if my_cards:
                list_report = BoardMyCardsRazvitieJob._create_paragraphs_from_cards(
                    my_cards, f"📜 <b>{board_list.name}</b>", True, app_context
                )
                paragraphs += list_report
                paragraphs.append("")  # hotfix for separating lists

        send(
            load("focalboard__my_cards_razvitie_job__text", data="\n".join(paragraphs))
        )

    @staticmethod
    def _create_paragraphs_from_cards(
        cards: Iterable[TrelloCard],
        introduction: str,
        need_label: bool,
        app_context: AppContext,
    ):
        paragraphs = []
        if introduction:
            paragraphs.append(introduction)

        paragraphs += _make_cards_text(cards, need_label, app_context)
        return paragraphs

    @staticmethod
    def _normalize_username(username: str) -> str:
        return username.strip().lstrip("@").lower()

    @staticmethod
    def _get_status_lists(board_all_lists):
        board_list_names = [lst.name for lst in board_all_lists]
        index_of_first_list = BoardMyCardsRazvitieJob._find_list_index(
            board_list_names, TASKS_START_LIST_NAME
        )
        index_of_last_list = BoardMyCardsRazvitieJob._find_list_index(
            board_list_names, TASKS_END_LIST_NAME
        )
        if index_of_last_list <= index_of_first_list:
            raise ValueError(
                f"Список '{TASKS_END_LIST_NAME}' должен быть после списка "
                f"'{TASKS_START_LIST_NAME}' на доске '{RAZVITIE_BOARD_NAME}'"
            )
        return board_all_lists[index_of_first_list + 1 : index_of_last_list]

    @staticmethod
    def _find_list_index(board_list_names, list_name):
        try:
            return board_list_names.index(list_name)
        except ValueError as e:
            raise ValueError(
                f"Не удалось найти список '{list_name}' на доске '{RAZVITIE_BOARD_NAME}'"
            ) from e
