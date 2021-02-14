from .base_facebook_analytics import BaseFacebookAnalytics
from datetime import datetime, timedelta

from ..facebook.facebook_client import FacebookClient, ReportPeriod


class ApiFacebookAnalytics(BaseFacebookAnalytics):

    def __init__(self, fb_client: FacebookClient):
        self._fb_client = fb_client

    def get_new_posts_count(self, since: datetime, until: datetime):
        return self._fb_client.get_new_posts_count(since, until)

    def get_weekly_total_reach_of_new_posts(self, end_week: datetime):
        end_week_day_start = end_week - timedelta(days=1) + timedelta(microseconds=1)
        end_week_day_end = end_week
        result = self._fb_client.get_total_reach(
            end_week_day_start, end_week_day_end, period=ReportPeriod.WEEK
        )
        if not result:
            return 0
        return result[0][1]

    def get_weekly_organic_reach_of_new_posts(self, end_week: datetime):
        end_week_day_start = end_week - timedelta(days=1) + timedelta(microseconds=1)
        end_week_day_end = end_week
        result = self._fb_client.get_organic_reach(
            end_week_day_start,
            end_week_day_end,
            period=ReportPeriod.WEEK
        )
        if not result:
            return 0
        return result[0][1]
