from typing import Callable, List

from ..app_context import AppContext
from ..consts import BoardListAlias
from ..strings import load
from ..tg.sender import pretty_send
from ..trello.trello_client import TrelloClient
from ..trello.trello_objects import TrelloCard
from . import utils
from .base_job import BaseJob


class TrelloGetArticlesRubricJob(BaseJob):
    """
    kwargs has to be set in job config.
    kwargs required: spreadsheet_key, template_string
    kwargs optional:
      - sheet_name (required if it's not the first tab)
      - name (for readability and logs)
    """

    @staticmethod
    def _execute(
        app_context: AppContext,
        send: Callable[[str], None],
        called_from_handler=False,
        *args,
        **kwargs,
    ):
        paragraphs = []
        if called_from_handler:
            if len(args) == 0:
                send("Please type in rubric name after get_articles_rubric")
                return
            else:
                rubric_name = args[0]
        else:
            rubric_name = kwargs["rubric_name"]
        paragraphs.append(load("rubric_report_job__intro", rubric=rubric_name))

        for alias in BoardListAlias:
            if alias not in [
                BoardListAlias.BACK_BURNER,
                BoardListAlias.PUBLISH_DONE_11,
            ]:
                paragraphs += TrelloGetArticlesRubricJob._get_rubric_paragraphs(
                    app_context=app_context,
                    trello_client=app_context.trello_client,
                    rubric_title=load(alias.value),
                    rubric_alias=alias,
                    rubric_name=rubric_name,
                )

        pretty_send(paragraphs, send)

    @staticmethod
    def _format_card(card: TrelloCard, app_context: AppContext) -> str:
        if not app_context.trello_client.deprecated:
            card_fields = app_context.trello_client.get_custom_fields(card.id)
        else:
            card_fields = app_context.focalboard_client.get_custom_fields(card.id)
        return load(
            "rubric_report_job__card",
            date=card.due.strftime("%d.%m").lower() if card.due else "",
            url=card.url,
            name=card.name,
            authors=utils.format_possibly_plural(
                load("common_role__author"), card_fields.authors
            ),
        )

    def _get_rubric_paragraphs(
        app_context: AppContext,
        trello_client: TrelloClient,
        rubric_title: str,
        rubric_alias: str,
        rubric_name: str,
    ) -> List[str]:
        if not trello_client.deprecated:
            list_ids = trello_client.get_list_id_from_aliases([rubric_alias])
            cards = trello_client.get_cards(list_ids)
        else:
            list_ids = app_context.focalboard_client.get_list_id_from_aliases(
                [rubric_alias]
            )
            cards = app_context.focalboard_client.get_cards(list_ids)
        cards_filtered = []
        for card in cards:
            if rubric_name in [label.name for label in card.labels]:
                cards_filtered.append(card)

        paragraphs = [
            load(
                "common_report__list_title_and_size",
                title=rubric_title,
                length=len(cards_filtered),
            )
        ]
        for card in cards_filtered:
            formatted_card = TrelloGetArticlesRubricJob._format_card(card, app_context)
            paragraphs.append(formatted_card)
        return paragraphs
