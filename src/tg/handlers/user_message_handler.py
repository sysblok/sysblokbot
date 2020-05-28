import logging

logger = logging.getLogger(__name__)


def handle_user_message(update, tg_context):
    # TODO: depending on user state, do anything (postpone the task, etc)
    if update.message is not None:
        logger.debug(
            f'Got {update.message.text} from {update.message.chat_id}'
        )
