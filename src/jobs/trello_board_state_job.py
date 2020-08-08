from collections import defaultdict
import datetime
import logging
from typing import Callable, List, Tuple

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
        paragraphs = [
            load("trello_board_state_job__intro")
        ]  # list of paragraph strings
        curator_cards = TrelloBoardStateJob.get_cards_by_curator(app_context)
        for curator, curator_cards in curator_cards.items():
            card_paragraphs = []
            curator_cards.sort(key=lambda c: c.due if c.due else datetime.datetime.min)
            for card in curator_cards:
                card_paragraph = TrelloBoardStateJob._make_card_failure_text(card, app_context)
                if card_paragraph:
                    card_paragraphs.append(card_paragraph)
            if card_paragraphs:
                paragraphs.append(f"⭐️ <b>Куратор</b>: {curator}")
                paragraphs += card_paragraphs
        utils.pretty_send(paragraphs, send)

    @staticmethod
    def get_cards_by_curator(app_context: AppContext):
        cards = app_context.trello_client.get_cards()
        curator_cards = defaultdict(list)
        for card in cards:
            curators = TrelloBoardStateJob._get_curators(card, app_context.db_client)
            if not curators:
                # TODO: get main curator from spreadsheet
                curators = [('Илья Булгаков (@bulgak0v)', None)]
            for curator_name, _ in curators:
                curator_cards[curator_name].append(card)

        return curator_cards

    @staticmethod
    def _make_card_failure_text(card: TrelloCard, app_context: AppContext):
        """
        Returns card description with failure reasons, if any.
        If card does not match any of FILTER_TO_FAILURE_REASON, returns None.
        """
        failure_reasons = []
        for filter_func, reason_alias in FILTER_TO_FAILURE_REASON.items():
            is_failed, kwargs = filter_func(card, app_context)
            if is_failed:
                reason = load(reason_alias, **kwargs)
                if reason and len(failure_reasons) > 0:
                    reason = reason[0].lower() + reason[1:]
                failure_reasons.append(reason)
        if not failure_reasons:
            return None

        return TrelloBoardStateJob._format_card(card, failure_reasons, app_context)

    @staticmethod
    def _is_deadline_missed(card: TrelloCard, app_context: AppContext) -> Tuple[bool, dict]:
        list_ids = app_context.trello_client.get_list_id_from_aliases(
            [TrelloListAlias.IN_PROGRESS]
        )
        is_missed = (
            card.lst.id in list_ids and card.due is not None
            and card.due.date() < datetime.datetime.now().date()
        )
        return is_missed, {'date': card.due.strftime("%d.%m")} if is_missed else {}

    @staticmethod
    def _is_due_date_missing(card: TrelloCard, app_context: AppContext) -> Tuple[bool, dict]:
        if card.due:
            return False, {}
        list_ids = app_context.trello_client.get_list_id_from_aliases(
            [TrelloListAlias.IN_PROGRESS]
        )
        return card.lst.id in list_ids, {}

    @staticmethod
    def _is_author_missing(card: TrelloCard, app_context: AppContext) -> Tuple[bool, dict]:
        if card.members:
            return False, {}

        list_aliases = (
            TrelloListAlias.IN_PROGRESS,
            TrelloListAlias.TO_EDITOR,
            TrelloListAlias.EDITED_NEXT_WEEK,
            TrelloListAlias.TO_SEO_EDITOR,
            TrelloListAlias.EDITED_SOMETIMES,
            TrelloListAlias.TO_CHIEF_EDITOR,
            TrelloListAlias.PROOFREADING,
            TrelloListAlias.DONE,
        )
        list_ids = app_context.trello_client.get_list_id_from_aliases(list_aliases)
        return card.lst.id in list_ids, {}

    @staticmethod
    def _is_tag_missing(card: TrelloCard, app_context: AppContext) -> Tuple[bool, dict]:
        if card.labels:
            return False, {}

        list_aliases = (
            TrelloListAlias.IN_PROGRESS,
            TrelloListAlias.TO_EDITOR,
            TrelloListAlias.EDITED_NEXT_WEEK,
            TrelloListAlias.TO_SEO_EDITOR,
            TrelloListAlias.EDITED_SOMETIMES,
            TrelloListAlias.TO_CHIEF_EDITOR,
            TrelloListAlias.PROOFREADING,
            TrelloListAlias.DONE
        )
        list_ids = app_context.trello_client.get_list_id_from_aliases(list_aliases)
        return card.lst.id in list_ids, {}

    @staticmethod
    def _is_doc_missing(card: TrelloCard, app_context: AppContext) -> Tuple[bool, dict]:
        doc_url = app_context.trello_client.get_custom_fields(card.id).google_doc
        if doc_url:
            return False, {}

        list_aliases = (
            TrelloListAlias.TO_EDITOR,
            TrelloListAlias.EDITED_NEXT_WEEK,
            TrelloListAlias.TO_SEO_EDITOR,
            TrelloListAlias.EDITED_SOMETIMES,
            TrelloListAlias.TO_CHIEF_EDITOR,
            TrelloListAlias.PROOFREADING,
            TrelloListAlias.DONE
        )
        list_ids = app_context.trello_client.get_list_id_from_aliases(list_aliases)
        return card.lst.id in list_ids, {}

    @staticmethod
    def _has_no_doc_access(card: TrelloCard, app_context: AppContext) -> Tuple[bool, dict]:
        doc_url = app_context.trello_client.get_custom_fields(card.id).google_doc or ''
        if not doc_url:
            # should be checked in _is_doc_missing
            return False, {}

        list_aliases = (
            TrelloListAlias.TO_EDITOR,
            TrelloListAlias.EDITED_NEXT_WEEK,
            TrelloListAlias.TO_SEO_EDITOR,
            TrelloListAlias.EDITED_SOMETIMES,
            TrelloListAlias.TO_CHIEF_EDITOR,
            TrelloListAlias.PROOFREADING,
            TrelloListAlias.DONE
        )
        list_ids = app_context.trello_client.get_list_id_from_aliases(list_aliases)
        is_open_for_edit = app_context.drive_client.is_open_for_edit(doc_url)
        return not is_open_for_edit and card.lst.id in list_ids, {}

    @staticmethod
    def _format_card(card: TrelloCard, failure_reasons: List[str], app_context: AppContext) -> str:
        failure_reasons_formatted = ', '.join(failure_reasons)
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
            failure_reasons=failure_reasons_formatted,
            url=card.url,
            name=card.name,
            labels=labels,
            list_name=list_name,
            members=members,
        )

    @staticmethod
    def _get_curators(card, db_client):
        curators = set()
        for member in card.members:
            curator_names = utils.retrieve_curator_names_by_author(member, db_client)
            curators.update(curator_names)
        if curators:
            return curators

        # e.g. if no members in a card, should tag curators based on label
        curators_by_label = utils.retrieve_curator_names_by_categories(
            card.labels, db_client
        )
        return curators_by_label


FILTER_TO_FAILURE_REASON = {
    TrelloBoardStateJob._is_author_missing: "trello_board_state_job__title_author_missing",
    TrelloBoardStateJob._is_due_date_missing: "trello_board_state_job__title_due_date_missing",
    TrelloBoardStateJob._is_deadline_missed: "trello_board_state_job__title_due_date_expired",
    TrelloBoardStateJob._is_tag_missing: "trello_board_state_job__title_tag_missing",
    TrelloBoardStateJob._is_doc_missing: "trello_board_state_job__title_no_doc",
    TrelloBoardStateJob._has_no_doc_access: "trello_board_state_job__title_no_doc_access",
}
