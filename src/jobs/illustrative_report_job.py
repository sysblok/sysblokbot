import datetime
import logging
import time
from typing import Callable, List
from urllib.parse import urlparse

from ..app_context import AppContext
from ..consts import TrelloListAlias, TrelloCustomFieldTypeAlias, TrelloCardColor
from ..strings import load
from ..trello.trello_client import TrelloClient
from ..trello.trello_objects import TrelloCustomField
from .base_job import BaseJob
from .utils import (check_trello_card, format_errors, format_possibly_plural,
                    get_no_access_marker, pretty_send)

logger = logging.getLogger(__name__)


class IllustrativeReportJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None], called_from_handler=False):
        paragraphs = []  # list of paragraph strings
        errors = {}

        paragraphs += IllustrativeReportJob._retrieve_cards_for_paragraph(
            app_context=app_context,
            title=load('illustrative_report_job__title_to_chief_editor'),
            list_aliases=(TrelloListAlias.TO_CHIEF_EDITOR, ),
            errors=errors,
            strict_archive_rules=False,
        )

        paragraphs += IllustrativeReportJob._retrieve_cards_for_paragraph(
            app_context=app_context,
            title=load('illustrative_report_job__title_edited_sometimes'),
            list_aliases=(TrelloListAlias.EDITED_SOMETIMES, ),
            errors=errors,
            strict_archive_rules=False,
        )

        paragraphs += IllustrativeReportJob._retrieve_cards_for_paragraph(
            app_context=app_context,
            title=load('common_report__section_title_editorial_board'),
            list_aliases=(TrelloListAlias.EDITED_NEXT_WEEK, TrelloListAlias.TO_SEO_EDITOR),
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
        list_ids = app_context.trello_client.get_list_id_from_aliases(list_aliases)
        cards = app_context.trello_client.get_cards(list_ids)
        parse_failure_counter = 0

        paragraphs = [
            load('common_report__list_title_and_size', title=title, length=len(cards))
        ]

        for card in cards:
            if not card:
                parse_failure_counter += 1
                continue

            card_fields = app_context.trello_client.get_custom_fields(card.id)

            label_names = [
                label.name for label in card.labels if label.color != TrelloCardColor.BLACK
            ]
            is_archive_card = load('common_trello_label__archive') in label_names

            card_is_ok = check_trello_card(
                card,
                errors,
                is_bad_title=(
                    card_fields.title is None and
                    card.lst.id not in (
                        app_context.trello_client.lists_config[TrelloListAlias.EDITED_NEXT_WEEK],
                        app_context.trello_client.lists_config[TrelloListAlias.TO_SEO_EDITOR]
                    )
                ),
                is_bad_google_doc=card_fields.google_doc is None,
                is_bad_authors=len(card_fields.authors) == 0,
            )

            if not card_is_ok:
                continue

            if not card_fields.cover and not is_archive_card:
                card_fields.cover = app_context.drive_client.create_folder_for_card(card)
                logger.info(f'Trying to put {card_fields.cover} as cover field for {card.url}')
                app_context.trello_client.set_card_custom_field(
                    card.id,
                    TrelloCustomFieldTypeAlias.COVER,
                    card_fields.cover,
                )

            cover = ''
            if card_fields.cover and not is_archive_card:
                if urlparse(card_fields.cover).scheme:
                    if app_context.drive_client.is_folder_empty(card_fields.cover):
                        cover = load(
                            'illustrative_report_job__card_cover_url_empty',
                            url=card_fields.cover
                        )
                    else:
                        cover = load(
                            'illustrative_report_job__card_cover_url',
                            url=card_fields.cover
                        )
                else:
                    cover = load('illustrative_report_job__card_cover', name=card_fields.cover)

            file_url = (
                card_fields.google_doc if urlparse(card_fields.google_doc).scheme else card.url
            )
            no_access_marker = get_no_access_marker(file_url, app_context.drive_client)
            card_text = load(
                'illustrative_report_job__card',
                url=file_url,
                name=card_fields.title or card.name,
                authors=format_possibly_plural('Автор', card_fields.authors),
                editors=format_possibly_plural('Редактор', card_fields.editors),
                illustrators=format_possibly_plural('Иллюстратор', card_fields.illustrators),
                cover=cover,
            )
            paragraphs.append(no_access_marker + card_text)

        if parse_failure_counter > 0:
            logger.error(f'Unparsed cards encountered: {parse_failure_counter}')
        return paragraphs
