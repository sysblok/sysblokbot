import datetime
import logging
from typing import Callable, List

from ..app_context import AppContext
from ..consts import TrelloCardColor, TrelloListAlias
from ..db.db_client import DBClient
from ..strings import load
from ..trello.trello_client import TrelloClient
from ..trello.trello_objects import TrelloCard
from .base_job import BaseJob
from . import utils

logger = logging.getLogger(__name__)


class TrelloBoardStateJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None], called_from_handler=False):
        paragraphs = [load('trello_board_state_job__intro')]  # list of paragraph strings
        curator_cards = TrelloBoardStateJob.get_cards_by_curator(app_context)
        for curator, curator_cards in curator_cards.items():
            paragraphs += TrelloBoardStateJob.format_cards_for_curator(
                app_context, curator, curator_cards)
        utils.pretty_send(paragraphs, send)

    @staticmethod
    def get_cards_by_curator(app_context):
        cards = app_context.trello_client.get_cards()
        curator_cards = {}
        for card in cards:
            curators = TrelloBoardStateJob._get_curators(card, app_context.db_client)
            for curator_name, _ in curators:
                if curator_name in curator_cards:
                    curator_cards[curator_name].append(card)
                else:
                    curator_cards[curator_name] = [card]
        return curator_cards

    @staticmethod
    def _is_deadline_missed(card) -> bool:
        return card.due is not None and card.due.date() < datetime.datetime.now().date()

    @staticmethod
    def _make_paragraphs_for_curator_category(
            app_context: AppContext,
            title_alias: str,
            list_aliases: List[TrelloListAlias],
            filter_func: Callable,
            curator_cards: List[TrelloCard],
            show_due=True
    ) -> List[str]:
        '''
        Returns a list of paragraphs for given curator cards, filtered
        '''
        logger.debug(f'Started counting: "{title_alias}"')
        list_ids = app_context.trello_client.get_list_id_from_aliases(list_aliases)
        cards = list(
            filter(
                filter_func,
                [card for card in curator_cards if card.lst.id in list_ids]
            )
        )
        parse_failure_counter = 0

        if not cards:
            return []
        paragraphs = [load('trello_board_state_job__title_and_size', title=load(title_alias), length=len(cards))]

        for card in cards:
            if not card:
                parse_failure_counter += 1
                continue
            paragraphs.append(
                TrelloBoardStateJob._format_card(
                    card,
                    app_context,
                    show_due=show_due
                )
            )

        if parse_failure_counter > 0:
            logger.error(f'Unparsed cards encountered: {parse_failure_counter}')
        return paragraphs

    @staticmethod
    def _format_card(card, app_context, show_due=True) -> str:
        labels = load(
            'trello_board_state_job__card_labels',
            names=", ".join(
                # We filter BLACK cards as this is an auxiliary label
                label.name for label in card.labels
                if label.color != TrelloCardColor.BLACK
            )) if card.labels else ''

        # Avoiding message overflow, strip explanations in ()
        list_name = card.lst.name + '('
        list_name = list_name[:list_name.find('(')].strip()

        # date = load(
        #    'trello_board_state_job__card_date',
        #    date=card.due.strftime("%d.%m"),
        # ) if show_due else ''

        members = load(
            'trello_board_state_job__card_members',
            members=', '.join(utils.retrieve_usernames(
                    card.members,
                    app_context.db_client
                )),
            curators=''
        ) if card.members else ''

        return load(
            'trello_board_state_job__card_2',
            url=card.url,
            name=card.name,
            labels=labels,
            list_name=list_name,
            members=members,
        )

    @staticmethod
    def _get_curators(card, db_client):
        if not card.members:
            # if no members in a card, should tag curators based on label
            curators_by_label = utils.retrieve_curator_names_by_categories(card.labels, db_client)
            if curators_by_label:
                return curators_by_label
        curators = set()
        for member in card.members:
            curator_names = utils.retrieve_curator_names_by_author(member, db_client)
            curators.update(curator_names)
        return curators

    @staticmethod
    def format_cards_for_curator(app_context, curator, curator_cards):
        error_cards_paragraphs = []
        error_cards_paragraphs += TrelloBoardStateJob._make_paragraphs_for_curator_category(
            app_context=app_context,
            title_alias='trello_board_state_job__title_author_missing',
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
            curator_cards=curator_cards,
        )
        error_cards_paragraphs += TrelloBoardStateJob._make_paragraphs_for_curator_category(
            app_context=app_context,
            title_alias='trello_board_state_job__title_due_date_expired',
            list_aliases=(TrelloListAlias.IN_PROGRESS, ),
            filter_func=TrelloBoardStateJob._is_deadline_missed,
            curator_cards=curator_cards,
            show_due=True,
        )
        error_cards_paragraphs += TrelloBoardStateJob._make_paragraphs_for_curator_category(
            app_context=app_context,
            title_alias='trello_board_state_job__title_due_date_missing',
            list_aliases=(TrelloListAlias.IN_PROGRESS, ),
            filter_func=lambda card: not card.due,
            curator_cards=curator_cards,
            show_due=False
        )
        error_cards_paragraphs += TrelloBoardStateJob._make_paragraphs_for_curator_category(
            app_context=app_context,
            title_alias='trello_board_state_job__title_tag_missing',
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
            curator_cards=curator_cards,
            show_due=False
        )
        if error_cards_paragraphs:
            return [f'⭐️ <b>Куратор</b>: {curator}'] + error_cards_paragraphs
        return []
