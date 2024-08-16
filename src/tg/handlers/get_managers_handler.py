from ... import consts
from ...config_manager import ConfigManager
from .utils import admin_only, reply


@admin_only
async def get_managers(update, tg_context):
    config_manager = ConfigManager()
    manager_ids = config_manager.get_telegram_config()[consts.TELEGRAM_MANAGER_IDS][:]
    await reply(str(manager_ids), update)
