from ...db.db_client import DBClient
from ...strings import load
from .utils import get_chat_id, get_chat_name, is_group_chat, reply


def get_chat_id_handler(update, tg_context):
    chat_id = get_chat_id(update)
    if is_group_chat(update):
        reply(load("get_chat_id_handler__group", chat_id=chat_id), update)
    else:
        reply(load("get_chat_id_handler__direct", chat_id=chat_id), update)
    DBClient().set_chat_name(get_chat_id(update), get_chat_name(update))
