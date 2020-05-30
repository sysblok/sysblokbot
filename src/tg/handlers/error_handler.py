import logging

logger = logging.getLogger(__name__)


def error(update, tg_context):
    """Log Errors caused by Updates."""
    logger.error('Update "%s" caused error "%s"', update, tg_context.error)
