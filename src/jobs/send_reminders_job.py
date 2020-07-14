import logging
from typing import Callable

from ..app_context import AppContext
from ..strings import load
from ..tg.sender import TelegramSender
from .base_job import BaseJob

logger = logging.getLogger(__name__)


class SendRemindersJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None], called_from_handler=False):
        sender = TelegramSender()
        reminders = app_context.db_client.get_reminders_to_send()
        for reminder in reminders:
            if reminder.is_active:
                sender.send_to_chat_id(reminder.text, reminder.group_chat_id)
            else:
                logger.info(f'Reminder {reminder.name} not sent (deactivated)')
<<<<<<< HEAD
        send(f'Sent {len(reminders)} reminders')
=======
        send(load('send_reminders_job__success', length=len(reminders)))
>>>>>>> af66cc68352ad5e1c2f34276af7d6161546264f0
