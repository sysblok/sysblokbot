#!/usr/bin/env python3

import logging
import os

from src.bot import SysBlokBot
from src.config_manager import ConfigManager
from src import consts
from src.scheduler import JobScheduler
from src.tg.sender import TelegramSender
from src.utils.log_handler import ErrorBroadcastHandler


logging.basicConfig(format=consts.LOG_FORMAT, level=logging.INFO)


def get_bot():
    """
    All singletone classes must be initialized within this method before bot
    actually launched. This includes clients, config manager and scheduler.
    """
    config_manager = ConfigManager(consts.CONFIG_PATH, consts.CONFIG_OVERRIDE_PATH)
    config = config_manager.load_config_with_override()
    if not config:
        raise ValueError(f"Could not load config, can't go on")

    scheduler = JobScheduler(config)

    bot = SysBlokBot(config_manager, signal_handler=lambda signum,
                     frame: scheduler.stop_running())
    bot.init_handlers()

    # Scheduler must be run after clients initialized
    scheduler.run()
    scheduler.init_jobs()

    # Setting final logger and sending a message bot is up
    tg_sender = TelegramSender()

    for handler in logging.getLogger().handlers:
        logging.getLogger().removeHandler(handler)
    logging.getLogger().addHandler(ErrorBroadcastHandler(tg_sender))

    start_msg = (
        f'[{consts.APP_SOURCE.value}] Bot successfully started, '
        f'revision <a href="{consts.COMMIT_URL}">{consts.COMMIT_HASH}</a>.'
    )
    tg_sender.send_important_event(start_msg)

    return bot


if __name__ == '__main__':
    get_bot().run()
