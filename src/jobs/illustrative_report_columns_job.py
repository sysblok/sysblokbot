import logging
from typing import Callable, List
from urllib.parse import urlparse

from ..app_context import AppContext
from ..consts import TrelloListAlias, TrelloCustomFieldTypeAlias, TrelloCardColor
from ..strings import load
from ..tg.sender import pretty_send
from .base_job import BaseJob
from .utils import (
    check_trello_card,
    format_trello_labels,
    format_errors,
    format_possibly_plural,
    get_no_access_marker,
)

logger = logging.getLogger(__name__)


class IllustrativeReportColumnsJob(BaseJob):
    @staticmethod
    def _execute(
        app_context: AppContext, send: Callable[[str], None], called_from_handler=False
    ):
        paragraphs = []  # list of paragraph strings
        errors = {}

        paragraphs += IllustrativeReportColumnsJob._retrieve_cards_for_paragraph(
            app_context=app_context,
            title=load("illustrative_report_job__title_to_chief_editor"),
            list_aliases=(TrelloListAlias.TO_CHIEF_EDITOR,),
            errors=errors,
            strict_archive_rules=False,
        )

        paragraphs += IllustrativeReportColumnsJob._retrieve_cards_for_paragraph(
            app_context=app_context,
            title=load("illustrative_report_job__title_edited_sometimes"),
            list_aliases=(TrelloListAlias.EDITED_SOMETIMES,),
            errors=errors,
            strict_archive_rules=False,
        )

        paragraphs += IllustrativeReportColumnsJob._retrieve_cards_for_paragraph(
            app_context=app_context,
            title=load("common_report__section_title_editorial_board"),
            list_aliases=(
                TrelloListAlias.EDITED_NEXT_WEEK,
                TrelloListAlias.TO_SEO_EDITOR,
            ),
            errors=errors,
            strict_archive_rules=False,
        )

        paragraphs += IllustrativeReportColumnsJob._retrieve_cards_for_paragraph(
            app_context=app_context,
            title=load("common_report__section_title_proofreading"),
            list_aliases=(TrelloListAlias.PROOFREADING,),
            errors=errors,
            strict_archive_rules=False,
        )

        paragraphs += IllustrativeReportColumnsJob._retrieve_cards_for_paragraph(
            app_context=app_context,
            title=load("common_report__section_title_typesetting"),
            list_aliases=(TrelloListAlias.DONE,),
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
        """
        Returns a list of paragraphs that should always go in a single message.
        """
        logger.info(f'Started counting: "{title}"')
        list_ids = app_context.trello_client.get_list_id_from_aliases(list_aliases)
        cards = app_context.trello_client.get_cards(list_ids)
        parse_failure_counter = 0

        paragraphs = [
            load("common_report__list_title_and_size", title=title, length=len(cards))
        ]
        # additional labels to card title in report
        labels_to_display = [
            load("common_trello_label__main_post"),
            load("common_trello_label__glossary"),
            load("common_trello_label__interview"),
            load("common_trello_label__neuropoems"),
            load("common_trello_label__news"),
            load("common_trello_label__reviews"),
            load("common_trello_label__survey"),
            load("common_trello_label__test"),
            load("common_trello_label__visual_legacy"),
            load("common_trello_label__archive"),
            load("common_trello_label__digest"),
            load("common_trello_label__promo"),
            load("common_trello_label__video"),
            load("common_trello_label__visualisation"),
            load("common_trello_label__memes"),
            load("common_trello_label__scientist_blogs"),
            load("common_trello_label__podcasts"),
            load("common_trello_label__pishu_postcard_weekly"),
            load("common_trello_label__pishu_selection"),
        ]
        for card in cards:
            if not card:
                parse_failure_counter += 1
                continue

            card_fields = app_context.trello_client.get_custom_fields(card.id)

            label_names = [
                label.name
                for label in card.labels
                if label.color != TrelloCardColor.BLACK
            ]
            is_archive_card = load("common_trello_label__archive") in label_names

            card_is_ok = check_trello_card(
                card,
                errors,
                is_bad_title=(
                    card_fields.title is None
                    and card.lst.id
                    not in (
                        app_context.trello_client.lists_config[
                            TrelloListAlias.EDITED_NEXT_WEEK
                        ],
                        app_context.trello_client.lists_config[
                            TrelloListAlias.TO_SEO_EDITOR
                        ],
                    )
                ),
                is_bad_google_doc=card_fields.google_doc is None,
                is_bad_authors=len(card_fields.authors) == 0,
            )

            if not card_is_ok:
                continue

            if not card_fields.cover and not is_archive_card:
                card_fields.cover = app_context.drive_client.create_folder_for_card(
                    card
                )
                if card_fields.cover is None:
                    logger.error(f"The folder for {card.url} was not created")
                else:
                    logger.info(
                        f"Trying to put {card_fields.cover} as cover field for {card.url}"
                    )
                    app_context.trello_client.set_card_custom_field(
                        card.id,
                        TrelloCustomFieldTypeAlias.COVER,
                        card_fields.cover,
                    )

            cover = ""
            if card_fields.cover and not is_archive_card:
                if urlparse(card_fields.cover).scheme:
                    if app_context.drive_client.is_folder_empty(card_fields.cover):
                        cover = load(
                            "illustrative_report_job__card_cover_url_empty",
                            url=card_fields.cover,
                        )
                    else:
                        cover = load(
                            "illustrative_report_job__card_cover_url",
                            url=card_fields.cover,
                        )
                else:
                    cover = load(
                        "illustrative_report_job__card_cover", name=card_fields.cover
                    )

            file_url = (
                card_fields.google_doc
                if urlparse(card_fields.google_doc).scheme
                else card.url
            )
            no_access_marker = get_no_access_marker(file_url, app_context.drive_client)
            is_edited_sometimes = (
                card.lst.id
                == app_context.trello_client.lists_config[
                    TrelloListAlias.EDITED_SOMETIMES
                ]
            )
            card_labels = [label for label in label_names if label in labels_to_display]
            card_text = load(
                "illustrative_report_job__card",
                url=file_url,
                name=card_fields.title or card.name,
                labels=format_trello_labels(card_labels),
                authors=format_possibly_plural(
                    load("common_role__author"), card_fields.authors
                ),
                editors=format_possibly_plural(
                    load("common_role__editor"), card_fields.editors
                ),
                illustrators=format_possibly_plural(
                    load("common_role__illustrator"), card_fields.illustrators
                ),
                cover=cover,
            )
            paragraphs.append(no_access_marker + card_text)

        if parse_failure_counter > 0:
            logger.error(f"Unparsed cards encountered: {parse_failure_counter}")
        return paragraphs
