import datetime
import inspect
import logging
import time
from collections import defaultdict
from typing import Callable, List

import telegram

from .. import jobs
from ..app_context import AppContext
from ..consts import TrelloCardColor
from ..db.db_client import DBClient
from ..db.db_objects import Curator, TrelloAnalytics
from ..drive.drive_client import GoogleDriveClient
from ..strings import load
from ..trello.trello_objects import TrelloMember

logger = logging.getLogger(__name__)

# Delay to ensure messages come in right order.
MESSAGE_DELAY_SEC = 0.1


def retrieve_username(
        trello_member: TrelloMember,
        db_client: DBClient
):
    """
    Where possible and defined, choose @tg_id over trello_id.
    Returns: "John Smith (@jsmith_tg)" if telegram login found,
    "John Smith (jsmith_trello)" otherwise.
    """
    trello_id = trello_member.username
    tg_id = None

    try:
        tg_id = db_client.find_author_telegram_by_trello(
            '@' + trello_id
        )
    except Exception as e:
        logger.error(f'Failed to retrieve tg id for "{trello_id}": {e}')

    if tg_id and tg_id.startswith('@'):  # otherwise can be phone number
        return f'{trello_member.full_name} ({tg_id})'
    return f'{trello_member.full_name} ({trello_id})'


def retrieve_usernames(
        trello_members: List[TrelloMember],
        db_client: DBClient
) -> List[str]:
    """
    Process an iterable of trello members to list of formatted strings.
    """
    return [
        retrieve_username(member, db_client)
        for member in trello_members
    ]


def retrieve_curator_names_by_author(
        trello_member: TrelloMember,
        db_client: DBClient
) -> List[str]:
    """
    Tries to find a curator for trello member. Returns nothing if user is curator.
    Returns: "John Smith (@jsmith_tg)" where possible, otherwise "John Smith".
    If trello member or curator could not be found in Authors sheet, returns None
    """
    trello_id = '@' + trello_member.username
    try:
        curator = db_client.get_curator_by_trello_id(trello_id)
        if curator:
            curators = [curator]
        else:
            curators = db_client.find_curators_by_author_trello(trello_id)
    except Exception as e:
        logger.error(f'Could not retrieve curators by author: {e}')
        return
    if not curators:
        return []
    return [_make_curator_string(curator) for curator in curators]


def retrieve_curator_names_by_categories(labels: List[str], db_client: DBClient):
    """
    To be used when there is no known authors.
    Category is a trello label (e.g. NLP)
    """
    curators = set()
    try:
        for label in labels:
            curators = curators.union(
                set(db_client.find_curators_by_trello_label(label.name))
            )
    except Exception as e:
        logger.error(f'Could not retrieve curators by category: {e}')
        return
    if not curators:
        return []
    return [_make_curator_string(curator) for curator in curators]


def _make_curator_string(curator: Curator):
    """
    Returns: (pretty_curator_string, tg_login_or_None)
    """
    if curator.name:
        if curator.telegram:
            return f'{curator.name} ({curator.telegram})', curator.telegram
        return curator.name, None
    return curator.telegram, curator.telegram


def pretty_send(
        paragraphs: List[str],
        send: Callable[[str], None]
) -> str:
    '''
    Send a bunch of paragraphs grouped into messages with adequate delays.
    Return the whole message for testing purposes.
    '''
    messages = paragraphs_to_messages(paragraphs)
    for i, message in enumerate(messages):
        if i > 0:
            time.sleep(MESSAGE_DELAY_SEC)
        send(message)
    return '\n'.join(messages)


