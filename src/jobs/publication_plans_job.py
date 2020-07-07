import datetime
import logging
import time
from typing import Callable, List

from ..app_context import AppContext
from .base_job import BaseJob
from ..consts import TrelloListAlias, TrelloCardColor
from ..trello.trello_client import TrelloClient
from .utils import format_errors, format_possibly_plural, pretty_send

logger = logging.getLogger(__name__)


class PublicationPlansJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None], called_from_handler=False):
        paragraphs = []  # list of paragraph strings
        errors = {}
        paragraphs.append('Всем привет!')

        paragraphs += PublicationPlansJob._retrieve_cards_for_paragraph(
            trello_client=app_context.trello_client,
            title='Публикуем на неделе',
            list_aliases=(TrelloListAlias.PROOFREADING, TrelloListAlias.DONE),
            errors=errors,
            show_due=True,
            strict_archive_rules=True,
        )

        paragraphs += PublicationPlansJob._retrieve_cards_for_paragraph(
            trello_client=app_context.trello_client,
            title='На редактуре',
            list_aliases=(TrelloListAlias.EDITED_NEXT_WEEK, ),
            errors=errors,
            show_due=False,
            need_illustrators=False,
            strict_archive_rules=False,
        )

        paragraphs.append('Спасибо авторам, редакторам, кураторам и иллюстраторам! 🤖❤️')

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

        paragraphs = [f'<b>{title}: {len(cards)}</b>']

        for card in cards:
            if not card:
                parse_failure_counter += 1
                continue

            card_fields = trello_client.get_custom_fields(card.id)

            label_names = [
                label.name for label in card.labels if label.color != TrelloCardColor.BLACK
            ]

            is_archive_card = 'Архив' in label_names

            this_card_bad_fields = []
            if (
                    card_fields.title is None and
                    card.lst.id != trello_client.lists_config[TrelloListAlias.EDITED_NEXT_WEEK]
            ):
                this_card_bad_fields.append('название поста')
            if card_fields.google_doc is None:
                this_card_bad_fields.append('google doc')
            if len(card_fields.authors) == 0:
                this_card_bad_fields.append('автор')
            if len(card_fields.editors) == 0:  # and 'Архив' not in label_names:
                this_card_bad_fields.append('редактор')
            if (
                    len(card_fields.illustrators) == 0 and need_illustrators and
                    not is_archive_card
            ):
                this_card_bad_fields.append('иллюстратор')
            if card.due is None and show_due:
                this_card_bad_fields.append('дата публикации')
            if len(label_names) == 0:
                this_card_bad_fields.append('рубрика')

            if (
                    len(this_card_bad_fields) > 0
                    and not (is_archive_card and not strict_archive_rules)
            ):
                logger.info(
                    f'Trello card is unsuitable for publication: {card.url} {this_card_bad_fields}'
                )
                errors[card] = this_card_bad_fields
                continue

            paragraphs.append(
                PublicationPlansJob._format_card(
                    card, card_fields, show_due=show_due
                )
            )

        if parse_failure_counter > 0:
            logger.error(f'Unparsed cards encountered: {parse_failure_counter}')
        return paragraphs

    @staticmethod
    def _format_card(
            card, card_fields, show_due=True
    ) -> str:
        card_text = (
            f'<a href="{card_fields.google_doc or card.url}">'
            f'{card_fields.title or card.name}</a>\n'
        )

        card_text += format_possibly_plural('Автор', card_fields.authors)
        card_text += format_possibly_plural('Редактор', card_fields.editors)
        card_text += format_possibly_plural('Иллюстратор', card_fields.illustrators)

        if show_due:
            card_text = (
                f'<b>{card.due.strftime("%d.%m (%a)").lower()}</b> — {card_text}'
            )
        return card_text.strip()
