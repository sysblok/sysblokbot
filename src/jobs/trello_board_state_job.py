from collections import defaultdict
import datetime
import logging
from typing import Callable, List

from ..app_context import AppContext
from ..consts import TrelloCardColor
from ..strings import load
from ..trello.trello_client import TrelloClient
from ..trello.trello_objects import TrelloCard
from ..utils import card_checks
from .base_job import BaseJob
from . import utils

logger = logging.getLogger(__name__)


class TrelloBoardStateJob(BaseJob):
    @staticmethod
    def _execute(
        app_context: AppContext, send: Callable[[str], None], called_from_handler=False
    ):
        paragraphs = [
            load("trello_board_state_job__intro")
        ]  # list of paragraph strings
        curator_cards = TrelloBoardStateJob.get_cards_by_curator(app_context)
        for curator, curator_cards in curator_cards.items():
            card_paragraphs = []
            curator_cards.sort(key=lambda c: c.due if c.due else datetime.datetime.min)
            for card in curator_cards:
                card_paragraph = TrelloBoardStateJob._format_card(
                    card, card_checks.make_card_failure_reasons(card, app_context), app_context
                )
                if card_paragraph:
                    card_paragraphs.append(card_paragraph)
            if card_paragraphs:
                paragraphs.append(f"⭐️ <b>Куратор</b>: {curator}")
                paragraphs += card_paragraphs
        utils.pretty_send(paragraphs, send)

    @staticmethod
    def get_cards_by_curator(app_context: AppContext):
        cards = app_context.trello_client.get_cards()
        curator_cards = defaultdict(list)
        for card in cards:
            curators = TrelloBoardStateJob._get_curators(card, app_context.db_client)
            if not curators:
                # TODO: get main curator from spreadsheet
                curators = [('Илья Булгаков (@bulgak0v)', None)]
            for curator_name, _ in curators:
                curator_cards[curator_name].append(card)

        return curator_cards

    @staticmethod
    def _format_card(card: TrelloCard, failure_reasons: List[str], app_context: AppContext) -> str:
        if not failure_reasons:
            return None

        failure_reasons_formatted = ', '.join(failure_reasons)
        labels = (
            load(
                "trello_board_state_job__card_labels",
                names=", ".join(
                    # We filter BLACK cards as this is an auxiliary label
                    label.name
                    for label in card.labels
                    if label.color != TrelloCardColor.BLACK
                ),
            )
            if card.labels
            else ""
        )

        # Avoiding message overflow, strip explanations in ()
        list_name = card.lst.name + "("
        list_name = list_name[: list_name.find("(")].strip()

        members = (
            load(
                "trello_board_state_job__card_members",
                members=", ".join(
                    utils.retrieve_usernames(card.members, app_context.db_client)
                ),
                curators="",
            )
            if card.members
            else ""
        )

        return load(
            "trello_board_state_job__card_2",
            failure_reasons=failure_reasons_formatted,
            url=card.url,
            name=card.name,
            labels=labels,
            list_name=list_name,
            members=members,
        )

    @staticmethod
    def _get_curators(card, db_client):
        curators = set()
        for member in card.members:
            curator_names = utils.retrieve_curator_names_by_author(member, db_client)
            curators.update(curator_names)
        if curators:
            return curators

        # e.g. if no members in a card, should tag curators based on label
        curators_by_label = utils.retrieve_curator_names_by_categories(
            card.labels, db_client
        )
        return curators_by_label
