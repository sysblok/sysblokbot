import logging

logger = logging.getLogger(__name__)


async def error(update, tg_context):
    """Log Errors caused by Updates."""
    logger.exception('Update "%s" caused error', update, exc_info=tg_context.error)
