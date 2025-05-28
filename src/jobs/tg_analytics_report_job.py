import json
import logging
from datetime import datetime, timezone
from typing import Callable, Tuple

from src.app_context import AppContext
from src.jobs.base_job import BaseJob

from ..strings import load
from ..tg.sender import pretty_send

logger = logging.getLogger(__name__)


class TgAnalyticsReportJob(BaseJob):
    @staticmethod
    def _execute(
        app_context: AppContext, send: Callable[[str], None], called_from_handler=False
    ):
        app_context.tg_client.api_client.loop.run_until_complete(
            app_context.tg_client.api_client.connect()
        )
        stats = app_context.tg_client.api_client.loop.run_until_complete(
            app_context.tg_client.api_client.get_stats(app_context.tg_client.channel)
        )
        entity = app_context.tg_client.api_client.loop.run_until_complete(
            app_context.tg_client.api_client.get_entity(app_context.tg_client.channel)
        )
        app_context.tg_client.api_client.disconnect()
        new_posts_count = len(stats.recent_message_interactions)
        followers_stats = TgAnalyticsReportJob._get_followers_stats(stats)
        message = load(
            "tg_analytics_report_job__text",
            title=entity.title,
            username=entity.username,
            since=stats.period.min_date.strftime("%d.%m"),
            until=stats.period.max_date.strftime("%d.%m"),
            new_posts_count=new_posts_count,
            new_followers_count=int(stats.followers.current),
            joined_followers=followers_stats[0],
            left_followers=followers_stats[1],
            enabled_notifications_total=int(stats.enabled_notifications.part),
            enabled_notifications_part=round(
                stats.enabled_notifications.part
                / stats.enabled_notifications.total
                * 100,
                2,
            ),
            recent_message_views=sum(
                [
                    message_stats.views
                    for message_stats in stats.recent_message_interactions
                ]
            ),
            views_per_post=int(stats.views_per_post.current),
            views_per_post_delta=TgAnalyticsReportJob._format_delta(
                stats.views_per_post.current - stats.views_per_post.previous
            ),
            shares_per_post=int(stats.shares_per_post.current),
            shares_per_post_delta=TgAnalyticsReportJob._format_delta(
                stats.shares_per_post.current - stats.shares_per_post.previous
            ),
        )
        pretty_send([message], send)

    @staticmethod
    def _get_followers_stats(stats) -> Tuple[int, int]:
        """
        Returns count of [Joined, Left] followers
        """
        columns = json.loads(stats.followers_graph.json.data)["columns"]
        data = list(zip(*columns))
        # convert timestamp to datetime
        data = list(
            map(
                lambda x: (datetime.fromtimestamp(x[0] / 1000, timezone.utc),) + x[1:],
                data[1:],
            )
        )
        # filter dates
        data = list(
            filter(
                lambda x: stats.period.min_date <= x[0] <= stats.period.max_date, data
            )
        )
        joined = sum([date[1] for date in data])
        left = sum([date[2] for date in data])
        return [joined, left]

    @staticmethod
    def _format_delta(delta: int) -> str:
        return "{:+.0f}".format(delta)
