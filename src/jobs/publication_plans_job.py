import datetime
import logging
from typing import Callable, List

from ..app_context import AppContext
from ..consts import BoardCardColor, BoardListAlias, TrelloCardColor
from ..strings import load
from ..tg.sender import pretty_send
from ..trello.trello_client import TrelloClient
from .base_job import BaseJob
from .utils import check_trello_card, format_errors, format_possibly_plural

logger = logging.getLogger(__name__)


class PublicationPlansJob(BaseJob):
    @staticmethod
    def _execute(
        app_context: AppContext, send: Callable[[str], None], called_from_handler=False
    ):
        paragraphs = [load("publication_plans_job__intro")]  # list of paragraph strings
        errors = {}

        paragraphs += PublicationPlansJob._retrieve_cards_for_paragraph(
            trello_client=app_context.trello_client,
            title=load("publication_plans_job__title_publish_this_week"),
            list_aliases=(
                BoardListAlias.PUBLISH_BACKLOG_9,
                BoardListAlias.PUBLISH_IN_PROGRESS_10,
            ),
            errors=errors,
            show_due=True,
            strict_archive_rules=True,
        )

        paragraphs += PublicationPlansJob._retrieve_cards_for_paragraph(
            trello_client=app_context.trello_client,
            title=load("common_report__section_title_editorial_board"),
            list_aliases=(
                BoardListAlias.PENDING_EDITOR_5,
                BoardListAlias.PENDING_SEO_EDITOR_6,
            ),
            errors=errors,
            show_due=False,
            need_illustrators=False,
            strict_archive_rules=False,
        )

        paragraphs.append(load("publication_plans_job__outro"))

        if len(errors) > 0:
            paragraphs = format_errors(errors)

        pretty_send(paragraphs, send)

    @staticmethod
    def _retrieve_cards_for_paragraph(
        trello_client: TrelloClient,
        title: str,
        list_aliases: List[BoardListAlias],
        errors: dict,
        show_due=True,
        need_illustrators=True,
        strict_archive_rules=False,
    ) -> List[str]:
        """
        Returns a list of paragraphs that should always go in a single message.
        """
        logger.info(f'Started counting: "{title}"')
        list_ids = trello_client.get_list_id_from_aliases(list_aliases)
        cards = trello_client.get_cards(list_ids)
        if show_due:
            cards.sort(key=lambda card: card.due or datetime.datetime.min)
        parse_failure_counter = 0

        paragraphs = [
            load("common_report__list_title_and_size", title=title, length=len(cards))
        ]

        for card in cards:
            if not card:
                parse_failure_counter += 1
                continue

            card_fields = trello_client.get_custom_fields(card.id)

            label_names = [
                label.name
                for label in card.labels
                if label.color not in [TrelloCardColor.BLACK, BoardCardColor.BLACK]
            ]

            is_archive_card = load("common_trello_label__archive") in label_names

            card_is_ok = check_trello_card(
                card,
                errors,
                is_bad_title=(
                    card_fields.title is None
                    and card.lst.id
                    not in (
                        trello_client.lists_config[BoardListAlias.PENDING_EDITOR_5],
                        trello_client.lists_config[BoardListAlias.PENDING_SEO_EDITOR_6],
                    )
                ),
                is_bad_illustrators=(
                    len(card_fields.illustrators) == 0
                    and need_illustrators
                    and not is_archive_card
                ),
                is_bad_due_date=card.due is None and show_due,
            )

            if not card_is_ok:
                continue

            date = (
                load(
                    "common_report__card_date",
                    date=card.due.strftime("%d.%m (%a)").lower(),
                )
                if show_due
                else ""
            )

            paragraphs.append(
                load(
                    "publication_plans_job__card",
                    date=date,
                    url=card_fields.google_doc or card.url,
                    name=card_fields.title or card.name,
                    authors=format_possibly_plural(
                        load("common_role__author"), card_fields.authors
                    ),
                    editors=format_possibly_plural(
                        load("common_role__editor"), card_fields.editors
                    ),
                    illustrators=format_possibly_plural(
                        load("common_role__illustrator"), card_fields.illustrators
                    ),
                )
            )

        if parse_failure_counter > 0:
            logger.error(f"Unparsed cards encountered: {parse_failure_counter}")
        return paragraphs
