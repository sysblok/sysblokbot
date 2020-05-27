import json
import logging

from .utils import admin_only, reply
from ... import jobs
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
    config_manager = ConfigManager()
    current_config = config_manager.get_latest_config()
    try:
        tokens = update.message.text.strip().split(maxsplit=2)
        assert len(tokens) == 3
        config_path = tokens[1]
        new_value = json.loads(tokens[2])
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
    except Exception as e:
        reply((
            '<b>Usage example:</b>\n/set_config jobs.sample_job.at "15:00"\n\n'
            'Try to /get_config first and follow the existing format'
        ), update)
        logger.warning(f'Failed to set config: {e}')
        return

    # run config update job after config_override successfully updated
    chat_ids = config_manager.get_job_send_to('config_updater_job')
    jobs.ConfigUpdaterJob.execute(AppContext(), TelegramSender().create_chat_ids_send(chat_ids))
