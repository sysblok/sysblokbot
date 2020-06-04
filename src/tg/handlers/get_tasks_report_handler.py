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


def generate_report_messages(list_id: str, add_labels: bool) -> List[str]:
    app_context = AppContext()
    paragraphs = []  # list of paragraph strings

    trello_list = app_context.trello_client.get_list(list_id)
    paragraphs.append(
        f'<b>{trello_list.name}</b>'
    )

    list_cards = app_context.trello_client.get_cards(list_id)
    members_with_cards = set()
    for card in list_cards:
        members_with_cards = members_with_cards.union(set(card.members))

    paragraphs += (_retrieve_cards_for_paragraph(
        list_cards, app_context
        ))
    return paragraphs_to_messages(paragraphs)


def _format_card(card, app_context) -> str:
    # Name and url always present.
    card_text = f'<a href="{card.url}">{card.name}</a>\n'
    return card_text.strip()


def _get_members(cards):
    members = []
    for card in cards:
        for member in card.members:
            members.append(member)
    return sorted(list(set(members)))


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


def _group_cards_by_date(cards, app_context):
    # generates the text of the cards based on availability of the dates
    result = []
    card_text_without_dates = []
    for card in cards:
        if card.due:
            deadline = _get_deadline(card)
            card_text = _format_card(card, app_context)
            result.append(deadline + card_text)  # with the date and task
        if not card.due:
            card_text_without_dates.append(
                _format_card(card, app_context))
    # cards without dates at the end
    result += card_text_without_dates
    return result


def _retrieve_cards_for_paragraph(cards, app_context):
    paragraphs = ['Всем привет! Собрали задачки на неделю для участников.'
                    'Проверьте, что все правильно, пожалуйста.']
    members = _get_members(cards)
    for member in members:
        member_name = _make_member_text(member)
        paragraphs.append(member_name)
        member_cards = _get_member_cards(member, cards)
        cards_text = _group_cards_by_date(
            member_cards, app_context)
        paragraphs += cards_text

    # cards without members at the end
    cards_without_members = _get_cards_without_members(cards)
    if cards_without_members:
        paragraphs.append('<b>Разное:</b>')
        cards_without_members_text = _group_cards_by_date(
            cards_without_members, app_context)
        paragraphs += cards_without_members_text
    return paragraphs
