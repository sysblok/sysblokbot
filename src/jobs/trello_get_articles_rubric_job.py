from typing import Callable, List

from ..app_context import AppContext
from ..consts import BoardListAlias
from ..planka.planka_client import PlankaClient
from ..strings import load
from ..tg.sender import pretty_send
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
                    planka_client=app_context.planka_client,
                    rubric_title=load(alias.value),
                    rubric_alias=alias,
                    rubric_name=rubric_name,
                )

        pretty_send(paragraphs, send)

    @staticmethod
    def _format_card(card, planka_client: PlankaClient) -> str:
        card_fields = planka_client.get_custom_fields(card.id)
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
        planka_client: PlankaClient,
        rubric_title: str,
        rubric_alias: str,
        rubric_name: str,
    ) -> List[str]:
        list_ids = planka_client.get_list_id_from_aliases([rubric_alias])
        cards = planka_client.get_cards(list_ids)
        cards_filtered = [
            card
            for card in cards
            if rubric_name in [label.name for label in card.labels]
        ]

        paragraphs = [
            load(
                "common_report__list_title_and_size",
                title=rubric_title,
                length=len(cards_filtered),
            )
        ]
        for card in cards_filtered:
            paragraphs.append(
                TrelloGetArticlesRubricJob._format_card(card, planka_client)
            )
        return paragraphs
