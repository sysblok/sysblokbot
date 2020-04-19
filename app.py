#!/usr/bin/env python3

import logging

from src.bot import SysBlokBot
from src.consts import CONFIG_PATH, CONFIG_OVERRIDE_PATH
from src.scheduler import JobScheduler
from src.config_manager import ConfigManager


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)


def get_bot():
    config = ConfigManager(
        CONFIG_PATH, CONFIG_OVERRIDE_PATH
    ).load_config_with_override()
    if not config:
        raise ValueError(f"Could not load config, can't go on")

    scheduler = JobScheduler()

    bot = SysBlokBot(config, signal_handler=lambda signum,
                     frame: scheduler.stop_running())
    bot.init_handlers()

    scheduler.initialize(config, bot)
    scheduler.init_jobs()

    return bot


if __name__ == '__main__':
    get_bot().run()