def paragraphs_to_messages(
        paragraphs: List[str],
        char_limit=telegram.constants.MAX_MESSAGE_LENGTH,
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


def get_job_runnable(job_id: str):
    """
    Finds a job class inside a module and returns its execute method.
    Adds readable name to execute method for introspection.
    """
    try:
        job_module = getattr(jobs, job_id)
    except Exception as e:
        logger.error(f'Job "{job_id}" not found: {e}')
        return

    for name, obj in inspect.getmembers(job_module):
        if (inspect.isclass(obj) and
                issubclass(obj, jobs.base_job.BaseJob) and
                obj is not jobs.base_job.BaseJob):
            execute_job = obj.execute
            execute_job.__func__.__name__ = name
            return execute_job
    logger.error(f'Could not find job runnable for {job_module}')


def format_errors(errors: dict):
    # probably will move it to BaseJob
    error_messages = []
    for bad_card, bad_fields in errors.items():
        card_error_message = load(
            'jobs__utils__format_errors_error',
            url=bad_card.url,
            name=bad_card.name,
            fields=', '.join(bad_fields),
        )
        error_messages.append(card_error_message)
    paragraphs = [
        load('jobs__utils__format_errors_intro'),
        '\n'.join(error_messages),
        load('jobs__utils__format_errors_outro'),
    ]
    return paragraphs


def format_possibly_plural(name: str, values: List[str]) -> str:
    if len(values) == 0:
        return ''
    # yeah that's a bit sexist
    return load(
        'common__named_list',
        name=name,
        plural="ы" if len(values) > 1 else "",
        items=", ".join(values)
    )


def format_labels(values: List[str]) -> str:
    if len(values) == 0:
        return ''
    return '[' + ']['.join(values) + ']'


def retrieve_last_trello_analytics(db_client: DBClient) -> dict:
    try:
        return db_client.get_latest_trello_analytics()
    except Exception as e:
        logger.error(f'Failed to retrieve statistic: {e}')


def retrieve_last_trello_analytics_date(db_client: DBClient) -> datetime.datetime:
    try:
        return datetime.datetime.strptime(
            db_client.get_latest_trello_analytics().date,
            '%Y-%m-%d'
        )
    except Exception as e:
        logger.error(f'Failed to retrieve latest statistic date: {e}')


def get_no_access_marker(file_url: str, drive_client: GoogleDriveClient) -> str:
    """
    Returns either marker of Google Doc edit permissions
    or empty string if not a Google Doc or not open for edit to everyone.
    """
    if not drive_client.is_open_for_edit(file_url):
        return load('common__no_file_access') + ' '
    return ''


def check_trello_card(
    card,
    errors,
    is_bad_title=False,
    is_bad_google_doc=False,
    is_bad_authors=False,
    is_bad_editors=False,
    is_bad_illustrators=False,
    is_bad_cover=False,
    is_bad_due_date=False,
    is_bad_label_names=False,
    strict_archive_rules=False,
):
    label_names = [
        label.name for label in card.labels if label.color != TrelloCardColor.BLACK
    ]

    is_archive_card = load('common_trello_label__archive') in label_names
    if is_archive_card and not strict_archive_rules:
        return True

    this_card_bad_fields = []
    if is_bad_title:
        this_card_bad_fields.append(load('trello_custom_field__post_title').lower())
    if is_bad_google_doc:
        this_card_bad_fields.append(load('trello_custom_field__google_doc').lower())
    if is_bad_authors:
        this_card_bad_fields.append(load('trello_custom_field__author').lower())
    if is_bad_editors:
        this_card_bad_fields.append(load('trello_custom_field__editor').lower())
    if is_bad_cover:
        this_card_bad_fields.append(load('trello_custom_field__cover').lower())
    if is_bad_illustrators:
        this_card_bad_fields.append(load('trello_custom_field__illustrator').lower())
    if is_bad_due_date:
        this_card_bad_fields.append(load('trello_custom_field__due_date').lower())
    if is_bad_label_names:
        this_card_bad_fields.append(load('trello_custom_field__rubric').lower())

    if len(this_card_bad_fields) > 0:
        logger.info(
            f'Trello card is unsuitable for publication: {card.url} {this_card_bad_fields}'
        )
        errors[card] = this_card_bad_fields
        return False
    return True


def get_cards_by_curator(app_context: AppContext):
    cards = app_context.trello_client.get_cards()
    curator_cards = defaultdict(list)
    for card in cards:
        curators = get_curators_by_card(card, app_context.db_client)
        if not curators:
            # TODO: get main curator from spreadsheet
            curators = [('Илья Булгаков (@bulgak0v)', '@bulgak0v')]
        for curator in curators:
            curator_cards[curator].append(card)

    return curator_cards


def get_curators_by_card(card, db_client):
    curators = set()
    for member in card.members:
        curator_names = retrieve_curator_names_by_author(member, db_client)
        curators.update(curator_names)
    if curators:
        return curators

    # e.g. if no members in a card, should tag curators based on label
    curators_by_label = retrieve_curator_names_by_categories(
        card.labels, db_client
    )
    return curators_by_label
