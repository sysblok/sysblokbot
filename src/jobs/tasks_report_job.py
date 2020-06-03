import datetime
import logging
from typing import Callable, List

from .base_job import BaseJob
from . import utils
from ..app_context import AppContext
from ..consts import TrelloCardColor, TrelloListAlias
from ..db.db_client import DBClient
from ..trello.trello_client import TrelloClient
from ..sheets.sheets_client import GoogleSheetsClient

logger = logging.getLogger(__name__)


class TasksReportJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None]):
        paragraphs = []  # list of paragraph strings

        # TODO: get list_ and list_id
        list_id = ['']  # there should be list_id
        paragraphs.append(
            f'<b></b>'  # there should be list_.name
        )

        list_cards = app_context.trello_client.get_cards(list_id)
        members_with_cards = set()
        for card in list_cards:
            members_with_cards = members_with_cards.union(set(card.members))

        paragraphs += (TasksReportJob._retrieve_cards_for_paragraph(
            list_cards, app_context
            ))
        utils.pretty_send(paragraphs, send)

    @staticmethod
    def _format_card(card, app_context) -> str:
        # Name and url always present.
        card_text = f'<a href="{card.url}">{card.name}</a>\n'
        return card_text.strip()

    @staticmethod
    def _make_members_string(card, app_context: AppContext) -> str:
        members_text = '👤 '
        # if there are members, should tag both members and their curators
        members_text += ", ".join(
            utils.retrieve_usernames(card.members, app_context.db_client)
        )
        return members_text

    @staticmethod
    def _get_members(cards, app_context):
        members = []
        for card in cards:
            for member in card.members:
                members.append(member)
        return sorted(list(set(members)))

    @staticmethod
    def _get_member_cards(member, cards):
        member_cards = []
        for card in cards:
            if member in card.members:
                member_cards.append(card)
        member_cards = sorted(member_cards, key=lambda card: card.due)
        return member_cards

    @staticmethod
    def _get_cards_without_members(cards):
        cards_without_members = []
        for card in cards:
            if not card.members:
                cards_without_members.append(card)
        cards_without_members = sorted(
            cards_without_members,
            key=lambda card: card.due)
        return cards_without_members

    @staticmethod
    def _make_member_text(member) -> str:
        members_text = '👤 '
        members_text += f'<b>{member.full_name} </b>' + '(@' + member.username + '):'
        return members_text

    @staticmethod
    def _get_deadline(card) -> str:
        date_text = 'До ' + f'{card.due.strftime("%d.%m")}' + ' — '
        return date_text

    @staticmethod
    def _group_cards_by_date(cards, app_context):
        # generates the text of the cards based on availability of the dates
        result = []
        card_text_without_dates = []
        for card in cards:
            if card.due:
                deadline = TasksReportJob._get_deadline(card)
                card_text = TasksReportJob._format_card(card, app_context)
                result.append(deadline + card_text)  # with the date and task
            if not card.due:
                card_text_without_dates.append(
                    TasksReportJob._format_card(card, app_context))
        # cards without dates at the end
        result += card_text_without_dates
        return result

    @staticmethod
    def _retrieve_cards_for_paragraph(cards, app_context):
        paragraphs = ['Всем привет! Собрали задачки на неделю для участников. Проверьте, что все правильно, пожалуйста.']
        members = TasksReportJob._get_members(cards, app_context)
        for member in members:
            member_name = TasksReportJob._make_member_text(member)
            paragraphs.append(member_name)
            member_cards = TasksReportJob._get_member_cards(member, cards)
            cards_text = TasksReportJob._group_cards_by_date(
                member_cards, app_context)
            paragraphs += cards_text

        # cards without members at the end
        cards_without_members = TasksReportJob._get_cards_without_members(cards)
        if cards_without_members:
            paragraphs.append('<b>Разное:</b>')
            cards_without_members_text = TasksReportJob._group_cards_by_date(
                cards_without_members, app_context)
            paragraphs += cards_without_members_text
        return paragraphs
