import logging
from typing import Callable

from ..app_context import AppContext
from ..strings import load
from ..tg.sender import TelegramSender
from .base_job import BaseJob

logger = logging.getLogger(__name__)


class SendRemindersJob(BaseJob):
    @staticmethod
    def _execute(
        app_context: AppContext, send: Callable[[str], None], called_from_handler=False
    ):
        sender = TelegramSender()
        reminders = app_context.db_client.get_reminders_to_send()
        for reminder in reminders:
            try:
                if reminder.is_active:
                    sender.send_to_chat_id(reminder.text, reminder.group_chat_id)
                    if reminder.send_poll:
                        poll_options = {
                            "question": load("manage_reminders_handler__poll_name"),
                            "options": [
                                load("manage_reminders_handler__poll_option_yes_btn"),
                                load("manage_reminders_handler__poll_option_no_btn"),
                            ],
                            "is_anonymous": False,
                        }
                        sender.send_to_chat_id(
                            "", reminder.group_chat_id, poll_options=poll_options
                        )
                else:
                    logger.info(f"Reminder {reminder.name} not sent (deactivated)")
            except Exception as e:
                logger.error(
                    f"Failed to send reminder {reminder.id} {reminder.name} to chat {reminder.group_chat_id}: {e}"
                )
                continue
        send(load("send_reminders_job__success", length=len(reminders)))

    @staticmethod
    def _usage_muted():
        return True
