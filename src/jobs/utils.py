"""
A module for business logic-containing regular jobs.
Jobs should use corresponding client objects to interact with
Trello, Spreadsheets or Telegram API.
Jobs can be ran from scheduler or from anywhere else for a one-off action.
"""

import logging
import time
from typing import Callable, List


logger = logging.getLogger(__name__)

# Delay to ensure messages come in right order.
MESSAGE_DELAY_SEC = 0.1


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
