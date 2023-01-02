import logging
from datetime import datetime, timedelta
from typing import Callable, Iterable

from ..consts import ReportPeriod
from ..sheets.sheets_objects import PostRegistryItem
from ..strings import load
from ..tg.sender import pretty_send
from ..vk.vk_objects import VkPostStats, VkPost

from src.app_context import AppContext
from src.jobs.base_job import BaseJob

logger = logging.getLogger(__name__)


class VkAnalyticsReportJob(BaseJob):
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
        group_stats = app_context.vk_client.get_group_stats(
            group_id=group.id, period=ReportPeriod.WEEK
        )
        last_30_posts = app_context.vk_client.get_posts(group.id, count=30)
        recent_posts = app_context.vk_client.get_posts_per_period(
            last_30_posts, week_ago, end_week_day
        )
        recent_posts_stats = app_context.vk_client.get_post_stats(
            group.id, recent_posts, ReportPeriod.WEEK
        )
        registry_table = app_context.sheets_client.fetch_posts_registry()
        # sorted in reverse, because recent posts are added to the bottom
        post_registry_items = [PostRegistryItem(item) for item in registry_table][::-1]
        top_reach_post_stats = _get_top_reach_post_stats(recent_posts_stats)
        top_likes_post = _get_top_likes_post(recent_posts)
        top_reposts_post = _get_top_reposts_post(recent_posts)
        top_comments_post = _get_top_comments_post(recent_posts)

        message = load(
            "vk_analytics_report_job__text_with_top",
            link=group.url,
            name=group.name,
            since=week_ago.strftime("%d.%m"),
            until=end_week_day.strftime("%d.%m"),
            new_posts_num=len(recent_posts),
            subscribers_num=group.members_count,
            subscribed=group_stats.subscribed,
            unsubscribed=group_stats.unsubscribed,
            total_reach=_format_int(group_stats.total_reach),
            mobile_reach=_format_int(group_stats.mobile_reach),
            subscribers_reach=_format_int(group_stats.reach_subscribers),
            total_posts_reach=_format_int(
                sum([post.reach_total for post in recent_posts_stats])
            ),
            average_post_reach=_format_int(
                sum([post.reach_total for post in recent_posts_stats])
                / len(recent_posts_stats)
            ),
            likes_num=group_stats.likes,
            comments_num=group_stats.comments,
            reposts_num=group_stats.reposts,
            views_num=_format_int(group_stats.views),
            visitors_num=_format_int(group_stats.visitors),
            likes_posts_num=sum([post.likes for post in recent_posts]),
            comments_posts_num=sum([post.comments for post in recent_posts]),
            reposts_posts_num=sum([post.reposts for post in recent_posts]),
            average_likes_num="%.1f"
            % (sum([post.likes for post in recent_posts]) / len(recent_posts)),
            reports_num=sum([post.reports for post in recent_posts_stats]),
            hides_num=sum([post.hides for post in recent_posts_stats]),
            unsubscribed_posts_num=sum(
                [post.unsubscribed for post in recent_posts_stats]
            ),
            links_follow_num=sum([post.links for post in recent_posts_stats]),
            top_reach_post_link=top_reach_post_stats.post.url,
            top_reach_post_name=top_reach_post_stats.post.get_registry_name(
                post_registry_items
            ),
            top_reach_post_num=_format_int(top_reach_post_stats.reach_total),
            top_likes_post_link=top_likes_post.url,
            top_likes_post_name=top_likes_post.get_registry_name(post_registry_items),
            top_likes_post_num=top_likes_post.likes,
            top_reposts_post_link=top_reposts_post.url,
            top_reposts_post_name=top_reposts_post.get_registry_name(
                post_registry_items
            ),
            top_reposts_post_num=top_reposts_post.reposts,
            top_comments_post_link=top_comments_post.url,
            top_comments_post_name=top_comments_post.get_registry_name(
                post_registry_items
            ),
            top_comments_post_num=top_comments_post.comments,
        )
        pretty_send([message], send)


def _format_int(num: int) -> str:
    if num < 1000:
        return str(num)
    return "%.1fk" % (num / 1000)


def _get_top_reach_post_stats(post_stats: Iterable[VkPostStats]) -> VkPostStats:
    return sorted(post_stats, key=lambda stats: stats.reach_total)[-1]


def _get_top_likes_post(posts: Iterable[VkPost]) -> VkPost:
    return sorted(posts, key=lambda post: post.likes)[-1]


def _get_top_reposts_post(posts: Iterable[VkPost]) -> VkPost:
    return sorted(posts, key=lambda post: post.reposts)[-1]


def _get_top_comments_post(posts: Iterable[VkPost]) -> VkPost:
    return sorted(posts, key=lambda post: post.comments)[-1]
