import logging

from ...scheduler import JobScheduler
from .utils import admin_only, reply

logger = logging.getLogger(__name__)


@admin_only
async def list_jobs(update, tg_context):
    await reply("\n\n".join(JobScheduler.list_jobs()), update)
