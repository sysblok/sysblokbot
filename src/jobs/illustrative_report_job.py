import logging
from operator import itemgetter
from typing import Callable, List, Tuple, Dict
from collections import defaultdict
from urllib.parse import urlparse

from ..app_context import AppContext
from ..consts import TrelloListAlias
from ..strings import load
from .base_job import BaseJob
from .utils import (format_errors, format_labels,
                    get_no_access_marker, pretty_send, check_trello_card)

logger = logging.getLogger(__name__)


class IllustrativeReportJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None], called_from_handler=False):
        paragraphs = []  # list of paragraph strings
        errors = {}

        result = IllustrativeReportJob._retrieve_cards(
            app_context=app_context,
            list_aliases=(
                TrelloListAlias.EDITED_SOMETIMES,
                TrelloListAlias.EDITED_NEXT_WEEK,
                TrelloListAlias.TO_SEO_EDITOR
            ),
            errors=errors,
        )

        if len(errors) > 0:
            paragraphs = format_errors(errors)
        else:
            # go first
            no_illustrators_cards = result.get('')
            if no_illustrators_cards and len(no_illustrators_cards) > 0:
                paragraphs += IllustrativeReportJob._get_cards_group_paragraphs(
                    load('illustrative_report_job__no_illustrators'),
                    no_illustrators_cards
                )
            for illustrators, cards in result.items():
                if illustrators == '':
                    # already processed
                    continue
                paragraphs += IllustrativeReportJob._get_cards_group_paragraphs(
                    illustrators,
                    cards
                )
        logger.warning(paragraphs)

        pretty_send(paragraphs, send)

    @staticmethod
    def _retrieve_cards(
            app_context: AppContext,
            list_aliases: List[TrelloListAlias],
            errors: dict,
    ) -> Dict[str, List[Tuple[bool, str]]]:
        """
        Returns card reports texts grouped by illustrators
        """
        logger.info(f'Started retrieving cards')
        list_ids = app_context.trello_client.get_list_id_from_aliases(list_aliases)
        cards = app_context.trello_client.get_cards(list_ids)
        parse_failure_counter = 0

        result = defaultdict(list)
        # additional labels to card title in report
        labels_to_display = [load('common_trello_label__main_post')]
        for card in cards:
            if not card:
                parse_failure_counter += 1
                continue

            card_fields = app_context.trello_client.get_custom_fields(card.id)

            label_names = [label.name for label in card.labels]
            is_skipped_card = (
                load('common_trello_label__archive') in label_names or
                load('common_trello_label__mems') in label_names or
                load('common_trello_label__digest') in label_names or
                load('common_trello_label__video') in label_names
            )

            if is_skipped_card:
                continue

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
                is_bad_cover=card_fields.cover is None
            )

            if not card_is_ok:
                continue

            cover = IllustrativeReportJob._get_cover_report_field(
                app_context,
                card_fields.cover if card_fields.cover else ''
            )
            doc_url = (
                card_fields.google_doc if urlparse(card_fields.google_doc).scheme else ''
            )
            no_access_marker = get_no_access_marker(doc_url, app_context.drive_client)
            is_edited_sometimes = (
                card.lst.id == app_context.trello_client.lists_config[
                    TrelloListAlias.EDITED_SOMETIMES
                ]
            )
            card_labels = []
            if is_edited_sometimes:
                card_labels += [load('illustrative_report_job__edited_label')]
            card_labels += [label for label in label_names if label in labels_to_display]
            card_text = load(
                'illustrative_report_job__card_new',
                url=doc_url,
                name=card_fields.title or card.name,
                labels=format_labels(card_labels),
                cover=cover,
                card=load('illustrative_report_job__card_url', url=card.url)
            )
            card_illustrators = ''
            if card_fields.illustrators:
                card_illustrators = ", ".join(sorted(card_fields.illustrators))
            result[card_illustrators].append(
                (is_edited_sometimes, no_access_marker + card_text)
            )

        if parse_failure_counter > 0:
            logger.error(f'Unparsed cards encountered: {parse_failure_counter}')
        logger.info(f'Finished retrieving cards')
        return result

    @staticmethod
    def _get_cover_report_field(app_context: AppContext, cover_folder_path: str) -> str:
        """
        Returns cover field text for card in report
        """
        if urlparse(cover_folder_path).scheme:
            if app_context.drive_client.is_folder_empty(cover_folder_path):
                return load(
                    'illustrative_report_job__card_cover_url_empty',
                    url=cover_folder_path
                )
            return load(
                    'illustrative_report_job__card_cover_url',
                    url=cover_folder_path
                )
        return load('illustrative_report_job__card_cover', name=cover_folder_path)

    @staticmethod
    def _get_cards_group_paragraphs(
            illustrators: str, cards: List[Tuple[bool, str]]
    ) -> List[str]:
        """
        Returns a list of paragraphs for illustrators group
        """
        if len(cards) == 0:
            return []
        paragraphs = [load(
            'illustrative_report_job__author_title', name=illustrators
        )]
        paragraphs += [
            card_text for _, card_text in sorted(
                cards, key=itemgetter(0), reverse=True
            )
        ]
        return paragraphs
