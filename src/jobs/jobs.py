"""
A module for business logic-containing regular jobs.
Jobs should use corresponding client objects to interact with
Trello, Spreadsheets or Telegram API.
Jobs can be ran from scheduler or from anywhere else for a one-off action.
"""

import datetime
import logging
import time
from typing import Callable, List

from ..app_context import AppContext
from ..trello.trello_client import TrelloClient


logger = logging.getLogger(__name__)

# Delay to ensure messages come in right order.
MESSAGE_DELAY_SEC = 0.1


def sample_job(app_context: AppContext, send: Callable[[str], None]):
    # Logic here could include retrieving data from trello/sheets
    # and sending a notification to corresponding user.
    # app_context contain all necessary clients inside.
    print("I am a job and I'm done")


def manager_stats_job(app_context: AppContext, send: Callable[[str], None]):
    # TODO: make it a decorator
    logger.info('Starting manager_stats_job...')

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

    for i, message in enumerate(_paragraphs_to_messages(stats_paragraphs)):
        if i > 0:
            time.sleep(MESSAGE_DELAY_SEC)
        send(message)
    logger.info('Finished manager_stats_job')


def weekly_publish_digest_job(app_context: AppContext, sender: TelegramSender):

    logger.info('Starting weekly_publish_digest_job...')

    digest_paragraphs = []  # list of paragraph strings
    digest_paragraphs.append('Всем привет!')

    digest_paragraphs += _retrieve_cards_for_digest(
        trello_client=app_context.trello_client,
        title='Публикуем на неделе',
        list_ids=(app_context.lists_config['proofreading'], app_context.lists_config['done']),
        show_due=True,
    )


    for i, message in enumerate(_paragraphs_to_messages(digest_paragraphs)):
        if i > 0:
            time.sleep(MESSAGE_DELAY_SEC)
        sender.send_to_managers(message)
    logger.info('Finished weekly_publish_digest_job')


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


def _retrieve_cards_for_digest(
        trello_client: TrelloClient,
        title: str,
        list_ids: List[str],
        filter_func: Callable=lambda _: True,
        show_due=True,
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
        card_fields = trello_client.get_card_custom_fields(card.id)
        authors, editors, illustrators = card_fields
        paragraphs.append(
            _format_card_for_digest(card, authors, editors, illustrators, show_due=show_due)
        )

    if parse_failure_counter > 0:
        logger.error(f'Unparsed cards encountered: {parse_failure_counter}')
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


def _format_card_for_digest(
        card, authors, editors, illustrators, show_due=True
) -> str:
    # Name and url always present.
    card_text = f'<a href="{card.url}">{card.name}</a>\n'

    card_text += f'Авторы: {authors} '
    card_text += f'Редакторы: {editors} '
    card_text += f'Иллюстраторы: {illustrators} '

    if show_due:
        card_text = f'<b>{card.due.strftime("%d.%m")}</b> — {card_text}'
    return card_text.strip()


def _paragraphs_to_messages(
        paragraphs: List[str],
        char_limit=4096,
        delimiter='\n\n',
) -> List[str]:
    '''
    Makes as few message texts as possible from given paragraph list.
    '''
    if not paragraphs:
        logger.warning('No paragraphs to process, exiting')
        return

    delimiter_len = len(delimiter)
    messages = []
    message_paragraphs = []
    char_counter = char_limit  # so that we start a new message immediately

    for paragraph in paragraphs:
        if len(paragraph) + char_counter + delimiter_len < char_limit:
            message_paragraphs.append(paragraph)
            char_counter += len(paragraph) + delimiter_len
        else:
            # Overflow, starting a new message
            messages.append(delimiter.join(message_paragraphs))

            assert len(paragraph) < char_limit  # should not fire
            message_paragraphs = [paragraph]
            char_counter = len(paragraph)
    messages.append(delimiter.join(message_paragraphs))

    # first message is empty by design.
    assert messages[0] == ''
    return messages[1:]
