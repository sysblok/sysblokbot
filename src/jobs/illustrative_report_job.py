import datetime
import logging
import time
from typing import Callable, List

from ..app_context import AppContext
from .base_job import BaseJob
from ..consts import TrelloListAlias, TrelloCustomFieldTypeAlias, TrelloCardColor
from ..trello.trello_client import TrelloClient
from .utils import format_errors, pretty_send

logger = logging.getLogger(__name__)


class IllustrativeReportJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None]):
        paragraphs = []  # list of paragraph strings
        errors = {}

        paragraphs += IllustrativeReportJob._retrieve_cards_for_paragraph(
            trello_client=app_context.trello_client,
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
    def _card_is_urgent(card):
        return 'Срочно' in [label.name for label in card.labels]

    @staticmethod
    def _retrieve_cards_for_paragraph(
            trello_client: TrelloClient,
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
        list_ids = [trello_client.lists_config[alias] for alias in list_aliases]
        cards = trello_client.get_cards(list_ids)
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
                    title.title is None and
                    card.lst.id != trello_client.lists_config[TrelloListAlias.EDITED_NEXT_WEEK]
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
    def _format_card(card, card_fields, is_archive_card=False, drive_folder_url='') -> str:
        card_text = (
            f'<a href="{card_fields.google_doc or card.url}">'
            f'{card_fields.title or card.name}</a>\n'
        )

        card_text += IllustrativeReportJob._format_possibly_plural(
            'Автор', card_fields.authors
        )
        card_text += IllustrativeReportJob._format_possibly_plural(
            'Редактор', card_fields.editors
        )
        card_text += IllustrativeReportJob._format_possibly_plural(
            'Иллюстратор', card_fields.illustrators
        )

        if drive_folder_url and not is_archive_card:
            card_text += f'\n<a href="{drive_folder_url}">Папка для обложки</a>'

        return card_text.strip()

    @staticmethod
    def _format_possibly_plural(name: str, values: List[str]) -> str:
        if len(values) == 0:
            return ''
        # yeah that's a bit sexist
        return f'{name}{"ы" if len(values) > 1 else ""}: {", ".join(values)}. '
