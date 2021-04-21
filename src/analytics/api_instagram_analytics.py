from .base_analytics import BaseAnalytics
from datetime import datetime, timedelta

from ..consts import ReportPeriod
from ..instagram.instagram_client import InstagramClient


class ApiInstagramAnalytics(BaseAnalytics):

    def __init__(self, ig_client: InstagramClient):
        self._ig_client = ig_client

    def get_new_posts_count(self, since: datetime, until: datetime) -> int:
        return self._ig_client.get_new_posts_count(since, until)

    def get_new_subscribers_count(self, since: datetime, until: datetime) -> int:
        new_subscribers = self._ig_client.get_new_subscribers(since, until)
        return sum(map(lambda day: day['value'], new_subscribers['data'][0]['values']))

    def get_reach(self, since: datetime, until: datetime) -> int:
        new_subscribers = self._ig_client.get_reach(since, until)
        return sum(map(lambda day: day['value'], new_subscribers['data'][0]['values']))

    def get_interactions_count(self, since: datetime, until: datetime) -> int:
        likes_count = self._ig_client.get_likes_count(since, until)
        comments_count = self._ig_client.get_comments_count(since, until)
        saves_count = self._ig_client.get_saves_count(since, until)
        return likes_count + comments_count + saves_count

    def get_likes_count(self, since: datetime, until: datetime) -> int:
        return self._ig_client.get_likes_count(since, until)

    def get_likes_avg(self, since: datetime, until: datetime) -> int:
        return self._ig_client.get_likes_avg(since, until)

    def get_comments_count(self, since: datetime, until: datetime) -> int:
        return self._ig_client.get_comments_count(since, until)

    @staticmethod
    def _get_end_week_day_start(end_week_day: datetime) -> datetime:
        return end_week_day - timedelta(days=1) + timedelta(microseconds=1)

    @staticmethod
    def _get_end_week_day_end(end_week_day: datetime) -> datetime:
        return end_week_day
