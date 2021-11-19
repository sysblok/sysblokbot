from .base_analytics import BaseAnalytics
from datetime import datetime, timedelta

from ..consts import ReportPeriod
from ..vk.vk_client import VkClient


class ApiVkAnalytics(BaseAnalytics):
    # TODO: maybe move __init__ to BaseAnalytics
    def __init__(self, vk_client: VkClient):
        self._vk_client = vk_client

    def get_new_posts_count(self, since: datetime, until: datetime):
        return self._vk_client.get_new_posts_count(since, until)

    def get_weekly_total_reach_of_new_posts(self, end_week: datetime):
        result = self._vk_client.get_total_reach(
            ApiVkAnalytics._get_end_week_day_start(end_week),
            ApiVkAnalytics._get_end_week_day_end(end_week),
            period=ReportPeriod.WEEK
        )
        if not result:
            return 0
        return result[0][1]

    def get_weekly_organic_reach_of_new_posts(self, end_week: datetime):
        result = self._vk_client.get_organic_reach(
            ApiVkAnalytics._get_end_week_day_start(end_week),
            ApiVkAnalytics._get_end_week_day_end(end_week),
            period=ReportPeriod.WEEK
        )
        if not result:
            return 0
        return result[0][1]

    def get_weekly_new_follower_count(self, end_week: datetime):
        result = self._vk_client.get_new_follower_count(
            ApiVkAnalytics._get_end_week_day_start(end_week),
            ApiVkAnalytics._get_end_week_day_end(end_week),
            period=ReportPeriod.WEEK
        )
        if not result:
            return 0
        return result[0][1]

    def get_weekly_new_fan_count(self, end_week: datetime):
        result = self._vk_client.get_new_fan_count(
            ApiVkAnalytics._get_end_week_day_start(end_week),
            ApiVkAnalytics._get_end_week_day_end(end_week),
            period=ReportPeriod.WEEK
        )
        if not result:
            return 0
        return result[0][1]

    @staticmethod
    def _get_end_week_day_start(end_week_day: datetime) -> datetime:
        return end_week_day - timedelta(days=1) + timedelta(microseconds=1)

    @staticmethod
    def _get_end_week_day_end(end_week_day: datetime) -> datetime:
        return end_week_day
