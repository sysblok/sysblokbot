import datetime
import logging
import time
from typing import Callable, List

from ..app_context import AppContext
from .base_job import BaseJob
from ..consts import TrelloListAlias, TrelloCustomFieldTypeAlias, TrelloCardColor
from ..trello.trello_client import TrelloClient
from ..trello.trello_objects import TrelloCustomField
from .utils import format_errors, format_possibly_plural, pretty_send

logger = logging.getLogger(__name__)


class IllustrativeReportJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None]):
        paragraphs = []  # list of paragraph strings
        errors = {}

        paragraphs += IllustrativeReportJob._retrieve_cards_for_paragraph(
            app_context=app_context,
            title='На редактуре',
            list_aliases=(TrelloListAlias.EDITED_NEXT_WEEK, ),
            errors=errors,
            strict_archive_rules=False,
        )

        if len(errors) > 0:
            paragraphs = format_errors(errors)

        logger.warning(paragraphs)

        pretty_send(paragraphs, send)

    @staticmethod
    def _retrieve_cards_for_paragraph(
            app_context: AppContext,
            title: str,
            list_aliases: List[TrelloListAlias],
            errors: dict,
            moved_from_exclusive: List[TrelloListAlias] = (),
            show_post_title=False,
            need_editor=True,
            need_title=False,
            strict_archive_rules=True,
    ) -> List[str]:
        '''
        Returns a list of paragraphs that should always go in a single message.
        '''
        logger.info(f'Started counting: "{title}"')
        list_ids = [app_context.trello_client.lists_config[alias] for alias in list_aliases]
        cards = app_context.trello_client.get_cards(list_ids)
        parse_failure_counter = 0

        paragraphs = [f'<b>{title}: {len(cards)}</b>']

        for card in cards:
            if not card:
                parse_failure_counter += 1
                continue

            card_fields = app_context.trello_client.get_custom_fields(card.id)

            label_names = [
                label.name for label in card.labels if label.color != TrelloCardColor.BLACK
            ]
            is_archive_card = 'Архив' in label_names

            this_card_bad_fields = []

            if (
                    title.title is None and
                    card.lst.id != app_context.trello_client.lists_config[
                        TrelloListAlias.EDITED_NEXT_WEEK
                    ]
            ):
                this_card_bad_fields.append('название поста')
            if card_fields.google_doc is None:
                this_card_bad_fields.append('google doc')
                this_card_bad_fields.append('автор')

            if (
                    len(this_card_bad_fields) > 0
                    and not is_archive_card
            ):
                logger.info(
                    f'Trello card is unsuitable for publication: {card.url} {this_card_bad_fields}'
                )
                errors[card] = this_card_bad_fields
                continue

            if not card_fields.cover or True:
                card_fields.cover = app_context.drive_client.create_folder_for_card(card)
                logger.info(f'Trying to put {card_fields.cover} as cover field for {card.url}')
                app_context.trello_client.set_card_custom_field(
                    card.id,
                    TrelloCustomFieldTypeAlias.COVER,
                    card_fields.cover,
                )

            paragraphs.append(
                IllustrativeReportJob._format_card(
                    card,
                    card_fields,
                    is_archive_card=is_archive_card,
                )
            )

        if parse_failure_counter > 0:
            logger.error(f'Unparsed cards encountered: {parse_failure_counter}')
        return paragraphs

    @staticmethod
    def _format_card(card, card_fields, is_archive_card=False) -> str:
        card_text = (
            f'<a href="{card_fields.google_doc or card.url}">'
            f'{card_fields.title or card.name}</a>\n'
        )

        card_text += format_possibly_plural('Автор', card_fields.authors)
        card_text += format_possibly_plural('Редактор', card_fields.editors)
        card_text += format_possibly_plural('Иллюстратор', card_fields.illustrators)

        if card_fields.cover and not is_archive_card:
            card_text += f'\n<a href="{card_fields.cover}">Папка для обложки</a>'

        return card_text.strip()
