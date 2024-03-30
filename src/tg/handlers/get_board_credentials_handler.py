import json
import logging
import telegram

from ...db.db_client import DBClient
from ...strings import load
from .utils import get_sender_id, get_sender_username, reply


logger = logging.getLogger(__name__)


def get_board_credentials(update: telegram.Update, tg_context):
    if update.message.chat_id < 0:
        return
    member = next((
        member for member in DBClient().get_all_members()
        if member.telegram == f"@{get_sender_username(update)}"
    ), None)
    if member is None or not member.trello:
        logger.usage(
            f'Trello not found for {get_sender_username(update)}, ID={get_sender_id(update)}'
        )
        reply(load('get_board_credentials_handler__not_found'), update)
        return
    try:
        print(member.trello)
        with open('board_credentials.json', encoding="utf-8") as fin:
            try:
                board_json = json.loads(fin.read())
                creds = next((
                    cred for cred in board_json if cred["trelloUsername"] == member.trello
                ), None)
                if not creds:
                    logger.usage(
                        f'Board creds not found for user {get_sender_username(update)}'
                    )
                    reply(load('get_board_credentials_handler__not_found'), update)
                    return
                logger.usage(f'Board creds found for username {get_sender_username(update)}')
                reply(
                    load(
                        'get_board_credentials_handler__found',
                        username=creds["focalboardUsername"][1:],
                        password=creds["focalboardPassword"]
                    ),
                    update
                )
            except json.JSONDecodeError as e:
                logger.error(e)
    except IOError:
        logger.warning(f"Board passwords file not found", exc_info=e)
