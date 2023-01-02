import json
import logging

from .utils import admin_only, reply, manager_only
from ... import consts, jobs
from ...app_context import AppContext
from ...config_manager import ConfigManager
from ...scheduler import JobScheduler
from ...strings import load
from ...tg.sender import TelegramSender

logger = logging.getLogger(__name__)


@admin_only
def get_config(update, tg_context):
    config = ConfigManager().get_latest_config()
    try:
        tokens = update.message.text.strip().split()
        config_path = tokens[1] if len(tokens) > 1 else ""
        if config_path:
            for config_item in config_path.split("."):
                config = config[config_item]
    except Exception as e:
        reply(load("access_config_handler__get_config_usage_example"), update)
        logger.warning(f"Failed to get config: {e}")
        return
    reply(
        load(
            "common__code_wrapper",
            arg=json.dumps(ConfigManager.redact(config), indent=2),
        ),
        update,
    )


@admin_only
def get_config_jobs(update, tg_context):
    config_jobs = ConfigManager().get_latest_jobs_config()
    try:
        tokens = update.message.text.strip().split()
        config_path = tokens[1] if len(tokens) > 1 else ""
        if config_path:
            for config_item in config_path.split("."):
                config_jobs = config_jobs[config_item]
    except Exception as e:
        reply(load("access_config_handler__get_jobs_config_usage_example"), update)
        logger.warning(f"Failed to get jobs config: {e}")
        return
    reply(
        load(
            "common__code_wrapper",
            arg=json.dumps(ConfigManager.redact(config_jobs), indent=2),
        ),
        update,
    )


@manager_only
def reload_config_jobs(update, tg_context):
    try:
        jobs_config_file_key = ConfigManager().get_jobs_config_file_key()
        if jobs_config_file_key is None:
            raise Exception("No jobs config file key provided")
        jobs_config_json = AppContext().drive_client.download_json(jobs_config_file_key)
        config_jobs = ConfigManager().set_jobs_config_with_override_from_json(
            jobs_config_json
        )
        job_scheduler = JobScheduler()
        job_scheduler.reschedule_jobs()
    except Exception as e:
        reply(load("access_config_handler__reload_config_jobs_usage_example"), update)
        logger.warning(f"Failed to reload jobs config: {e}")
        return
    reply(
        load(
            "common__code_wrapper",
            arg=json.dumps(ConfigManager.redact(config_jobs), indent=2),
        ),
        update,
    )


@admin_only
def set_config(update, tg_context):
    try:
        tokens = update.message.text.strip().split(maxsplit=2)
        assert len(tokens) == 3
        config_path = tokens[1]
        new_value = json.loads(tokens[2])
        _set_config(update, config_path, new_value, ConfigManager())
    except Exception as e:
        reply(load("access_config_handler__set_config_usage_example"), update)
        logger.warning(f"Failed to set config: {e}")
        return


@admin_only
def add_manager(update, tg_context):
    try:
        tokens = update.message.text.strip().split(maxsplit=2)
        assert len(tokens) == 2
        manager_id = json.loads(tokens[1])
        assert isinstance(manager_id, int) or (
            isinstance(manager_id, str) and not manager_id.startswith("@")
        )
        config_manager = ConfigManager()
        manager_ids = config_manager.get_telegram_config()[consts.TELEGRAM_MANAGER_IDS][
            :
        ]
        if manager_id not in manager_ids:
            manager_ids.append(manager_id)
        _set_config(
            update,
            f"{consts.TELEGRAM_CONFIG}.{consts.TELEGRAM_MANAGER_IDS}",
            manager_ids,
            config_manager,
        )
    except Exception as e:
        reply(load("access_config_handler__add_manager_usage_example"), update)
        logger.warning(f"Failed to add manager: {e}")
        return


@admin_only
def change_board(update, tg_context):
    try:
        tokens = update.message.text.strip().split(maxsplit=2)
        assert len(tokens) == 2
        board_id = json.loads(tokens[1])
        _set_config(
            update,
            f"{consts.TRELLO_CONFIG}.{consts.TRELLO_BOARD_ID}",
            board_id,
            ConfigManager(),
        )
    except Exception as e:
        reply(load("access_config_handler__change_board_usage_example"), update)
        logger.warning(f"Failed to change boards: {e}")
        return


def _set_config(update, config_path: str, new_value, config_manager: ConfigManager):
    current_config = config_manager.get_latest_config()
    for config_item in config_path.split("."):
        current_config = current_config[config_item]
    if isinstance(current_config, dict):
        reply(
            load(
                "access_config_handler__set_config_subconfig_dict",
                config_path=config_path,
            ),
            update,
        )
        return
    if type(current_config) != type(new_value):
        reply(
            load(
                "access_config_handler__set_config_type_mismatch",
                old_value=type(current_config).__name__,
                new_value=type(new_value).__name__,
            ),
            update,
        )
        return
    if current_config == new_value:
        reply(load("access_config_handler__set_config_no_update"), update)
        return

    config_manager.set_value_to_config_override(config_path, new_value)
    reply(
        load(
            "access_config_handler__set_config_updated",
            old_value=current_config,
            new_value=new_value,
        ),
        update,
    )
    # run config update job after config_override successfully updated
    chat_ids = config_manager.get_job_send_to("config_updater_job")
    jobs.ConfigUpdaterJob.execute(
        AppContext(), TelegramSender().create_chat_ids_send(chat_ids)
    )
