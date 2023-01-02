from .base_analytics import BaseAnalytics
from datetime import datetime, timedelta

from ..consts import ReportPeriod
from ..facebook.facebook_client import FacebookClient


class ApiFacebookAnalytics(BaseAnalytics):
    def __init__(self, fb_client: FacebookClient):
        self._fb_client = fb_client

    def get_new_posts_count(self, since: datetime, until: datetime):
        return self._fb_client.get_new_posts_count(since, until)

    def get_weekly_total_reach_of_new_posts(self, end_week: datetime):
        result = self._fb_client.get_total_reach(
            ApiFacebookAnalytics._get_end_week_day_start(end_week),
            ApiFacebookAnalytics._get_end_week_day_end(end_week),
            period=ReportPeriod.WEEK,
        )
        if not result:
            return 0
        return result[0][1]

    def get_weekly_organic_reach_of_new_posts(self, end_week: datetime):
        result = self._fb_client.get_organic_reach(
            ApiFacebookAnalytics._get_end_week_day_start(end_week),
            ApiFacebookAnalytics._get_end_week_day_end(end_week),
            period=ReportPeriod.WEEK,
        )
        if not result:
            return 0
        return result[0][1]

    def get_weekly_new_follower_count(self, end_week: datetime):
        result = self._fb_client.get_new_follower_count(
            ApiFacebookAnalytics._get_end_week_day_start(end_week),
            ApiFacebookAnalytics._get_end_week_day_end(end_week),
            period=ReportPeriod.WEEK,
        )
        if not result:
            return 0
        return result[0][1]

    def get_weekly_new_fan_count(self, end_week: datetime):
        result = self._fb_client.get_new_fan_count(
            ApiFacebookAnalytics._get_end_week_day_start(end_week),
            ApiFacebookAnalytics._get_end_week_day_end(end_week),
            period=ReportPeriod.WEEK,
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
