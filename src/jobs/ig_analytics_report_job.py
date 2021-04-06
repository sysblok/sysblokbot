import logging
from datetime import datetime, timedelta, timezone
from typing import Callable

from ..consts import MSK_TIMEZONE
from ..strings import load

from src.app_context import AppContext
from src.jobs.base_job import BaseJob
from src.jobs.utils import pretty_send

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
            new_stories=0,
            subscribers_num=app_context.instagram_analytics.get_new_subscribers_count(week_ago, end_week_day),
            subscribed=0,
            unsubscribed=0,
            total_reach=0,
            total_reach_delta=0,
            content_interactions_num=0,
            content_interactions_delta=0,
            likes_num=0,
            comments_num=0,
            likes_avg=0,
        )
        # paragraphs = [
        #     "{0}: {1}".format(
        #         load('fb_analytics_report_job__new_post_count'),
        #         str(
        #             app_context.facebook_analytics.get_new_posts_count(
        #                 since=week_ago, until=end_week_day
        #             )
        #         )
        #     ),
        #     "{0}: {1}".format(
        #         load('fb_analytics_report_job__total_reach'),
        #         str(
        #             app_context.facebook_analytics.get_weekly_total_reach_of_new_posts(
        #                 end_week_day
        #             )
        #         )
        #     ),
        #     "{0}: {1}".format(
        #         load('fb_analytics_report_job__organic_reach'),
        #         str(
        #             app_context.facebook_analytics.get_weekly_organic_reach_of_new_posts(
        #                 end_week_day
        #             )
        #         )
        #     ),
        #     "{0}: {1}".format(
        #         load('fb_analytics_report_job__new_follower_count'),
        #         str(
        #             app_context.facebook_analytics.get_weekly_new_follower_count(
        #                 end_week_day
        #             )
        #         )
        #     ),
        #     "{0}: {1}".format(
        #         load('fb_analytics_report_job__new_fan_count'),
        #         str(
        #             app_context.facebook_analytics.get_weekly_new_fan_count(
        #                 end_week_day
        #             )
        #         )
        #     ),
        # ]
        pretty_send([message], send)
