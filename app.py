#!/usr/bin/env python3

import logging
import os

from src.bot import SysBlokBot
from src.scheduler import JobScheduler
from src.config_manager import ConfigManager


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

# Global constants
ROOT_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
CONFIG_PATH = os.path.join(ROOT_DIR, 'config.json')
CONFIG_OVERRIDE_PATH = os.path.join(ROOT_DIR, 'config_override.json')


def get_bot():
    config = ConfigManager(
        CONFIG_PATH, CONFIG_OVERRIDE_PATH
    ).load_config_with_override()
    if not config:
        raise ValueError(f"Could not load config, can't go on")

    bot = SysBlokBot(config)
    bot.init_handlers()

    scheduler = JobScheduler(config, bot)
    scheduler.init_jobs()

    return bot


if __name__ == '__main__':
    get_bot().run()
