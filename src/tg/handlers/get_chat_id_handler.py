from .utils import get_chat_id, is_group_chat, reply


def get_chat_id_handler(update, tg_context):
    chat_id = get_chat_id(update)
    if is_group_chat(update):
        reply(f'Id этого чата: {chat_id}', update)
    else:
        reply(f'Твой chat_id: {chat_id}', update)
