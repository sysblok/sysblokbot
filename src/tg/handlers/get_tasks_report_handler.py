import logging
from typing import Callable, List

import telegram

from ... import consts
from ...app_context import AppContext
from ...jobs.utils import paragraphs_to_messages
from .utils import manager_only, reply

TASK_NAME = 'get_tasks_report'

logger = logging.getLogger(__name__)


@manager_only
def get_tasks_report(update: telegram.Update, tg_context: telegram.ext.CallbackContext):
    # set initial dialogue data
    tg_context.chat_data[consts.LAST_ACTIONABLE_COMMAND] = TASK_NAME
    tg_context.chat_data[TASK_NAME] = {
        consts.NEXT_ACTION: consts.PlainTextUserAction.ENTER_BOARD_URL.value
    }
    reply("Привет! Пришли, пожалуйста, ссылку на доску в Trello.", update)


def generate_report_messages(list_id: str, introduction: str, add_labels: bool) -> List[str]:
    app_context = AppContext()
    paragraphs = []  # list of paragraph strings

    trello_list = app_context.trello_client.get_list(list_id)
    paragraphs.append(
        f'<b>{trello_list.name}</b>'
    )

    list_cards = app_context.trello_client.get_cards([list_id])
    paragraphs += (_retrieve_cards_for_paragraph(
        list_cards, introduction, add_labels, app_context
    ))
    return paragraphs_to_messages(paragraphs)


def _retrieve_cards_for_paragraph(
        cards,
        introduction: str,
        need_label: bool,
        app_context: AppContext
):
    paragraphs = [introduction]
    members = _get_members(cards)

    for member in members:
        lines = []
        member_name = _make_member_text(member)
        lines.append(member_name)
        member_cards = _get_member_cards(member, cards)
        cards_text = _group_cards_by_date(
            member_cards, need_label, app_context)
        lines += cards_text
        paragraphs.append('\n'.join(lines))

    # cards without members at the end
    cards_without_members = _get_cards_without_members(cards)
    if cards_without_members:
        lines = ['<b>Разное:</b>']
        cards_without_members_text = _group_cards_by_date(
            cards_without_members, need_label, app_context)
        lines += cards_without_members_text
        paragraphs.append('\n'.join(lines))
    return paragraphs


def _format_card(card, need_label: bool) -> str:
    # Name and url always present, labels optional
    labels_text = ''
    if need_label and card.labels:
        labels = [f'"{label.name}"' for label in card.labels]
        labels_text = f'({", ".join(labels)})'
    return f'<a href="{card.url}">{card.name}</a> {labels_text}'.strip()


def _get_members(cards):
    members = set()
    for card in cards:
        for member in card.members:
            members.add(member)
    return sorted(list(members))


def _get_member_cards(member, cards):
    member_cards = []
    for card in cards:
        if member in card.members:
            member_cards.append(card)
    member_cards = sorted(member_cards, key=lambda card: card.due)
    return member_cards


def _get_cards_without_members(cards):
    cards_without_members = []
    for card in cards:
        if not card.members:
            cards_without_members.append(card)
    cards_without_members = sorted(
        cards_without_members,
        key=lambda card: card.due)
    return cards_without_members


def _make_member_text(member) -> str:
    members_text = '👤 '
    members_text += f'<b>{member.full_name} </b>(@{member.username}):'
    return members_text


def _get_deadline(card) -> str:
    date_text = f'До {card.due.strftime("%d.%m")} — '
    return date_text


def _group_cards_by_date(cards, need_label: bool, app_context: AppContext) -> List[str]:
    # generates the text of the cards based on availability of the dates
    result = []
    card_text_without_dates = []
    for card in cards:
        if card.due:
            deadline = _get_deadline(card)
            card_text = _format_card(card, need_label)
            result.append(deadline + card_text)  # with the date and task
        else:
            card_text_without_dates.append(
                _format_card(card, need_label))
    # cards without dates at the end
    result += card_text_without_dates
    return result
