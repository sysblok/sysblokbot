import datetime
import logging
from typing import Callable, List

from ..app_context import AppContext
from ..consts import TrelloCardColor
from ..strings import load
from ..tg.sender import pretty_send
from ..trello.trello_objects import TrelloCard
from ..utils import card_checks
from .base_job import BaseJob
from .utils import get_cards_by_curator, retrieve_usernames

logger = logging.getLogger(__name__)


class TrelloBoardStateJob(BaseJob):
    @staticmethod
    def _execute(
        app_context: AppContext, send: Callable[[str], None], called_from_handler=False
    ):
        paragraphs = [
            load("trello_board_state_job__intro")
        ]  # list of paragraph strings
        curator_cards = get_cards_by_curator(app_context)
        for curator, curator_cards in curator_cards.items():
            curator_name, _ = curator
            card_paragraphs = []
            curator_cards.sort(key=lambda c: c.due if c.due else datetime.datetime.min)
            for card in curator_cards:
                card_paragraph = TrelloBoardStateJob._format_card(
                    card, card_checks.make_card_failure_reasons(card, app_context), app_context
                )
                if card_paragraph:
                    card_paragraphs.append(card_paragraph)
            if card_paragraphs:
                paragraphs.append(f"⭐️ <b>Куратор</b>: {curator_name}")
                paragraphs += card_paragraphs
        pretty_send(paragraphs, send)

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
                    retrieve_usernames(card.members, app_context.db_client)
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
