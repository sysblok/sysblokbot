import datetime
import logging
from typing import Callable, List

from .base_job import BaseJob
from ..app_context import AppContext
from ..consts import TrelloCardColor, TrelloListAlias
from ..db.db_client import DBClient
from ..trello.trello_client import TrelloClient
from ..sheets.sheets_client import GoogleSheetsClient
from .utils import pretty_send, retrieve_usernames, retrieve_curator_names

logger = logging.getLogger(__name__)


class TrelloBoardStateJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None]):
        paragraphs = []  # list of paragraph strings
        paragraphs.append(
            'Всем привет! Еженедельная сводка о состоянии Trello-доски.\n#доскаживи'
        )

        paragraphs += TrelloBoardStateJob._retrieve_cards_for_paragraph(
            app_context=app_context,
            title='Не указан автор в карточке',
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
            title='Не указан срок в карточке',
            list_aliases=(TrelloListAlias.IN_PROGRESS, ),
            filter_func=lambda card: not card.due,
            show_due=False
        )

        paragraphs += TrelloBoardStateJob._retrieve_cards_for_paragraph(
            app_context=app_context,
            title='Не указан тег рубрики в карточке',
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

        # TODO: probably move to another cmd, @ibulgakov has thoughts on that
        # paragraphs += _retrieve_trello_members_stats(
        #     trello_client=app_context.trello_client,
        #     title='Авторы без карточек',
        #     filter_func=lambda member: member.username not in members_with_cards,
        # )

        paragraphs += TrelloBoardStateJob._retrieve_cards_for_paragraph(
            app_context=app_context,
            title='Пропущен дедлайн',
            list_aliases=(TrelloListAlias.IN_PROGRESS, ),
            filter_func=TrelloBoardStateJob._is_deadline_missed,
        )

        pretty_send(paragraphs, send)

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
        list_ids = [app_context.trello_client.lists_config[alias] for alias in list_aliases]
        cards = list(filter(filter_func, app_context.trello_client.get_cards(list_ids)))
        parse_failure_counter = 0

        paragraphs = [f'<b>{title}: {len(cards)}</b>']

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
    def _retrieve_trello_members_stats(
            trello_client: TrelloClient,
            db_client: DBClient,
            title: str,
            filter_func: Callable,
    ) -> List[str]:
        '''
        Returns a list of paragraphs that should always go in a single message.
        '''
        logger.info(f'Started counting: "{title}"')
        members = list(filter(filter_func, trello_client.get_members()))
        paragraphs = [f'<b>{title}: {len(members)}</b>']
        if members:
            paragraphs.append('👤 ' + ", ".join(
                retrieve_usernames(sorted(members), db_client)
            ))
        return paragraphs

    @staticmethod
    def _format_card(card, app_context, show_due=True, show_members=True) -> str:
        # Name and url always present.
        card_text = f'<a href="{card.url}">{card.name}</a>\n'

        # If no labels assigned, don't render them to text.
        if card.labels:
            # We filter BLACK cards as this is an auxiliary label
            label_names = [
                label.name for label in card.labels
                if label.color != TrelloCardColor.BLACK
            ]
            card_text = f'{card_text}📘 {", ".join(label_names)} '

        # Avoiding message overflow, strip explanations in ()
        list_name = card.lst.name + '('
        list_name = list_name[:list_name.find('(')].strip()
        card_text += f'📍 {list_name} '

        if show_due:
            card_text = f'<b>{card.due.strftime("%d.%m")}</b> — {card_text}'
        if show_members and card.members:
            members_text = (
                f'👤 '
                f'{", ".join(retrieve_usernames(card.members, app_context.db_client))}'
            )
            # add curators to the list
            # TODO: make it more readable!
            curators = set()
            for member in card.members:
                curator_names = retrieve_curator_names(member, app_context.sheets_client)
                if not curator_names:
                    continue
                for curator_text, telegram in curator_names:
                    # curator should not duplicate author or other curator
                    if (
                        curator_text and curator_text not in curators and
                            telegram and telegram not in members_text
                    ):
                        curators.add(curator_text)
            card_text += members_text
            if curators:
                curators_text = ' <b>Куратор:</b> ' + ', '.join(curators)
                card_text += curators_text
        return card_text.strip()
