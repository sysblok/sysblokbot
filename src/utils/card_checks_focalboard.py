import datetime
from typing import Tuple

from ..app_context import AppContext
from ..consts import TrelloListAlias
from ..strings import load
from ..trello.trello_objects import TrelloCard


def make_card_failure_reasons(card: TrelloCard, app_context: AppContext):
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
    return failure_reasons


def is_deadline_missed(card: TrelloCard, app_context: AppContext) -> Tuple[bool, dict]:
    list_ids = app_context.focalboard_client.get_list_id_from_aliases(
        [TrelloListAlias.IN_PROGRESS]
    )
    is_missed = (
        card.lst.id in list_ids
        and card.due is not None
        and card.due.date() < datetime.datetime.now().date()
    )
    return is_missed, {"date": card.due.strftime("%d.%m")} if is_missed else {}


def is_due_date_missing(card: TrelloCard, app_context: AppContext) -> Tuple[bool, dict]:
    if card.due:
        return False, {}
    list_ids = app_context.focalboard_client.get_list_id_from_aliases(
        [TrelloListAlias.IN_PROGRESS]
    )
    return card.lst.id in list_ids, {}


def is_author_missing(card: TrelloCard, app_context: AppContext) -> Tuple[bool, dict]:
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
    list_ids = app_context.focalboard_client.get_list_id_from_aliases(list_aliases)
    return card.lst.id in list_ids, {}


def is_tag_missing(card: TrelloCard, app_context: AppContext) -> Tuple[bool, dict]:
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
        TrelloListAlias.DONE,
    )
    list_ids = app_context.focalboard_client.get_list_id_from_aliases(list_aliases)
    return card.lst.id in list_ids, {}


def is_doc_missing(card: TrelloCard, app_context: AppContext) -> Tuple[bool, dict]:
    list_aliases = (
        TrelloListAlias.TO_EDITOR,
        TrelloListAlias.EDITED_NEXT_WEEK,
        TrelloListAlias.TO_SEO_EDITOR,
        TrelloListAlias.EDITED_SOMETIMES,
        TrelloListAlias.TO_CHIEF_EDITOR,
        TrelloListAlias.PROOFREADING,
        TrelloListAlias.DONE,
    )
    list_ids = app_context.focalboard_client.get_list_id_from_aliases(list_aliases)
    if card.lst.id not in list_ids:
        return False, {}

    doc_url = app_context.focalboard_client.get_custom_fields(card.id).google_doc
    return not doc_url, {}


def has_no_doc_access(card: TrelloCard, app_context: AppContext) -> Tuple[bool, dict]:
    list_aliases = (
        TrelloListAlias.TO_EDITOR,
        TrelloListAlias.EDITED_NEXT_WEEK,
        TrelloListAlias.TO_SEO_EDITOR,
        TrelloListAlias.EDITED_SOMETIMES,
        TrelloListAlias.TO_CHIEF_EDITOR,
        TrelloListAlias.PROOFREADING,
        TrelloListAlias.DONE,
    )
    list_ids = app_context.focalboard_client.get_list_id_from_aliases(list_aliases)
    if card.lst.id not in list_ids:
        return False, {}

    doc_url = app_context.focalboard_client.get_custom_fields(card.id).google_doc
    if not doc_url:
        # should be handled by is_doc_missing
        return False, {}

    is_open_for_edit = app_context.drive_client.is_open_for_edit(doc_url)
    return not is_open_for_edit, {}


FILTER_TO_FAILURE_REASON = {
    is_author_missing: "trello_board_state_job__title_author_missing",
    is_due_date_missing: "trello_board_state_job__title_due_date_missing",
    is_deadline_missed: "trello_board_state_job__title_due_date_expired",
    is_tag_missing: "trello_board_state_job__title_tag_missing",
    is_doc_missing: "trello_board_state_job__title_no_doc",
    has_no_doc_access: "trello_board_state_job__title_no_doc_access",
}
