import logging
from typing import Callable, Iterable

from ..app_context import AppContext
from ..strings import load
from ..tg.handlers.get_tasks_report_handler import _make_cards_text
from ..trello.trello_objects import TrelloCard
from .base_job import BaseJob

logger = logging.getLogger(__name__)


class BoardMyCardsRazvitieJob(BaseJob):
    @staticmethod
    def _execute(
        app_context: AppContext,
        send: Callable[[str], None],
        called_from_handler=False,
        *args,
        **kwargs,
    ):
        """Job returning my card on Razvitie board"""
        assert called_from_handler, "This job should be called from handler"
        # TODO sort out @ in the beginning of the username
        # focalboard_username = (
        #     app_context.db_client.find_focalboard_username_by_telegram_username(
        #         f"@{send.update.message.chat.username}"
        #     )
        # )
        # # curren
        # telegram_username = send.update.message.chat.username
        tg_username = send.update.message.chat.username

        # look for @
        focalboard_username = (
            app_context.db_client.find_focalboard_username_by_telegram_username(
                f"@{tg_username}"
            )
        )

        if not focalboard_username:
            raise ValueError(
                f"Focalboard username not found for Telegram user @{tg_username}"
            )

        focalboard_username = focalboard_username.lstrip("@")

        boards = app_context.focalboard_client.get_boards_for_telegram_user(
            tg_username,
            app_context.db_client,
        )
        board_id = next(
            (board.id for board in boards if "Развитие" in board.name), None
        )

        print(f"Доски для пользователя @{tg_username}: {[b.name for b in boards]}")
        board_id = next(
            (board.id for board in boards if "Развитие" in board.name), None
        )

        if not board_id:
            raise ValueError(
                f"Не удалось найти доску 'Развитие' для пользователя @{tg_username}"
            )

        board_all_lists = app_context.focalboard_client.get_lists(board_id, sorted=True)
        # filter board lists between 'Список задач' and 'Разделитель'
        board_list_names = list(map(lambda lst: lst.name, board_all_lists))
        index_of_first_list = board_list_names.index("Список задач")
        index_of_last_list = board_list_names.index("Разделитель")
        board_lists = board_all_lists[index_of_first_list + 1 : index_of_last_list]
        paragraphs = []
        for board_list in board_lists:
            cards: list[TrelloCard] = app_context.focalboard_client.get_cards(
                board_list.id, board_id
            )
            my_cards = [
                card
                for card in cards
                if focalboard_username in [member.username for member in card.members]
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
