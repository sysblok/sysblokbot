import logging

from ..tg.sender import TelegramSender


class ErrorBroadcastHandler(logging.StreamHandler):
    def __init__(self, tg_sender: TelegramSender):
        super().__init__()
        self.tg_sender = tg_sender

    def emit(self, record: logging.LogRecord):
        super().emit(record)
        if record.levelno >= logging.ERROR:
            self.tg_sender.send_error_log(
                f'<code>{record.levelname} - {record.module} - {record.message}</code>'
            )
