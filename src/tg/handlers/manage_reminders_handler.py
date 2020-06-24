import logging
from typing import List, Tuple

import telegram

from ... import consts
from ...db.db_client import DBClient
from ...db.db_objects import Chat, Reminder
from .utils import get_sender_id, manager_only, reply

TASK_NAME = 'manage_reminders'

logger = logging.getLogger(__name__)


@manager_only
def manage_reminders(update: telegram.Update, tg_context: telegram.ext.CallbackContext):
    # set initial dialogue data
    tg_context.chat_data[consts.LAST_ACTIONABLE_COMMAND] = TASK_NAME
    tg_context.chat_data[TASK_NAME] = {
        consts.NEXT_ACTION: consts.PlainTextUserAction.MANAGE_REMINDERS__CHOOSE_ACTION.value
    }
    # reply with buttons
    button_new = telegram.InlineKeyboardButton(
        "Создать новое",
        callback_data=consts.ButtonValues.MANAGE_REMINDERS__ACTIONS__NEW.value
    )
    button_edit = telegram.InlineKeyboardButton(
        "Редактировать",
        callback_data=consts.ButtonValues.MANAGE_REMINDERS__ACTIONS__EDIT.value
    )
    button_delete = telegram.InlineKeyboardButton(
        "Удалить",
        callback_data=consts.ButtonValues.MANAGE_REMINDERS__ACTIONS__DELETE.value
    )

    reminders = DBClient().get_reminders_by_user_id(get_sender_id(update))
    if reminders:
        reply(
            _get_reminders_text(reminders),
            update,
            reply_markup=telegram.InlineKeyboardMarkup(
                [[button_new], [button_edit], [button_delete]]
            )
        )
    else:
        reply(
            'Привет! У тебя пока нет напоминаний.',
            update,
            reply_markup=telegram.InlineKeyboardMarkup(
                [[button_new]]
            )
        )


def _get_reminders_text(reminders: List[Tuple[Reminder, Chat]]) -> str:
    text = 'Привет! Вот какие напоминания у тебя настроены:\n'
    text += '\n'.join(
        f'{i+1}) {chat.title}: {reminder.name}'
        for i, (reminder, chat) in enumerate(reminders)
    )
    return text
