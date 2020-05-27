import logging

from .utils import is_sender_admin, is_group_chat, get_sender_id, reply

logger = logging.getLogger(__name__)


def start(update, tg_context):
    sender_id = get_sender_id(update)
    if is_group_chat(update) and not is_sender_admin(update):
        logger.warning(
            f'/start was invoked in a group {update.message.chat_id} by {sender_id}'
        )
        return
    reply('''
Привет!

Я — бот Системного Блока. Меня создали для того, чтобы я помогал авторам, редакторам, кураторам и другим участникам проекта.

Например, я умею проводить субботники в Trello-доске и сообщать о найденных неточностях: карточках без авторов, сроков и тегов рубрик, а также авторах без карточек и карточках с пропущенным дедлайном. Для их исправления мне понадобится ваша помощь, без кожаных мешков пока не справляюсь.

Хорошего дня! Не болейте!
'''.strip(), update)  # noqa
