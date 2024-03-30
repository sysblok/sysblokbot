import json
import logging
import telegram

from ...db.db_client import DBClient
from ...strings import load
from .utils import get_sender_username, reply


logger = logging.getLogger(__name__)


def get_board_credentials(update: telegram.Update, tg_context):
    member = next((
        member for member in DBClient().get_all_members()
        if member.telegram == f"@{get_sender_username(update)}"
    ), None)
    if member is None or not member.trello:
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
                    reply(load('get_board_credentials_handler__not_found'), update)
                    return
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
