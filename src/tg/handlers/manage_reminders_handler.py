import logging
from typing import List, Tuple

import telegram

from ... import consts
from ...db.db_client import DBClient
from ...db.db_objects import Chat, Reminder
from ...strings import load
from .utils import admin_only, direct_message_only, get_sender_id, manager_only, reply

TASK_NAME = "manage_reminders"

logger = logging.getLogger(__name__)


@manager_only
@direct_message_only
def manage_reminders(update: telegram.Update, tg_context: telegram.ext.CallbackContext):
    return _manage_reminders(update, tg_context, get_sender_id(update))


@admin_only
@direct_message_only
def manage_all_reminders(
    update: telegram.Update, tg_context: telegram.ext.CallbackContext
):
    return _manage_reminders(update, tg_context, None)


def _manage_reminders(update, tg_context, reminder_owner_id: int):
    # create buttons
    button_new = telegram.InlineKeyboardButton(
        load("manage_reminders_handler__create_btn"),
        callback_data=consts.ButtonValues.MANAGE_REMINDERS__ACTIONS__NEW.value,
    )
    button_edit = telegram.InlineKeyboardButton(
        load("manage_reminders_handler__edit_btn"),
        callback_data=consts.ButtonValues.MANAGE_REMINDERS__ACTIONS__EDIT.value,
    )
    button_delete = telegram.InlineKeyboardButton(
        load("manage_reminders_handler__delete_btn"),
        callback_data=consts.ButtonValues.MANAGE_REMINDERS__ACTIONS__DELETE.value,
    )

    # set initial dialogue data
    reminders = DBClient().get_reminders_by_user_id(reminder_owner_id)

    tg_context.chat_data[consts.LAST_ACTIONABLE_COMMAND] = TASK_NAME
    tg_context.chat_data[TASK_NAME] = {
        consts.NEXT_ACTION: consts.PlainTextUserAction.MANAGE_REMINDERS__CHOOSE_ACTION.value,
        consts.ManageRemindersData.EXISTING_REMINDERS: [
            (reminder.id, chat.title, reminder.name) for reminder, chat in reminders
        ],
    }
    if reminders:
        reply(
            _get_reminders_text(reminders),
            update,
            reply_markup=telegram.InlineKeyboardMarkup(
                [[button_new], [button_edit], [button_delete]]
            ),
        )
    else:
        reply(
            load("manage_reminders_handler__no_reminders"),
            update,
            reply_markup=telegram.InlineKeyboardMarkup([[button_new]]),
        )


def _get_reminders_text(reminders: List[Tuple[Reminder, Chat]]) -> str:
    reminders = "\n".join(
        load(
            "manage_reminders_handler__reminder",
            index=i + 1,
            title=chat.title,
            name=reminder.name,
            weekday=consts.WEEKDAYS_SHORT[int(reminder.weekday)],
            time=reminder.time,
            is_suspended=(
                ""
                if reminder.is_active
                else load("manage_reminders_handler__reminder_suspended")
            ),
        )
        for i, (reminder, chat) in enumerate(reminders)
    )
    return load("manage_reminders_handler__reminders", reminders=reminders)
