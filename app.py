#!/usr/bin/env python3

import argparse
import locale
import logging
import os
import requests

from src.bot import SysBlokBot
from src.config_manager import ConfigManager
from src import consts
from src.scheduler import JobScheduler
from src.tg.sender import TelegramSender
from src.utils.log_handler import ErrorBroadcastHandler


locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
logging.basicConfig(format=consts.LOG_FORMAT, level=logging.INFO)

parser = argparse.ArgumentParser()
# maybe we'll move those to config.json later...
parser.add_argument("--skip-db-update", help="Skip db update on startup", action='store_true')


def get_bot():
    """
    All singleton classes must be initialized within this method before bot
    actually launched. This includes clients, config manager and scheduler.
    """
    config_manager = ConfigManager(consts.CONFIG_PATH, consts.CONFIG_OVERRIDE_PATH)
    config = config_manager.load_config_with_override()
    if not config:
        raise ValueError(f"Could not load config, can't go on")
    config_manager_jobs = ConfigManager(consts.CONFIG_JOBS_PATH, consts.CONFIG_JOBS_OVERRIDE_PATH)
    config_jobs = config_manager_jobs.load_config_with_override()
    if not config_jobs:
        raise ValueError(f"Could not load job config, can't go on")

    scheduler = JobScheduler(config_jobs)
    args = parser.parse_args()

    bot = SysBlokBot(config_manager, signal_handler=lambda signum,
                     frame: scheduler.stop_running(),
                     skip_db_update=args.skip_db_update)
    bot.init_handlers()

    # Setting final logger and sending a message bot is up
    tg_sender = TelegramSender()

    for handler in logging.getLogger().handlers:
        logging.getLogger().removeHandler(handler)
    logging.getLogger().addHandler(ErrorBroadcastHandler(tg_sender))

    # Scheduler must be run after clients initialized
    scheduler.run()
    scheduler.init_jobs()

    start_msg = f'[{consts.APP_SOURCE}] Bot successfully started'
    if consts.COMMIT_HASH:
        start_msg += (
            f', revision <a href="{consts.COMMIT_URL}">{consts.COMMIT_HASH}</a>.'
        )
    tg_sender.send_important_event(start_msg)

    return bot


def report_critical_error(e: BaseException):
    requests.post(
        url=f'https://api.telegram.org/bot{consts.TELEGRAM_TOKEN}/sendMessage',
        json={
            'text': f'Sysblokbot is down, {e}\n',
            'chat_id': consts.TELEGRAM_ERROR_CHAT_ID,
            'parse_mode': 'markdown',
        }
    )


if __name__ == '__main__':
    try:
        get_bot().run()
    except BaseException as e:
        report_critical_error(e)
