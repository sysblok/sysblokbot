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


class EditorialReportJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None], called_from_handler=False):
        paragraphs = []  # list of paragraph strings
        errors = {}
        paragraphs.append(load('editorial_report_job__intro'))

        paragraphs += EditorialReportJob._retrieve_cards_for_paragraph(
            trello_client=app_context.trello_client,
            title=load('editorial_report_job__title_redacted'),
            list_aliases=(TrelloListAlias.EDITED_SOMETIMES, TrelloListAlias.TO_CHIEF_EDITOR),
            errors=errors,
            need_title=True,
            strict_archive_rules=False,
        )

        paragraphs += EditorialReportJob._retrieve_cards_for_paragraph(
            trello_client=app_context.trello_client,
            title=load('editorial_report_job__title_revision'),
            list_aliases=(TrelloListAlias.IN_PROGRESS, ),
            errors=errors,
            moved_from_exclusive=(TrelloListAlias.EDITED_NEXT_WEEK, ),
            strict_archive_rules=False,
        )

        paragraphs += EditorialReportJob._retrieve_cards_for_paragraph(
            trello_client=app_context.trello_client,
            title=load('editorial_report_job__title_editors'),
            list_aliases=(TrelloListAlias.EDITED_NEXT_WEEK, ),
            errors=errors,
            strict_archive_rules=False,
        )

        paragraphs += EditorialReportJob._retrieve_cards_for_paragraph(
            trello_client=app_context.trello_client,
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
            load('editorial_report_job__title_and_size', title=title, length=len(cards_filtered))
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

            label_names = [
                label.name for label in card.labels if label.color != TrelloCardColor.BLACK
            ]
            is_archive_card = 'Архив' in label_names

            this_card_bad_fields = []
            if card_fields.title is None and need_title:
                this_card_bad_fields.append('название поста')
            if card_fields.google_doc is None:
                this_card_bad_fields.append('google doc')
            if len(card_fields.authors) == 0:
                this_card_bad_fields.append('автор')
            if len(card_fields.editors) == 0 and need_editor:
                this_card_bad_fields.append('редактор')

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
                load(
                    'editorial_report_job__card',
                    date=card.due.strftime('%d.%m').lower() if card.due else '??.??',
                    urgent='(Срочно!)' if EditorialReportJob._card_is_urgent(card) else '',
                    url=card_fields.google_doc or card.url,
                    name=card_fields.title or card.name,
                    authors=format_possibly_plural('Автор', card_fields.authors),
                    editors=format_possibly_plural('Редактор', card_fields.editors),
                )
            )

        if parse_failure_counter > 0:
            logger.error(f'Unparsed cards encountered: {parse_failure_counter}')
        return paragraphs
