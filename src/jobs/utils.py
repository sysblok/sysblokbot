import inspect
import logging
import time
from typing import Callable, List


from ..app_context import AppContext
from ..db.db_client import DBClient
from ..db.db_objects import Curator
from ..sheets.sheets_client import GoogleSheetsClient
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
        return None
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
        return None
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
        card_error_message = (
            f'В карточке <a href="{bad_card.url}">{bad_card.name}</a>'
            f' не заполнено: {", ".join(bad_fields)}'
        )
        error_messages.append(card_error_message)
    paragraphs = [
        'Не могу сгенерировать сводку.',
        '\n'.join(error_messages),
        'Пожалуйста, заполни требуемые поля в карточках и запусти генерацию снова.'
    ]
    return paragraphs
