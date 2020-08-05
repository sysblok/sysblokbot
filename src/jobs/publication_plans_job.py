import datetime
import logging
import time
from typing import Callable, List

from ..app_context import AppContext
from ..consts import TrelloListAlias, TrelloCardColor
from ..strings import load
from ..trello.trello_client import TrelloClient
from .base_job import BaseJob
from .utils import format_errors, format_possibly_plural, pretty_send

logger = logging.getLogger(__name__)


class PublicationPlansJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None], called_from_handler=False):
        paragraphs = [load('publication_plans_job__intro')]  # list of paragraph strings
        errors = {}

        paragraphs += PublicationPlansJob._retrieve_cards_for_paragraph(
            trello_client=app_context.trello_client,
            title=load('publication_plans_job__title_publish_this_week'),
            list_aliases=(TrelloListAlias.PROOFREADING, TrelloListAlias.DONE),
            errors=errors,
            show_due=True,
            strict_archive_rules=True,
        )

        paragraphs += PublicationPlansJob._retrieve_cards_for_paragraph(
            trello_client=app_context.trello_client,
            title=load('publication_plans_job__title_editor'),
            list_aliases=(TrelloListAlias.EDITED_NEXT_WEEK, ),
            errors=errors,
            show_due=False,
            need_illustrators=False,
            strict_archive_rules=False,
        )

        paragraphs.append(load('publication_plans_job__outro'))

        if len(errors) > 0:
            paragraphs = format_errors(errors)

        pretty_send(paragraphs, send)

    @staticmethod
    def _retrieve_cards_for_paragraph(
            trello_client: TrelloClient,
            title: str,
            list_aliases: List[TrelloListAlias],
            errors: dict,
            show_due=True,
            need_illustrators=True,
            strict_archive_rules=False,
    ) -> List[str]:
        '''
        Returns a list of paragraphs that should always go in a single message.
        '''
        logger.info(f'Started counting: "{title}"')
        list_ids = trello_client.get_list_id_from_aliases(list_aliases)
        cards = trello_client.get_cards(list_ids)
        if show_due:
            cards.sort(key=lambda card: card.due or datetime.datetime.min)
        parse_failure_counter = 0

        paragraphs = [load('publication_plans_job__title_and_size', title=title, length=len(cards))]

        for card in cards:
            if not card:
                parse_failure_counter += 1
                continue

            card_fields = trello_client.get_custom_fields(card.id)

            label_names = [
                label.name for label in card.labels if label.color != TrelloCardColor.BLACK
            ]

            is_archive_card = load('common__label_archive') in label_names

            this_card_bad_fields = []
            if (
                    card_fields.title is None and
                    card.lst.id != trello_client.lists_config[TrelloListAlias.EDITED_NEXT_WEEK]
            ):
                this_card_bad_fields.append(load('common__post_title'))
            if card_fields.google_doc is None:
                this_card_bad_fields.append(load('common__post_google_doc'))
            if len(card_fields.authors) == 0:
                this_card_bad_fields.append(load('common__post_author'))
            if len(card_fields.editors) == 0:  # and load('common__label_archive') not in label_names:
                this_card_bad_fields.append(load('common__post_editor'))
            if (
                    len(card_fields.illustrators) == 0 and need_illustrators and
                    not is_archive_card
            ):
                this_card_bad_fields.append(load('common__post_illustrator'))
            if card.due is None and show_due:
                this_card_bad_fields.append(load('common__post_date'))
            if len(label_names) == 0:
                this_card_bad_fields.append(load('common__post_rubric'))

            if (
                    len(this_card_bad_fields) > 0
                    and not (is_archive_card and not strict_archive_rules)
            ):
                logger.info(
                    f'Trello card is unsuitable for publication: {card.url} {this_card_bad_fields}'
                )
                errors[card] = this_card_bad_fields
                continue

            date = load(
                'publication_plans_job__card_date', date=card.due.strftime("%d.%m (%a)").lower()
            ) if show_due else ''

            paragraphs.append(
                load(
                    'publication_plans_job__card',
                    date=date,
                    url=card_fields.google_doc or card.url,
                    name=card_fields.title or card.name,
                    authors=format_possibly_plural('Автор', card_fields.authors),
                    editors=format_possibly_plural('Редактор', card_fields.editors),
                    illustrators=format_possibly_plural('Иллюстратор', card_fields.illustrators),
                )
            )

        if parse_failure_counter > 0:
            logger.error(f'Unparsed cards encountered: {parse_failure_counter}')
        return paragraphs
