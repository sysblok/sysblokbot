import logging

import telegram

from ... import consts
from .utils import manager_only, reply

TASK_NAME = 'get_tasks_report'

logger = logging.getLogger(__name__)


@manager_only
def get_tasks_report(update: telegram.Update, tg_context: telegram.ext.CallbackContext):
    # set initial dialogue data
    tg_context.chat_data[consts.LAST_ACTIONABLE_COMMAND] = TASK_NAME
    tg_context.chat_data[TASK_NAME] = {
        consts.NEXT_ACTION: consts.PlainTextUserAction.ENTER_BOARD_URL.value
    }
    reply("Привет! Пришли, пожалуйста, ссылку на доску в Trello.", update)
