import logging
from datetime import datetime, timedelta
from typing import Callable, Iterable

from src.app_context import AppContext
from src.jobs.base_job import BaseJob

from ..consts import ReportPeriod
from ..sheets.sheets_objects import PostRegistryItem
from ..strings import load
from ..tg.sender import pretty_send
from ..vk.vk_objects import VkPost, VkPostStats

logger = logging.getLogger(__name__)


class VkAnalyticsReportJobNew(BaseJob):
    @staticmethod
    def _execute(
        app_context: AppContext, send: Callable[[str], None], called_from_handler=False
    ):
        today = datetime.now()
        end_week_day = datetime(today.year, today.month, today.day) - timedelta(
            microseconds=1
        )
        week_ago = end_week_day - timedelta(days=7) + timedelta(microseconds=1)
        group = app_context.vk_client.get_group_info()
        print(group)
        message = load(
            "vk_analytics_report_job_new",
            since=week_ago.strftime("%d.%m"),
            until=end_week_day.strftime("%d.%m"),
            name=group.name,
            link=group.url,
        )
        pretty_send([message], send)
