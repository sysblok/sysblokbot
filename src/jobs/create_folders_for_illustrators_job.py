import logging
from typing import Callable, List

from ..app_context import AppContext
from ..consts import TrelloListAlias, TrelloCustomFieldTypeAlias, TrelloCardColor
from ..strings import load
from .base_job import BaseJob
from .utils import (check_trello_card, format_errors, pretty_send)

logger = logging.getLogger(__name__)


class CreateFoldersForIllustratorsJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None], called_from_handler=False):
        errors = {}
        paragraphs = []  # list of paragraph strings

        CreateFoldersForIllustratorsJob._create_folders(
            app_context=app_context,
            list_aliases=(TrelloListAlias.TO_CHIEF_EDITOR, TrelloListAlias.EDITED_SOMETIMES,
                          TrelloListAlias.EDITED_NEXT_WEEK, TrelloListAlias.TO_SEO_EDITOR),
            errors=errors
        )
        if len(errors) > 0:
            paragraphs = format_errors(errors)
        else:
            paragraphs = ['Successfully created']
        pretty_send(paragraphs, send)

    @staticmethod
    def _create_folders(
        app_context: AppContext,
        list_aliases: List[TrelloListAlias],
        errors: dict
    ):
        logger.info(f'Started counting:')
        list_ids = app_context.trello_client.get_list_id_from_aliases(list_aliases)
        cards = app_context.trello_client.get_cards(list_ids)

        parse_failure_counter = 0
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
                if card_fields.cover is None:
                    logger.error(f'The folder for card {card.url} was not created')
                    continue
                logger.info(f'Trying to put {card_fields.cover} as cover field for {card.url}')
                app_context.trello_client.set_card_custom_field(
                    card.id,
                    TrelloCustomFieldTypeAlias.COVER,
                    card_fields.cover,
                )
        if parse_failure_counter > 0:
            logger.error(f'Unparsed cards encountered: {parse_failure_counter}')
