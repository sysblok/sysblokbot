import logging
from enum import IntEnum
from typing import Callable, List, Tuple
from urllib.parse import urlparse

from ..app_context import AppContext
from ..consts import TrelloCardColor, TrelloCustomFieldTypeAlias, TrelloListAlias, BoardCardColor
from ..strings import load
from ..tg.sender import pretty_send, TelegramSender
from .base_job import BaseJob

logger = logging.getLogger(__name__)


class IllustratorFolderState(IntEnum):
    EXISTING = 0
    CREATED = 1
    INCORRECT_URL = 2


class CreateFoldersForIllustratorsJob(BaseJob):
    @staticmethod
    async def _execute(
            app_context: AppContext,
            send: Callable[[str], None],
            called_from_handler=False,
            *args,
            **kwargs
    ):
        paragraphs = []  # list of paragraph strings

        result = CreateFoldersForIllustratorsJob._create_folders(
            app_context=app_context,
            list_aliases=(
                TrelloListAlias.TO_CHIEF_EDITOR,
                TrelloListAlias.EDITED_SOMETIMES,
                TrelloListAlias.EDITED_NEXT_WEEK,
                TrelloListAlias.TO_SEO_EDITOR,
            ),
        )

        if len(result) == 0:
            paragraphs += [load("create_folders_for_illustrators_job__no_cards")]
        else:
            current_state = None
            for card in sorted(result, key=lambda card: card[0]):
                if card[0] != current_state:
                    # new section start
                    paragraphs.append(
                        CreateFoldersForIllustratorsJob._get_folder_state_description(
                            card[0]
                        )
                    )
                    current_state = card[0]
                paragraphs.append(card[1])

        await pretty_send(
            paragraphs,
            # send
            TelegramSender().bot,
            kwargs['chat_id'],
            disable_notification=False,
            disable_web_page_preview=False,
        )

    @staticmethod
    def _create_folders(
        app_context: AppContext,
        list_aliases: List[TrelloListAlias],
    ) -> List[Tuple[IllustratorFolderState, str]]:
        logger.info("Started counting:")
        if app_context.trello_client.deprecated:
            list_ids = app_context.focalboard_client.get_list_id_from_aliases(list_aliases)
            cards = app_context.focalboard_client.get_cards(list_ids)
        else:
            list_ids = app_context.trello_client.get_list_id_from_aliases(list_aliases)
            cards = app_context.trello_client.get_cards(list_ids)

        parse_failure_counter = 0
        result = []
        for card in cards:
            if not card:
                parse_failure_counter += 1
                continue

            if app_context.trello_client.deprecated:
                card_fields = app_context.focalboard_client.get_custom_fields(card.id)
            else:
                card_fields = app_context.trello_client.get_custom_fields(card.id)

            label_names = [
                label.name
                for label in card.labels
                if label.color not in [TrelloCardColor.BLACK, BoardCardColor.BLACK]
            ]
            is_archive_card = load("common_trello_label__archive") in label_names

            if is_archive_card:
                continue

            folder_state = IllustratorFolderState.INCORRECT_URL
            if card_fields.cover:
                # filled cover field
                if urlparse(card_fields.cover).scheme:
                    # existing folder path is correct
                    cover = load(
                        "create_folders_for_illustrators_job__cover",
                        url=card_fields.cover,
                    )
                    folder_state = IllustratorFolderState.EXISTING
                else:
                    cover = load(
                        "create_folders_for_illustrators_job__bad_cover_url",
                        url=card_fields.cover,
                    )
                    folder_state = IllustratorFolderState.INCORRECT_URL
            else:
                # create folder for cover
                card_fields.cover = app_context.drive_client.create_folder_for_card(
                    card
                )
                if card_fields.cover is None:
                    cover = load(
                        "create_folders_for_illustrators_job__bad_cover_url",
                        url=card_fields.cover,
                    )
                    folder_state = IllustratorFolderState.INCORRECT_URL
                    logger.error(f"The folder for card {card.url} was not created")
                else:
                    # save path to folder into trello card
                    logger.info(
                        f"Trying to put {card_fields.cover} as cover field for {card.url}"
                    )
                    if app_context.trello_client.deprecated:
                        app_context.focalboard_client.set_card_custom_field(
                            card,
                            TrelloCustomFieldTypeAlias.COVER,
                            card_fields.cover,
                        )
                    else:
                        app_context.trello_client.set_card_custom_field(
                            card.id,
                            TrelloCustomFieldTypeAlias.COVER,
                            card_fields.cover,
                        )
                    cover = load(
                        "create_folders_for_illustrators_job__cover",
                        url=card_fields.cover,
                    )
                    folder_state = IllustratorFolderState.CREATED

            card_text = load(
                "create_folders_for_illustrators_job__card",
                url=card.url,
                name=card_fields.title or card.name,
                cover=cover,
            )
            result.append((folder_state, card_text))

        if parse_failure_counter > 0:
            logger.error(f"Unparsed cards encountered: {parse_failure_counter}")
        return result

    @staticmethod
    def _get_folder_state_description(state: IllustratorFolderState) -> str:
        """Returns string representing the status of folder creation"""
        if state == IllustratorFolderState.EXISTING:
            return load("create_folders_for_illustrators_job__section_existing")
        elif state == IllustratorFolderState.CREATED:
            return load("create_folders_for_illustrators_job__section_created")
        elif state == IllustratorFolderState.INCORRECT_URL:
            return load("create_folders_for_illustrators_job__section_incorrect_url")

    @staticmethod
    def _usage_muted():
        return True
