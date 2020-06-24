from ...db.db_client import DBClient

from .utils import get_chat_id, get_chat_name, is_group_chat, reply


def get_chat_id_handler(update, tg_context):
    chat_id = get_chat_id(update)
    if is_group_chat(update):
        reply(f'Id этого чата: <code>{chat_id}</code>', update)
    else:
        reply(f'Твой chat_id: <code>{chat_id}</code>', update)
    DBClient().set_chat_name(get_chat_id(update), get_chat_name(update))
