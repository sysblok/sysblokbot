import logging
import time
from typing import Callable, List


from ..app_context import AppContext
from ..sheets.sheets_client import GoogleSheetsClient
from ..trello.trello_objects import TrelloMember


logger = logging.getLogger(__name__)

# Delay to ensure messages come in right order.
MESSAGE_DELAY_SEC = 0.1

# TODO: remove after we move to DB
# Per-session cache
tg_login_cache = {}


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
            ).strip()
        except Exception as e:
            logger.error(f'Failed to retrieve tg id for "{trello_id}": {e}')
        if tg_id:
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
    def wrapper(app_context: AppContext, send: Callable[[str], None]):
        # it works!
        module = func.__code__.co_filename.split('/')[-1]
        logger.info(f'Starting {module}...')
        func(app_context, send)
        logger.info(f'Finished {module}')
    return wrapper
