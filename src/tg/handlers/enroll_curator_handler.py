from ...db.db_client import DBClient

from ...strings import load
from .utils import direct_message_only, get_chat_id, get_chat_name, reply


@direct_message_only
def enroll_curator(update, tg_context):
    chat_id = get_chat_id(update)
    telegram_login = get_chat_name(update)
    db_client = DBClient()
    curator = db_client.get_curator_by_telegram(telegram_login)
    if curator:
        db_client.set_chat_name(chat_id, telegram_login, set_curator=True)
        reply(load("enroll_curator_handler__success"), update)
    else:
        reply(load("enroll_curator_handler__not_found"), update)
