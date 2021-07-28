import datetime
import logging
from typing import Callable, List

from ..app_context import AppContext
from ..consts import TrelloCardColor
from ..strings import load
from ..trello.trello_objects import TrelloCard
from ..consts import TrelloListAlias
from ..trello.trello_client import TrelloClient
from ..drive.drive_client import GoogleDriveClient
from ..utils import card_checks
from .base_job import BaseJob
from . import utils

logger = logging.getLogger(__name__)


class TrelloGetArticlesArts(BaseJob):
    @staticmethod
    def _execute(
        app_context: AppContext, send: Callable[[str], None], called_from_handler=False
    ):
        #cards = app_context.trello_client.get_cards()

        paragraphs = [] # тут собираем будущее сообщение
        errors = {}

        rubric_name = load ('rubric_names__arts')
        paragraphs.append(load ('rubric_report_job__intro', rubric=rubric_name))

        for alias in TrelloListAlias:
            paragraphs += TrelloGetArticlesArts._retrieve_cards_for_paragraph(
            app_context = app_context,
            trello_client=app_context.trello_client,
            drive_client=app_context.drive_client,
            title=load(alias.value),
            list_aliases=(alias,),
            rubric_name=rubric_name,
            errors = errors,
            strict_archive_rules=False,
        )

        utils.pretty_send(paragraphs, send)

    @staticmethod
    def _format_card(card: TrelloCard, app_context: AppContext) -> str:

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

        card_fields = app_context.trello_client.get_custom_fields(card.id)

        return load(
            'rubric_report_job__card',
            #"trello_board_state_job__card_2",
            date=card.due.strftime('%d.%m').lower() if card.due else '',
            url=card.url,
            name=card.name,
            # labels=labels,
            # list_name=card.lst,
            authors=utils.format_possibly_plural(
                load('common_role__author'), card_fields.authors
            ),
        )

    def _retrieve_cards_for_paragraph(
            app_context: AppContext,
            trello_client: TrelloClient,
            drive_client: GoogleDriveClient,
            title: str,
            list_aliases: List[TrelloListAlias],
            rubric_name: str,
            errors: dict,
            moved_from_exclusive: List[TrelloListAlias] = (),
            show_post_title=False,
            need_editor=True,
            need_title=False,
            strict_archive_rules=True,
    ) -> List[str]:
        list_ids = trello_client.get_list_id_from_aliases(list_aliases)
        cards = trello_client.get_cards(list_ids)
        #card_ids = []
        cards_filtered = []
        for card in cards:
            for label in card.labels:
                if rubric_name in label.name:
                    cards_filtered.append(card)
        if len (cards_filtered) == 0:
            return ''

        paragraphs = [
            load('common_report__list_title_and_size', title=title, length=len(cards_filtered))
        ]
        for card in cards_filtered:
            formatted_card = TrelloGetArticlesArts._format_card (card, app_context)
            paragraphs.append(formatted_card)
        return paragraphs