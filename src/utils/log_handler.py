import logging

from .singleton import Singleton
from ..tg.sender import TelegramSender


class ErrorBroadcastHandler(logging.StreamHandler, Singleton):
    def __init__(self, tg_sender: TelegramSender = None):
        if self.was_initialized():
            return
        if tg_sender is None:
            raise ValueError(
                'On first initialization must pass tg_sender to ErrorBroadcastHandler'
            )
        super().__init__()
        self.tg_sender = tg_sender
        self.is_muted = False

    def emit(self, record: logging.LogRecord):
        if record.levelno >= logging.ERROR and not self.is_muted:
            self.tg_sender.send_error_log(
                f'<code>{record.levelname} - {record.module} - {record.message}</code>'
            )

    def set_muted(self, is_muted: bool):
        self.is_muted = is_muted
