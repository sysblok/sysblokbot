import inspect
import logging
import time
from typing import Callable, List


from ..app_context import AppContext
from ..sheets.sheets_client import GoogleSheetsClient
from ..trello.trello_objects import TrelloMember
from .. import jobs


logger = logging.getLogger(__name__)

# Delay to ensure messages come in right order.
MESSAGE_DELAY_SEC = 0.1

# TODO: remove after we move to DB
# Per-session caches
tg_login_cache = {}
curator_name_cache = {}


def retrieve_username(
        trello_member: TrelloMember,
        sheets_client: GoogleSheetsClient
):
    """
    Where possible and defined, choose @tg_id over trello_id.
    Note: currently requires a request to GSheets API.
    Returns: "John Smith (@jsmith_tg)" if telegram login found,
    "John Smith (jsmith_trello)" otherwise.
    """
    global tg_login_cache
    trello_id = trello_member.username
    tg_id = None
    if trello_id in tg_login_cache:
        tg_id = tg_login_cache[trello_id]
    else:
        try:
            tg_id = sheets_client.find_telegram_id_by_trello_id(
                '@' + trello_id
            )
        except Exception as e:
            logger.error(f'Failed to retrieve tg id for "{trello_id}": {e}')
        if tg_id:
            tg_id = tg_id.strip()
            tg_login_cache[trello_id] = tg_id

    if tg_id and tg_id.startswith('@'):  # otherwise can be phone number
        return f'{trello_member.full_name} ({tg_id})'
    return f'{trello_member.full_name} ({trello_id})'


def retrieve_usernames(
        trello_members: List[TrelloMember],
        sheets_client: GoogleSheetsClient
) -> List[str]:
    """
    Process an iterable of trello members to list of formatted strings.
    """
    return [
        retrieve_username(member, sheets_client)
        for member in trello_members
    ]


def retrieve_curator_names(
        trello_member: TrelloMember,
        sheets_client: GoogleSheetsClient
) -> List[str]:
    """
    Tries to find a curator for trello member.
    Returns: "John Smith (@jsmith_tg)" where possible, otherwise "John Smith".
    If trello member or curator could not be found in Authors sheet, returns None
    Note: requires a request to GoogleSheets API.
    """
    global curator_name_cache
    curators = None
    if trello_member.username in curator_name_cache:
        curators = curator_name_cache[trello_member.username]
    else:
        try:
            curators = sheets_client.find_author_curators('trello', '@' + trello_member.username)
            if curators:
                curator_name_cache[trello_member.username] = curators
        except Exception as e:
            logger.error(f'Could not retrieve curator: {e}')
            return
    if not curators:
        return None
    return [_make_curator_string(curator) for curator in curators]


def _make_curator_string(curator: dict):
    """
    Returns: (pretty_curator_string, tg_login_or_None)
    """
    # TODO: make this SheetsCurator class
    name = curator.get('name')
    telegram = curator.get('telegram')
    if name:
        name = name.strip()
        if telegram:
            telegram = telegram.strip()
            return f'{name} ({telegram})', telegram
        return name, None
    return telegram, telegram


def pretty_send(
        paragraphs: List[str],
        send: Callable[[str], None]
):
    '''
    Send a bunch of paragraphs grouped into messages with adequate delays
    '''
    for i, message in enumerate(_paragraphs_to_messages(paragraphs)):
        if i > 0:
            time.sleep(MESSAGE_DELAY_SEC)
        send(message)


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


def job_log_start_stop(func):
    """
    Decorator that logs start and end events of each job.
    """
    def wrapper(*args, **kwargs):
        # it works!
        module = func.__code__.co_filename.split('/')[-1]
        logger.info(f'Starting {module}...')
        func(*args, **kwargs)
        logger.info(f'Finished {module}')
    return wrapper


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
        if inspect.isclass(obj) and issubclass(obj, jobs.base_job.BaseJob) and obj is not jobs.base_job.BaseJob:
            execute_job = obj.execute
            execute_job.__func__.__name__ = name
            return execute_job
    logger.error(f'Could not find job runnable for {job_module}')
