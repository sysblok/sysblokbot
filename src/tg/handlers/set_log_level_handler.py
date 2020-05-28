import logging

from .utils import admin_only, reply

logger = logging.getLogger(__name__)


@admin_only
def set_log_level(update, tg_context):
    level = update.message.text.strip().split()[-1].upper()
    try:
        if level == 'DEBUG':
            logging.getLogger().setLevel(logging.DEBUG)
        elif level == 'INFO':
            logging.getLogger().setLevel(logging.INFO)
    except Exception as e:
        logger.error(f'Failed to update log level to {level}: {e}')
    reply(f'Log level set to {logging.getLogger().level}', update)
