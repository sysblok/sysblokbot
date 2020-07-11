import datetime
import logging
from typing import Callable, List

from ..app_context import AppContext
from ..consts import TrelloCardColor, TrelloListAlias
from ..db.db_client import DBClient
from ..sheets.sheets_client import GoogleSheetsClient
from ..strings import load
from ..trello.trello_client import TrelloClient
from .base_job import BaseJob
from . import utils

logger = logging.getLogger(__name__)


class TrelloBoardStateJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None], called_from_handler=False):
        paragraphs = [load('trello_board_state_job__intro')]  # list of paragraph strings

        paragraphs += TrelloBoardStateJob._retrieve_cards_for_paragraph(
            app_context=app_context,
            title=load('trello_board_state_job__title_author_missing'),
            list_aliases=(
                TrelloListAlias.IN_PROGRESS,
                TrelloListAlias.TO_EDITOR,
                TrelloListAlias.EDITED_NEXT_WEEK,
                TrelloListAlias.EDITED_SOMETIMES,
                TrelloListAlias.TO_CHIEF_EDITOR,
                TrelloListAlias.PROOFREADING,
                TrelloListAlias.DONE,
            ),
            filter_func=lambda card: not card.members,
            show_due=False,
            show_members=False,
        )

        paragraphs += TrelloBoardStateJob._retrieve_cards_for_paragraph(
            app_context=app_context,
            title=load('trello_board_state_job__title_due_date_missing'),
            list_aliases=(TrelloListAlias.IN_PROGRESS, ),
            filter_func=lambda card: not card.due,
            show_due=False
        )

        paragraphs += TrelloBoardStateJob._retrieve_cards_for_paragraph(
            app_context=app_context,
            title=load('trello_board_state_job__title_tag_missing'),
            list_aliases=(
                TrelloListAlias.IN_PROGRESS,
                TrelloListAlias.TO_EDITOR,
                TrelloListAlias.EDITED_NEXT_WEEK,
                TrelloListAlias.EDITED_SOMETIMES,
                TrelloListAlias.TO_CHIEF_EDITOR,
                TrelloListAlias.PROOFREADING,
                TrelloListAlias.DONE,
            ),
            filter_func=lambda card: not card.labels,
            show_due=False
        )

        all_cards = app_context.trello_client.get_cards()
        members_with_cards = set()
        for card in all_cards:
            members_with_cards = members_with_cards.union(set(card.members))

        paragraphs += TrelloBoardStateJob._retrieve_cards_for_paragraph(
            app_context=app_context,
            title=load('trello_board_state_job__title_due_date_expired'),
            list_aliases=(TrelloListAlias.IN_PROGRESS, ),
            filter_func=TrelloBoardStateJob._is_deadline_missed,
        )

        utils.pretty_send(paragraphs, send)

    @staticmethod
    def _is_deadline_missed(card) -> bool:
        return card.due is not None and card.due.date() < datetime.datetime.now().date()

    @staticmethod
    def _retrieve_cards_for_paragraph(
            app_context: AppContext,
            title: str,
            list_aliases: List[str],
            filter_func: Callable,
            show_due=True,
            show_members=True,
    ) -> List[str]:
        '''
        Returns a list of paragraphs that should always go in a single message.
        '''
        logger.info(f'Started counting: "{title}"')
        list_ids = app_context.trello_client.get_list_id_from_aliases(list_aliases)
        cards = list(filter(filter_func, app_context.trello_client.get_cards(list_ids)))
        parse_failure_counter = 0

        paragraphs = [
            load('trello_board_state_job__title_and_size', title=title, length=len(cards))
        ]

        for card in cards:
            if not card:
                parse_failure_counter += 1
                continue
            paragraphs.append(
                TrelloBoardStateJob._format_card(
                    card,
                    app_context,
                    show_due=show_due,
                    show_members=show_members
                )
            )

        if parse_failure_counter > 0:
            logger.error(f'Unparsed cards encountered: {parse_failure_counter}')
        return paragraphs

    @staticmethod
    def _format_card(card, app_context, show_due=True, show_members=True) -> str:
        labels = load(
            'trello_board_state_job__card_labels',
            names=", ".join(
                # We filter BLACK cards as this is an auxiliary label
                label.name for label in card.labels
                if label.color != TrelloCardColor.BLACK
            )
        ) if card.labels else ''  # If no labels assigned, don't render them to text.

        # Avoiding message overflow, strip explanations in ()
        list_name = card.lst.name + '('
        list_name = list_name[:list_name.find('(')].strip()

        date = load(
            'trello_board_state_job__card_date',
            date=card.due.strftime("%d.%m"),
        ) if show_due else ''

        members = TrelloBoardStateJob._make_members_string(card, app_context)

        return load(
            'trello_board_state_job__card',
            url=card.url,
            name=card.name,
            labels=labels,
            list_name=list_name,
            members=members,
            date=date,
        )

    @staticmethod
    def _make_members_string(card, app_context: AppContext) -> str:
        curators = TrelloBoardStateJob._get_curators(card, app_context.db_client)
        members_text = ', '.join(utils.retrieve_usernames(card.members, app_context.db_client))
        if curators:
            curators = [
                curator_name for curator_name, telegram in curators
                if telegram and telegram not in members_text
            ]

        return load(
            'trello_board_state_job__card_members',
            members=members_text,
            curators=utils.format_possibly_plural('Куратор', curators),
        )

    @staticmethod
    def _get_curators(card, db_client):
        if not card.members:
            # if no members in a card, should tag curators based on label
            return utils.retrieve_curator_names_by_categories(card.labels, db_client)
        # add curators to the list
        curators = set()
        for member in card.members:
            curator_names = utils.retrieve_curator_names_by_author(member, db_client)
            curators.update(curator_names)
        return curators
