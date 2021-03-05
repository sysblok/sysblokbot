import logging
from datetime import datetime, timedelta
from typing import Callable

from ..consts import ReportPeriod
from ..strings import load

from src.app_context import AppContext
from src.jobs.base_job import BaseJob
from src.jobs.utils import pretty_send

logger = logging.getLogger(__name__)


class VkAnalyticsReportJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None], called_from_handler=False):
        today = datetime.now()
        end_week_day = datetime(today.year, today.month, today.day) - timedelta(microseconds=1)
        week_ago = end_week_day - timedelta(days=7) + timedelta(microseconds=1)
        group = app_context.vk_client.get_group_info()
        group_stats = app_context.vk_client.get_group_stats(
            group_id=group.id,
            period=ReportPeriod.WEEK
        )
        last_30_posts = app_context.vk_client.get_posts(count=30)
        recent_posts = app_context.vk_client.get_posts_per_period(
            last_30_posts,
            week_ago,
            end_week_day
        )
        recent_posts_stats = app_context.vk_client.get_post_stats(
            group.id,
            [post.id for post in recent_posts],
            ReportPeriod.WEEK
        )
        message = load(
            'vk_analytics_report_job__text',
            link=group.url,
            name=group.name,
            since=week_ago.strftime('%d.%m'),
            until=end_week_day.strftime('%d.%m'),
            new_posts_num=len(recent_posts),
            subscribers_num=group.members_count,
            subscribed=group_stats.subscribed,
            unsubscribed=group_stats.unsubscribed,
            total_reach=format_int(group_stats.total_reach),
            mobile_reach=format_int(group_stats.mobile_reach),
            subscribers_reach=format_int(group_stats.reach_subscribers),
            total_posts_reach=format_int(sum([post.reach_total for post in recent_posts_stats])),
            average_post_reach=format_int(
                sum([post.reach_total for post in recent_posts_stats]) / len(recent_posts_stats)
            ),
            likes_num=group_stats.likes,
            comments_num=group_stats.comments,
            reposts_num=group_stats.reposts,
            views_num=format_int(group_stats.views),
            visitors_num=format_int(group_stats.visitors),
            likes_posts_num=sum([post.likes for post in recent_posts]),
            comments_posts_num=sum([post.comments for post in recent_posts]),
            reposts_posts_num=sum([post.reposts for post in recent_posts]),
            average_likes_num='%.1f' % (
                sum([post.likes for post in recent_posts]) / len(recent_posts)
            ),
            reports_num=sum([post.reports for post in recent_posts_stats]),
            hides_num=sum([post.hides for post in recent_posts_stats]),
            unsubscribed_posts_num=sum([post.unsubscribed for post in recent_posts_stats]),
            links_follow_num=sum([post.links for post in recent_posts_stats])
        )
        pretty_send([message], send)


def format_int(num: int) -> str:
    if num < 1000:
        return str(num)
    return '%.1fk' % (num / 1000)
