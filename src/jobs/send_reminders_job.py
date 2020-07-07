import logging
from typing import Callable

from ..app_context import AppContext
from ..tg.sender import TelegramSender
from .base_job import BaseJob

logger = logging.getLogger(__name__)


class SendRemindersJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None], called_from_handler=False):
        sender = TelegramSender()
        reminders = app_context.db_client.get_reminders_to_send()
        for reminder in reminders:
            sender.send_to_chat_id(reminder.text, reminder.group_chat_id)
        send(f'Sent {len(reminders)} reminders')
