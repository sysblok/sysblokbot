import html
from logging import ERROR, Formatter, LogRecord, StreamHandler

from ..consts import LOG_FORMAT, USAGE_LOG_LEVEL
from ..tg.sender import TelegramSender
from .singleton import Singleton


class ErrorBroadcastHandler(StreamHandler, Singleton):
    def __init__(self, tg_sender: TelegramSender = None):
        if self.was_initialized():
            return
        if tg_sender is None:
            raise ValueError(
                "On first initialization must pass tg_sender to ErrorBroadcastHandler"
            )
        super().__init__()
        self.setFormatter(Formatter(LOG_FORMAT))
        self.tg_sender = tg_sender
        self.is_muted = False

    def emit(self, record: LogRecord):
        self.format(record)
        super().emit(record)
        if record.levelno == USAGE_LOG_LEVEL and not self.is_muted:
            try:
                usage_message = f"{record.asctime} - {record.message}"
                if record.exc_text:
                    usage_message += f" - {record.exc_text}"
                self.tg_sender.send_usage_log(
                    f"<code>{html.escape(usage_message)}</code>"
                )
            except Exception as e:
                # if it can't send a message, still should log it to the stream
                super().emit(
                    LogRecord(
                        name=__name__,
                        level=ERROR,
                        pathname=None,
                        lineno=-1,
                        msg=f"Could not send error to telegram: {e}",
                        args=None,
                        exc_info=None,
                    )
                )
        if record.levelno >= ERROR and not self.is_muted:
            error_message = f"{record.levelname} - {record.module} - {record.message}"
            if record.exc_text:
                error_message += f" - {record.exc_text}"
            try:
                self.tg_sender.send_error_log(
                    f"<code>{html.escape(error_message)}</code>"
                )
            except Exception as e:
                # if it can't send a message, still should log it to the stream
                super().emit(
                    LogRecord(
                        name=__name__,
                        level=ERROR,
                        pathname=None,
                        lineno=-1,
                        msg=f"Could not send error to telegram: {e}",
                        args=None,
                        exc_info=None,
                    )
                )

    def set_muted(self, is_muted: bool):
        self.is_muted = is_muted
