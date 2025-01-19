import logging

from ...scheduler import JobScheduler
from .utils import admin_only, reply

logger = logging.getLogger(__name__)


@admin_only
def list_jobs(update, tg_context):
    reply("\n\n".join(JobScheduler.list_jobs(tg_context.bot)), update)
