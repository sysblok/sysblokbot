import logging

from .utils import admin_only, reply
from ...scheduler import JobScheduler

logger = logging.getLogger(__name__)


@admin_only
def list_jobs(update, tg_context):
    reply("\n\n".join(JobScheduler.list_jobs()), update)
