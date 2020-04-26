#!/usr/bin/env python3

import logging

from src.bot import SysBlokBot
from src.config_manager import ConfigManager
from src.consts import CONFIG_PATH, CONFIG_OVERRIDE_PATH, TELEGRAM_CONFIG
from src.scheduler import JobScheduler
from src.tg.sender import TelegramSender


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)


def get_bot():
    """
    All singletone classes must be initialized within this method before bot
    actually launched. This includes clients, config manager and scheduler.
    """
    config_manager = ConfigManager(CONFIG_PATH, CONFIG_OVERRIDE_PATH)
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

    return bot


if __name__ == '__main__':
    get_bot().run()
