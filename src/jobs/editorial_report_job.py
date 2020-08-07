import datetime
import logging
import time
from typing import Callable, List

from ..app_context import AppContext
from ..consts import TrelloListAlias, TrelloCardColor
from ..strings import load
from ..drive.drive_client import GoogleDriveClient
from ..trello.trello_client import TrelloClient
from .base_job import BaseJob
from .utils import check_trello_card, format_errors, format_possibly_plural, get_no_access_marker, pretty_send

logger = logging.getLogger(__name__)


class EditorialReportJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None], called_from_handler=False):
        paragraphs = []  # list of paragraph strings
        errors = {}
        paragraphs.append(load('editorial_report_job__intro'))

        paragraphs += EditorialReportJob._retrieve_cards_for_paragraph(
            trello_client=app_context.trello_client,
            drive_client=app_context.drive_client,
            title=load('editorial_report_job__title_redacted'),
            list_aliases=(TrelloListAlias.EDITED_SOMETIMES, TrelloListAlias.TO_CHIEF_EDITOR),
            errors=errors,
            need_title=True,
            strict_archive_rules=False,
        )

        paragraphs += EditorialReportJob._retrieve_cards_for_paragraph(
            trello_client=app_context.trello_client,
            drive_client=app_context.drive_client,
            title=load('editorial_report_job__title_revision'),
            list_aliases=(TrelloListAlias.IN_PROGRESS, ),
            errors=errors,
            moved_from_exclusive=(TrelloListAlias.EDITED_NEXT_WEEK, ),
            strict_archive_rules=False,
        )

        paragraphs += EditorialReportJob._retrieve_cards_for_paragraph(
            trello_client=app_context.trello_client,
            drive_client=app_context.drive_client,
            title=load('common_report__section_title_editorial_board'),
            list_aliases=(TrelloListAlias.EDITED_NEXT_WEEK, ),
            errors=errors,
            strict_archive_rules=False,
        )

        paragraphs += EditorialReportJob._retrieve_cards_for_paragraph(
            trello_client=app_context.trello_client,
            drive_client=app_context.drive_client,
            title=load('editorial_report_job__title_editors_pending'),
            list_aliases=(TrelloListAlias.TO_EDITOR, ),
            errors=errors,
            need_editor=False,
            strict_archive_rules=False,
        )

        if len(errors) > 0:
            paragraphs = format_errors(errors)

        logger.warning(paragraphs)

        pretty_send(paragraphs, send)

    @staticmethod
    def _card_is_urgent(card):
        return load('common_trello_label__urgent') in [label.name for label in card.labels]

    @staticmethod
    def _retrieve_cards_for_paragraph(
            trello_client: TrelloClient,
            drive_client: GoogleDriveClient,
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
        list_ids = trello_client.get_list_id_from_aliases(list_aliases)
        list_moved_from_ids = trello_client.get_list_id_from_aliases(moved_from_exclusive)
        cards = trello_client.get_cards(list_ids)
        parse_failure_counter = 0

        card_ids = [card.id for card in cards]
        # TODO: merge them somehow
        cards_actions = trello_client.get_action_update_cards(card_ids)
        cards_actions_create = trello_client.get_action_create_cards(card_ids)

        cards_filtered = []

        for card in cards:
            if not card:
                parse_failure_counter += 1
                continue

            actions_moved_here = [
                action for action in cards_actions[card.id]
                if (
                    action.list_after_id == card.lst.id
                    and (
                        len(list_moved_from_ids) == 0
                        or action.list_before_id in list_moved_from_ids
                    )
                )
            ] + [
                action for action in cards_actions_create[card.id]
                if (
                    action.list_id == card.lst.id
                    and len(list_moved_from_ids) == 0
                )
            ]
            actions_moved_here.sort(key=lambda action: action.date, reverse=True)

            if len(actions_moved_here) == 0:
                if len(moved_from_exclusive) > 0:
                    # otherwise we don't really care where the card came from
                    continue
                logger.info(f'Card {card.url} unexpectedly appeared in list {card.lst.name}')
            else:
                card.due = actions_moved_here[0].date
            cards_filtered.append(card)

        paragraphs = [
            load('common_report__list_title_and_size', title=title, length=len(cards_filtered))
        ]

        for card in sorted(
            cards_filtered,
            key=lambda card: (
                not EditorialReportJob._card_is_urgent(card), card.due is None, card.due
            )
        ):
            if not card:
                parse_failure_counter += 1
                continue

            card_fields = trello_client.get_custom_fields(card.id)

            card_is_ok = check_trello_card(
                card,
                errors,
                is_bad_title=(
                    card_fields.title is None and need_title
                ),
                is_bad_google_doc=card_fields.google_doc is None,
                is_bad_authors=len(card_fields.authors) == 0,
                is_bad_editors=len(card_fields.editors) == 0 and need_editor,
            )

            if not card_is_ok:
                continue

            url = card_fields.google_doc or card.url
            paragraphs.append(
                load(
                    'editorial_report_job__card_2',
                    date=card.due.strftime('%d.%m').lower() if card.due else '??.??',
                    urgent='(Срочно!)' if EditorialReportJob._card_is_urgent(card) else '',
                    no_file_access=get_no_access_marker(url, drive_client),
                    url=url,
                    name=card_fields.title or card.name,
                    authors=format_possibly_plural('Автор', card_fields.authors),
                    editors=format_possibly_plural('Редактор', card_fields.editors),
                )
            )

        if parse_failure_counter > 0:
            logger.error(f'Unparsed cards encountered: {parse_failure_counter}')
        return paragraphs
