import logging
from datetime import datetime, timedelta, timezone
from typing import Callable

from ..consts import MSK_TIMEZONE
from ..strings import load
from ..tg.sender import pretty_send
from src.app_context import AppContext
from src.jobs.base_job import BaseJob

logger = logging.getLogger(__name__)


class IGAnalyticsReportJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None], called_from_handler=False):
        # statistics for current day hasn't fully calculated yet
        # use statistics for previous day
        today = datetime.now(MSK_TIMEZONE)
        end_week_day = datetime(
            today.year, today.month, today.day, tzinfo=today.tzinfo
        ) - timedelta(microseconds=1)
        week_ago = end_week_day - timedelta(days=7) + timedelta(microseconds=1)
        page = app_context.instagram_client.get_page()
        message = load(
            'ig_analytics_report_job__text',
            username=page.username,
            name=page.name,
            since=week_ago.strftime('%d.%m'),
            until=end_week_day.strftime('%d.%m'),
            new_posts=app_context.instagram_analytics.get_new_posts_count(week_ago, end_week_day),
            # new_stories=-1,
            subscribers_new_num=app_context.instagram_analytics.get_new_subscribers_count(
                week_ago, end_week_day
            ),
            subscribers_total_num=app_context.instagram_analytics.get_total_subscribers_count(),
            # subscribed=-1,
            # unsubscribed=-1,
            total_reach=app_context.instagram_analytics.get_reach(week_ago, end_week_day),
            # total_reach_delta=-1,
            content_interactions_num=app_context.instagram_analytics.get_interactions_count(
                week_ago, end_week_day
            ),
            # content_interactions_delta=-1,
            likes_num=app_context.instagram_analytics.get_likes_count(week_ago, end_week_day),
            comments_num=app_context.instagram_analytics.get_comments_count(
                week_ago, end_week_day
            ),
            likes_avg=app_context.instagram_analytics.get_likes_avg(
                week_ago, end_week_day
            ),
        )
        pretty_send([message], send)
