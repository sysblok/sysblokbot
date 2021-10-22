import logging
from enum import Enum
from typing import List, Tuple
from urllib.parse import parse_qs, urlparse
import dateutil.parser as dateparser

import facebook

from datetime import datetime

from .instagram_objects import InstagramPage, InstagramMedia
from ..consts import ReportPeriod
from ..utils.singleton import Singleton

logger = logging.getLogger(__name__)


class InstagramClient(Singleton):
    def __init__(self, facebook_config=None):
        if self.was_initialized():
            return

        self._facebook_config = facebook_config
        self._update_from_config()
        logger.info('InstagramClient successfully initialized')

    def update_config(self, new_facebook_config: dict):
        """To be called after config automatic update"""
        self._facebook_config = new_facebook_config
        self._update_from_config()

    def _update_from_config(self):
        self._api_client = facebook.GraphAPI(self._facebook_config['token'], 10.0)
        self._page_id = self._facebook_config['page_id']

    def get_page(self) -> InstagramPage:
        """
        Get the Instagram page
        """
        page_dict = self._api_client.get_object(self._page_id, fields='username,name')
        return InstagramPage.from_dict(page_dict)

    def _get_all_posts(self) -> List[InstagramMedia]:
        """
        Get all media (posts, stories, IGTV etc) on the page
        """
        media_dicts = self._api_client.get_all_connections(
            self._page_id, 'media',
            fields=(
                'id,ig_id,media_url,timestamp,media_type,like_count,comments_count'
            )
        )
        return [InstagramMedia.from_dict(media_dict) for media_dict in media_dicts]

    def _get_new_posts(self, since: datetime, until: datetime) -> List[InstagramMedia]:
        """
        Get all media (posts, stories, IGTV etc) for the period.
        """
        all_media = self._get_all_posts()
        return [
            media for media in all_media
            if media.timestamp > since and media.timestamp < until
        ]

    def get_new_posts_count(self, since: datetime, until: datetime) -> int:
        """
        Get the number of new posts for the period.
        """
        return len(self._get_new_posts(since, until))

    def get_total_subscribers(self) -> int:
        """
        Get the total number of subscribers.
        """
        return self._api_client.get_object(
            self._page_id, fields='followers_count'
        )['followers_count']

    def get_new_subscribers(self, since: datetime, until: datetime) -> dict:
        """
        Get the number of new subscribers for the period.
        """
        new_followers = self._api_client.get_connections(
            self._page_id, 'insights',
            since=since,
            until=until,
            metric='follower_count',
            period='day'
        )
        return new_followers

    def get_reach(self, since: datetime, until: datetime) -> dict:
        """
        Get the total reach for the period.
        """
        return self._api_client.get_connections(
            self._page_id, 'insights',
            since=since,
            until=until,
            metric='reach',
            period='day'
        )

    def get_likes_count(self, since: datetime, until: datetime) -> int:
        """
        Get the total number of likes on a profile over a period.
        """
        posts = self._get_new_posts(since, until)
        return sum(map(lambda post: post.like_count, posts))

    def get_likes_avg(self, since: datetime, until: datetime) -> int:
        """
        Get the average number of likes on recent posts.
        """
        posts = self._get_new_posts(since, until)
        return int(sum(map(lambda post: post.like_count, posts)) / len(posts))

    def get_comments_count(self, since: datetime, until: datetime) -> int:
        """
        Get the total number of comments on a profile over a period.
        """
        posts = self._get_new_posts(since, until)
        return sum(map(lambda post: post.comments_count, posts))

    def get_saves_count(self, since: datetime, until: datetime) -> int:
        """
        Get the total number of saves on a profile over a period.
        """
        saves = 0
        posts = self._get_new_posts(since, until)
        for post in posts:
            insights = self._get_post_insights(post.id)
            saves_insights = [
                insight for insight in insights['data']
                if insight.get('name', None) == 'saved'
            ][0]
            saves += saves_insights['values'][0]['value']
        return saves

    def _get_post_insights(self, post_id: str) -> dict:
        """
        Get all insights for the post.
        https://developers.facebook.com/docs/instagram-api/reference/ig-media/insights
        """
        return self._api_client.get_connections(
            post_id, "insights",
            metric="engagement,impressions,reach,saved"
        )

    def _get_all_batches(
            self, connection_name: str, since: datetime, until: datetime, **args
    ) -> List[dict]:
        result = []
        args['since'] = since
        args['until'] = until
        page = self._api_client.get_connections(self._page_id, connection_name, **args)
        result += page['data']
        # process next
        result += self._iterate_over_pages(connection_name, since, until, page, True)
        # process previous
        result += self._iterate_over_pages(connection_name, since, until, page, False)
        return result

    def _iterate_over_pages(
            self, connection_name: str, since: datetime, until: datetime,
            previous_page: str, go_next: bool
    ) -> List[dict]:
        result = []
        current_page = previous_page
        while True:
            direction_tag = 'previous'
            if go_next:
                direction_tag = 'next'
            next = current_page.get('paging', {}).get(direction_tag)
            if not next:
                break
            args = parse_qs(urlparse(next).query)
            if go_next:
                page_since = args.get('since')
                if not page_since or \
                        datetime.fromtimestamp(int(page_since[0]), tz=until.tzinfo) > until:
                    break
            else:
                page_until = args.get('until')
                if not page_until or \
                        datetime.fromtimestamp(int(page_until[0]), tz=since.tzinfo) < since:
                    break
            args.pop('access_token', None)
            current_page = self._api_client.get_connections(self._page_id, connection_name, **args)
            result += current_page['data']
        return result

    @staticmethod
    def _get_values_from_batches(
        batches: List[dict], since: datetime, until: datetime
    ) -> List[Tuple[datetime, int]]:
        value_by_date = []
        for batch in batches:
            for value_info in batch['values']:
                end_time = dateparser.isoparse(value_info['end_time'])
                if end_time < since or end_time > until:
                    continue
                value_by_date.append((end_time, value_info['value']))
        return value_by_date
