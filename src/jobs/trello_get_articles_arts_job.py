from typing import Callable, List

from ..app_context import AppContext
from ..strings import load
from ..trello.trello_objects import TrelloCard
from ..consts import TrelloListAlias
from ..trello.trello_client import TrelloClient
from .base_job import BaseJob
from . import utils


class TrelloGetArticlesArtsJob(BaseJob):
    @staticmethod
    def _execute(
        app_context: AppContext, send: Callable[[str], None],
            called_from_handler=False
    ):
        paragraphs = []
        rubric_name = load('rubric_names__arts')
        paragraphs.append(load('rubric_report_job__intro', rubric=rubric_name))

        for alias in TrelloListAlias:
            paragraphs += TrelloGetArticlesArtsJob._get_rubric_paragraphs(
                app_context=app_context,
                trello_client=app_context.trello_client,
                rubric_title=load(alias.value),
                rubric_alias=alias,
                rubric_name=rubric_name,
            )

        utils.pretty_send(paragraphs, send)

    @staticmethod
    def _format_card(card: TrelloCard, app_context: AppContext) -> str:
        card_fields = app_context.trello_client.get_custom_fields(card.id)
        return load(
            'rubric_report_job__card',
            date=card.due.strftime('%d.%m').lower() if card.due else '',
            url=card.url,
            name=card.name,
            authors=utils.format_possibly_plural(
                load('common_role__author'), card_fields.authors
            ),
        )

    def _get_rubric_paragraphs(
            app_context: AppContext,
            trello_client: TrelloClient,
            rubric_title: str,
            rubric_alias: TrelloListAlias,
            rubric_name: str,
    ) -> List[str]:
        list_ids = trello_client.get_list_id_from_aliases([rubric_alias])
        cards = trello_client.get_cards(list_ids)
        cards_filtered = []
        for card in cards:
            if rubric_name in [label.name for label in card.labels]:
                cards_filtered.append(card)

        paragraphs = [
            load('common_report__list_title_and_size',
                 title=rubric_title, length=len(cards_filtered))
        ]
        for card in cards_filtered:
            formatted_card = TrelloGetArticlesArtsJob._format_card(card,
                                                                   app_context)
            paragraphs.append(formatted_card)
        return paragraphs
