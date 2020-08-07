import inspect
import logging
import time
import datetime
from typing import Callable, List

import telegram

from ..app_context import AppContext
from ..db.db_client import DBClient
from ..db.db_objects import Curator, TrelloAnalytics
from ..sheets.sheets_client import GoogleSheetsClient
from ..drive.drive_client import GoogleDriveClient
from ..strings import load
from ..trello.trello_objects import TrelloMember
from .. import jobs

logger = logging.getLogger(__name__)

# Delay to ensure messages come in right order.
MESSAGE_DELAY_SEC = 0.1


def retrieve_username(
        trello_member: TrelloMember,
        db_client: DBClient
):
    """
    Where possible and defined, choose @tg_id over trello_id.
    Note: currently requires a request to GSheets API.
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
    Tries to find a curator for trello member.
    Returns: "John Smith (@jsmith_tg)" where possible, otherwise "John Smith".
    If trello member or curator could not be found in Authors sheet, returns None
    Note: requires a request to GoogleSheets API.
    """
    try:
        curators = db_client.find_curators_by_author_trello('@' + trello_member.username)
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
    return f'{name}{"ы" if len(values) > 1 else ""}: {", ".join(values)}. '


def retrieve_statistc(db_client: DBClient):
    try:
        statistics = db_client.find_the_latest_statistics()
        return sorted(
            [_make_statistic_string(statistic) for statistic in statistics],
            key=lambda k: k['date']
            )
    except Exception as e:
        logger.error(f'Failed to retrieve statistic')


def add_statistic(db_client: DBClient, data):
    try:
        db_client.add_item_to_statistics_table(data)
    except Exception as e:
        logger.error(f'Failed to add statistic item')


def _make_statistic_string(statistic: TrelloAnalytics):
    """
    Returns the dictionary with statistics data
    """
    if statistic.date and statistic.topic_suggestion and statistic.topic_ready \
            and statistic.in_progress and statistic.expect_this_week and statistic.editors_check:
        return {
            'date': datetime.datetime.strptime(statistic.date, '%Y-%m-%d'),
            'topic_suggestion': statistic.topic_suggestion,
            'topic_ready': statistic.topic_ready,
            'in_progress': statistic.in_progress,
            'expect_this_week': statistic.expect_this_week,
            'editors_check': statistic.editors_check
        }
    else:
        return None

def get_no_access_marker(file_url: str, drive_client: GoogleDriveClient) -> str:
    """
    Returns either marker of Google Doc edit permissions
    or empty string if not a Google Doc or not open for edit to everyone.
    """
    if not drive_client.is_open_for_edit(file_url):
        return load('common__no_file_access') + ' '
    return ''