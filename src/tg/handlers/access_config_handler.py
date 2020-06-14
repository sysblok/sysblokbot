import json
import logging

from .utils import admin_only, reply
from ... import consts, jobs
from ...app_context import AppContext
from ...config_manager import ConfigManager
from ...tg.sender import TelegramSender


logger = logging.getLogger(__name__)


@admin_only
def get_config(update, tg_context):
    config = ConfigManager().get_latest_config()
    try:
        tokens = update.message.text.strip().split()
        config_path = tokens[1] if len(tokens) > 1 else ''
        if config_path:
            for config_item in config_path.split('.'):
                config = config[config_item]
    except Exception as e:
        reply('<b>Usage example:</b>\n/get_config jobs.sample_job', update)
        logger.warning(f'Failed to get config: {e}')
        return
    reply(f'<code>{json.dumps(ConfigManager.redact(config), indent=2)}</code>', update)


@admin_only
def set_config(update, tg_context):
    try:
        tokens = update.message.text.strip().split(maxsplit=2)
        assert len(tokens) == 3
        config_path = tokens[1]
        new_value = json.loads(tokens[2])
        _set_config(update, config_path, new_value, ConfigManager())
    except Exception as e:
        reply((
            '<b>Usage example:</b>\n/set_config jobs.sample_job.at "15:00"\n\n'
            'Try to /get_config first and follow the existing format'
        ), update)
        logger.warning(f'Failed to set config: {e}')
        return


@admin_only
def add_manager(update, tg_context):
    try:
        tokens = update.message.text.strip().split(maxsplit=2)
        assert len(tokens) == 2
        manager_id = json.loads(tokens[1])
        assert isinstance(manager_id, int) or (
            isinstance(manager_id, str) and not manager_id.startswith('@')
        )
        config_manager = ConfigManager()
        manager_ids = config_manager.get_telegram_config()[consts.TELEGRAM_MANAGER_IDS][:]
        if manager_id not in manager_ids:
            manager_ids.append(manager_id)
        _set_config(
            update,
            f'{consts.TELEGRAM_CONFIG}.{consts.TELEGRAM_MANAGER_IDS}',
            manager_ids,
            config_manager
        )
    except Exception as e:
        reply(('<b>Usage example:</b>\n/add_manager 12345 or /add_manager "tg_login"'), update)
        logger.warning(f'Failed to add manager: {e}')
        return


@admin_only
def change_board(update, tg_context):
    try:
        tokens = update.message.text.strip().split(maxsplit=2)
        assert len(tokens) == 2
        board_id = json.loads(tokens[1])
        _set_config(
            update,
            f'{consts.TRELLO_CONFIG}.{consts.TRELLO_BOARD_ID}',
            board_id,
            ConfigManager()
        )
    except Exception as e:
        reply(('<b>Usage example:</b>\n/change_board "12345"'), update)
        logger.warning(f'Failed to change boards: {e}')
        return


def _set_config(update, config_path: str, new_value, config_manager: ConfigManager):
    current_config = config_manager.get_latest_config()
    for config_item in config_path.split('.'):
        current_config = current_config[config_item]
    if isinstance(current_config, dict):
        reply((
            f'Subconfig <code>{config_path}</code> is a complex object. '
            'Dict reassignment is not supported. '
            'Please, specify your request to str, bool, int or list field'
        ), update)
        return
    if type(current_config) != type(new_value):
        reply((
            f'Type mismatch. Old value was <code>{type(current_config).__name__}</code>, '
            f'new value is <code>{type(new_value).__name__}</code>. '
            'Try /get_config to see current value format'
        ), update)
        return
    if current_config == new_value:
        reply('New value equals to existing. Nothing was updated', update)
        return

    config_manager.set_value_to_config_override(config_path, new_value)
    reply((
        f'Successfully updated!\n'
        f'Old value: <code>{current_config}</code>\n'
        f'New value: <code>{new_value}</code>'
    ), update)
    # run config update job after config_override successfully updated
    chat_ids = config_manager.get_job_send_to('config_updater_job')
    jobs.ConfigUpdaterJob.execute(AppContext(), TelegramSender().create_chat_ids_send(chat_ids))
