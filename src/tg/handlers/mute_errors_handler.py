import logging

from .utils import admin_only, reply
from ...utils.log_handler import ErrorBroadcastHandler

logger = logging.getLogger(__name__)


@admin_only
def mute_errors(update, tg_context):
    ErrorBroadcastHandler().set_muted(True)
    reply(
        'I\'ll stop sending errors to important_events_recipients (until unmuted or restarted)!',
        update
    )


@admin_only
def unmute_errors(update, tg_context):
    ErrorBroadcastHandler().set_muted(False)
    reply(
        'I\'ll be sending error logs to important_events_recipients list!',
        update
    )
