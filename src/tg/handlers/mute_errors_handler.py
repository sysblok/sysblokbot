import logging

from ...strings import load
from ...utils.log_handler import ErrorBroadcastHandler
from .utils import admin_only, reply

logger = logging.getLogger(__name__)


@admin_only
async def mute_errors(update, tg_context):
    ErrorBroadcastHandler().set_muted(True)
    await reply(load("mure_errors_handler__mute"), update)


@admin_only
async def unmute_errors(update, tg_context):
    ErrorBroadcastHandler().set_muted(False)
    await reply(load("mure_errors_handler__unmute"), update)
