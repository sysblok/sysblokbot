import html
import json
import logging
from typing import Callable, Iterable

from deepdiff import DeepDiff

from ..app_context import AppContext
from ..scheduler import JobScheduler
from ..strings import load
from ..tg.sender import TelegramSender
from .base_job import BaseJob
from ..trello.trello_objects import TrelloCard
from ..tg.handlers.get_tasks_report_handler import _get_members, _make_member_text, _make_cards_text

logger = logging.getLogger(__name__)

class BoardMyCardsRazvitieJob(BaseJob):
    @staticmethod
    def _execute(
        app_context: AppContext, send: Callable[[str], None], called_from_handler=False, *args, **kwargs,
    ):
        """Job returning my card on Razvitie board"""
        # TODO sort out @ in the beginning of the username
        focalboard_username = app_context.db_client.find_focalboard_username_by_telegram_username(
            f"@{kwargs.get('called_from_chat_username')}"
        )
        # curren
        focalboard_username = focalboard_username[1:]
        board_id = [
            board.id for board in app_context.focalboard_client.get_boards_for_user()
            if "Развитие" in board.name
        ][0]
        board_all_lists = app_context.focalboard_client.get_lists(board_id, sorted=True)
        # filter board lists between 'Список задач' and 'Разделитель'
        board_list_names = list(map(lambda l: l.name, board_all_lists))
        index_of_first_list = board_list_names.index('Список задач')
        index_of_last_list = board_list_names.index('Разделитель')
        board_lists = board_all_lists[index_of_first_list + 1: index_of_last_list]
        paragraphs = []
        for board_list in board_lists:
            cards: list[TrelloCard] = app_context.focalboard_client.get_cards(
                board_list.id, board_id
            )
            my_cards = [
                card for card in cards if focalboard_username in [
                    member.username for member in card.members
                ]
            ]
            if my_cards:
                list_report = BoardMyCardsRazvitieJob._create_paragraphs_from_cards(
                    my_cards, f'📜 <b>{board_list.name}</b>', True, app_context
                )
                paragraphs += list_report
                paragraphs.append('')  # hotfix for separating lists

        send(load('focalboard__my_cards_razvitie_job__text', data='\n'.join(paragraphs)))

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
