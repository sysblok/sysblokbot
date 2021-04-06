from .base_analytics import BaseAnalytics
from datetime import datetime, timedelta

from ..consts import ReportPeriod
from ..instagram.instagram_client import InstagramClient


class ApiInstagramAnalytics(BaseAnalytics):

    def __init__(self, ig_client: InstagramClient):
        self._ig_client = ig_client

    def get_new_posts_count(self, since: datetime, until: datetime):
        return self._ig_client.get_new_posts_count(since, until)

    def get_new_subscribers_count(self, since: datetime, until: datetime):
        new_subscribers = self._ig_client.get_new_subscribers_count(since, until)
        return sum(new_subscribers)

    @staticmethod
    def _get_end_week_day_start(end_week_day: datetime) -> datetime:
        return end_week_day - timedelta(days=1) + timedelta(microseconds=1)

    @staticmethod
    def _get_end_week_day_end(end_week_day: datetime) -> datetime:
        return end_week_day
