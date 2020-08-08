import datetime
import logging
from typing import Callable, List

from ..app_context import AppContext
from ..consts import TrelloCardColor, TrelloListAlias
from ..strings import load
from ..trello.trello_client import TrelloClient
from ..trello.trello_objects import TrelloCard
from .base_job import BaseJob
from . import utils

logger = logging.getLogger(__name__)


class TrelloBoardStateJob(BaseJob):
    @staticmethod
    def _execute(
        app_context: AppContext, send: Callable[[str], None], called_from_handler=False
    ):
        FILTER_TO_FAILURE_REASON = {
            TrelloBoardStateJob._is_author_missing_due_date_expire: [
                "trello_board_state_job__title_author_missing",
                "trello_board_state_job__title_due_date_expired",
            ],
            TrelloBoardStateJob._is_author_missing: [
                "trello_board_state_job__title_author_missing"
            ],
            TrelloBoardStateJob._is_deadline_missed: [
                "trello_board_state_job__title_due_date_missing"
            ],
            TrelloBoardStateJob._is_due_date_expire: [
                "trello_board_state_job__title_due_date_expired"
            ],
            TrelloBoardStateJob._is_tag_missing: [
                "trello_board_state_job__title_tag_missing"
            ],
        }
        paragraphs = [
            load("trello_board_state_job__intro")
        ]  # list of paragraph strings
        curator_cards = TrelloBoardStateJob.get_cards_by_curator(app_context)
        for curator, curator_cards in curator_cards.items():
            paragraphs += [f"⭐️ <b>Куратор</b>: {curator}"]
            for filter_func, reason_alias in FILTER_TO_FAILURE_REASON.items():
                paragraphs += TrelloBoardStateJob._make_paragraphs_for_curator_category(
                    app_context, filter_func, reason_alias, curator_cards
                )
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
    def get_card_title(cards, titles_aliases):
        titles = (
            ", ".join(
                load(title_alias, title=load(title_alias), length=len(cards))
                for title_alias in titles_aliases
            )
            .lower()
            .capitalize()
        )
        return (  # if not date else f'<b>{titles}: {date}</b>'
            f"<b>{titles}: {len(cards)}</b>"
        )

    @staticmethod
    def _make_paragraphs_for_curator_category(
        app_context, filter_func, reason_alias, curator_cards, show_due=True
    ):
        """
        Returns a list of paragraphs for given curator cards, filtered
        """
        cards = list(filter(lambda card: filter_func(app_context, card), curator_cards))
        parse_failure_counter = 0
        if not cards:
            return []
        paragraphs = [TrelloBoardStateJob.get_card_title(cards, reason_alias)]
        for card in cards:
            if not card:
                parse_failure_counter += 1
                continue
            paragraphs.append(
                TrelloBoardStateJob._format_card(card, app_context, show_due=False)
            )
        if parse_failure_counter > 0:
            logger.error(f"Unparsed cards encountered: {parse_failure_counter}")
        return paragraphs

    @staticmethod
    def _is_deadline_missed(app_context, card) -> bool:
        return card.due is not None and card.due.date() < datetime.datetime.now().date()

    @staticmethod
    def _is_due_date_missing(app_context, card) -> bool:
        list_aliases = (TrelloListAlias.IN_PROGRESS,)
        list_ids = app_context.trello_client.get_list_id_from_aliases(list_aliases)
        return card.due is None and card.lst.id in list_ids

    @staticmethod
    def _is_author_missing(app_context, card) -> bool:
        list_aliases = (
            TrelloListAlias.IN_PROGRESS,
            TrelloListAlias.TO_EDITOR,
            TrelloListAlias.EDITED_NEXT_WEEK,
            TrelloListAlias.EDITED_SOMETIMES,
            TrelloListAlias.TO_CHIEF_EDITOR,
            TrelloListAlias.PROOFREADING,
            TrelloListAlias.DONE,
        )
        list_ids = app_context.trello_client.get_list_id_from_aliases(list_aliases)

        return card.members is None and card.lst.id in list_ids

    @staticmethod
    def _is_due_date_expire(app_context, card) -> bool:
        list_aliases = (TrelloListAlias.IN_PROGRESS,)
        list_ids = app_context.trello_client.get_list_id_from_aliases(list_aliases)
        return (
            TrelloBoardStateJob._is_deadline_missed(app_context, card)
            and card.lst.id in list_ids
        )

    @staticmethod
    def _is_tag_missing(app_context, card) -> bool:
        list_aliases = (
            (
                TrelloListAlias.IN_PROGRESS,
                TrelloListAlias.TO_EDITOR,
                TrelloListAlias.EDITED_NEXT_WEEK,
                TrelloListAlias.EDITED_SOMETIMES,
                TrelloListAlias.TO_CHIEF_EDITOR,
                TrelloListAlias.PROOFREADING,
                TrelloListAlias.DONE,
            ),
        )
        list_ids = app_context.trello_client.get_list_id_from_aliases(list_aliases)
        return card.labels is None and card.lst.id in list_ids

    @staticmethod
    def _is_author_missing_due_date_expire(app_context, card) -> TrelloCard:
        list_aliases = (TrelloListAlias.IN_PROGRESS,)
        list_ids = app_context.trello_client.get_list_id_from_aliases(list_aliases)
        if (
            TrelloBoardStateJob._is_author_missing(app_context, card)
            and TrelloBoardStateJob._is_deadline_missed(app_context, card)
            and card.lst.id in list_ids
        ):
            return card

    @staticmethod
    def _format_card(card, app_context, show_due=True) -> str:
        labels = (
            load(
                "trello_board_state_job__card_labels",
                names=", ".join(
                    # We filter BLACK cards as this is an auxiliary label
                    label.name
                    for label in card.labels
                    if label.color != TrelloCardColor.BLACK
                ),
            )
            if card.labels
            else ""
        )

        # Avoiding message overflow, strip explanations in ()
        list_name = card.lst.name + "("
        list_name = list_name[: list_name.find("(")].strip()

        date = (
            load("trello_board_state_job__card_date", date=card.due.strftime("%d.%m"),)
            if card.due and show_due
            else ""
        )

        members = (
            load(
                "trello_board_state_job__card_members",
                members=", ".join(
                    utils.retrieve_usernames(card.members, app_context.db_client)
                ),
                curators="",
            )
            if card.members
            else ""
        )

        return load(
            "trello_board_state_job__card_2",
            url=card.url,
            name=card.name,
            labels=labels,
            list_name=list_name,
            members=members,
            date=date,
        )

    @staticmethod
    def _get_curators(card, db_client):
        if not card.members:
            # if no members in a card, should tag curators based on label
            curators_by_label = utils.retrieve_curator_names_by_categories(
                card.labels, db_client
            )
            if curators_by_label:
                return curators_by_label
        curators = set()
        for member in card.members:
            curator_names = utils.retrieve_curator_names_by_author(member, db_client)
            curators.update(curator_names)
        return curators
