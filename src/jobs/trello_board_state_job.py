import datetime
import logging
from typing import Callable, List

from ..app_context import AppContext
from ..trello.trello_client import TrelloClient
from .utils import pretty_send


logger = logging.getLogger(__name__)


def execute(app_context: AppContext, send: Callable[[str], None]):
    # TODO: make it a decorator
    logger.info('Starting trello_board_state_job...')

    stats_paragraphs = []  # list of paragraph strings
    stats_paragraphs.append('Всем привет! Еженедельная сводка \
о состоянии Trello-доски.\n#доскаживи')

    stats_paragraphs += _retrieve_trello_card_stats(
        trello_client=app_context.trello_client,
        title='Не указан автор в карточке',
        list_ids=(
            app_context.lists_config['in_progress'],
            app_context.lists_config['editor'],
            app_context.lists_config['edited_next_week'],
            app_context.lists_config['edited_sometimes'],
            app_context.lists_config['chief_editor'],
            app_context.lists_config['proofreading'],
            app_context.lists_config['done'],
        ),
        filter_func=lambda card: not card.members,
        show_due=False,
        show_members=False,
    )

    stats_paragraphs += _retrieve_trello_card_stats(
        trello_client=app_context.trello_client,
        title='Не указан срок в карточке',
        list_ids=(app_context.lists_config['in_progress']),
        filter_func=lambda card: not card.due,
        show_due=False
    )

    stats_paragraphs += _retrieve_trello_card_stats(
        trello_client=app_context.trello_client,
        title='Не указан тег рубрики в карточке',
        list_ids=(
            app_context.lists_config['in_progress'],
            app_context.lists_config['editor'],
            app_context.lists_config['edited_next_week'],
            app_context.lists_config['edited_sometimes'],
            app_context.lists_config['chief_editor'],
            app_context.lists_config['proofreading'],
            app_context.lists_config['done'],
        ),
        filter_func=lambda card: not card.labels,
        show_due=False
    )

    all_cards = app_context.trello_client.get_cards()
    members_with_cards = set()
    for card in all_cards:
        members_with_cards = members_with_cards.union(set(card.members))

    # TODO: probably move to another cmd, @ibulgakov has thoughts on that
    # stats_paragraphs += _retrieve_trello_members_stats(
    #     trello_client=app_context.trello_client,
    #     title='Авторы без карточек',
    #     filter_func=lambda member: member.username not in members_with_cards,
    # )

    stats_paragraphs += _retrieve_trello_card_stats(
        trello_client=app_context.trello_client,
        title='Пропущен дедлайн',
        list_ids=(app_context.lists_config['in_progress']),
        filter_func=_is_deadline_missed,
    )

    pretty_send(stats_paragraphs, send)
    logger.info('Finished trello_board_state_job')



def _is_deadline_missed(card) -> bool:
    return card.due is not None and card.due < datetime.datetime.now()


def _retrieve_trello_card_stats(
        trello_client: TrelloClient,
        title: str,
        list_ids: List[str],
        filter_func: Callable,
        show_due=True,
        show_members=True,
) -> List[str]:
    '''
    Returns a list of paragraphs that should always go in a single message.
    '''
    logger.info(f'Started counting: "{title}"')
    cards = list(filter(filter_func, trello_client.get_cards(list_ids)))
    parse_failure_counter = 0

    paragraphs = [f'<b>{title}: {len(cards)}</b>']

    for card in cards:
        if not card:
            parse_failure_counter += 1
            continue
        paragraphs.append(
            _format_card(card, show_due=show_due, show_members=show_members)
        )

    if parse_failure_counter > 0:
        logger.error(f'Unparsed cards encountered: {parse_failure_counter}')
    return paragraphs


def _retrieve_trello_members_stats(
        trello_client: TrelloClient,
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
        paragraphs.append('👤 ' + ', '.join(map(str, sorted(members))))
    return paragraphs


def _format_card(card, show_due=True, show_members=True) -> str:
    # Name and url always present.
    card_text = f'<a href="{card.url}">{card.name}</a>\n'

    # If no labels assigned, don't render them to text.
    if card.labels:
        card_text = f'{card_text}📘 {", ".join(card.labels)} '

    # Avoiding message overflow, strip explanations in ()
    list_name = card.list_name + '('
    list_name = list_name[:list_name.find('(')].strip()
    card_text += f'📍 {list_name} '

    if show_due:
        card_text = f'<b>{card.due.strftime("%d.%m")}</b> — {card_text}'
    if show_members and card.members:
        card_text += f'👤 {", ".join(list(map(str, card.members)))}'
    return card_text.strip()

