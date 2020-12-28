from enum import Enum
from typing import List, Tuple
from urllib.parse import parse_qs, urlparse
import dateutil.parser as dateparser

import facebook

from datetime import datetime

import pytz

from ..utils.singleton import Singleton


class ReportPeriod(Enum):
    DAY = 'day'
    WEEK = 'week'
    DAYS_28 = 'days_28'


class FacebookClient(Singleton):
    def __init__(self, facebook_config=None):
        self._facebook_config = facebook_config
        self._update_from_config()

    def _update_from_config(self):
        self._api_client = facebook.GraphAPI(self._facebook_config['token'])
        self._page_id = self._facebook_config['page_id']

    def get_new_posts_count(self, since: datetime, until: datetime) -> int:
        """
        Get the number of new posts for the period.
        """
        result = self._api_client.get_connections(
            self._page_id,
            connection_name='published_posts',
            summary='total_count',
            since=since,
            until=until
        )
        return result['summary']['total_count']

    def get_total_reach(
            self, since: datetime, until: datetime, period: ReportPeriod
    ) -> List[Tuple[datetime, int]]:
        """
        Get statistics on the total reach of new posts.
        """
        batches = self._get_all_batches(
            connection_name='insights',
            metric='page_posts_impressions_unique',
            period=period.value,
            since=since,
            until=until
        )
        total_reach = self._get_reach_from_batches(
            batches=batches,
            since=since,
            until=until
        )
        return total_reach

    def get_organic_reach(
            self, since: datetime, until: datetime, period: ReportPeriod
    ) -> List[Tuple[datetime, int]]:
        """
        Get statistics on the organic reach of new posts.
        """
        batches = self._get_all_batches(
            connection_name='insights',
            metric='page_posts_impressions_organic_unique',
            period=period.value,
            since=since,
            until=until
        )
        organic_reach = self._get_reach_from_batches(
            batches=batches,
            since=since,
            until=until
        )
        return organic_reach

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
                        pytz.utc.localize(datetime.fromtimestamp(int(page_since[0]))) > until:
                    break
            else:
                page_until = args.get('until')
                if not page_until or \
                        pytz.utc.localize(datetime.fromtimestamp(int(page_until[0]))) < since:
                    break
            args.pop('access_token', None)
            current_page = self._api_client.get_connections(self._page_id, connection_name, **args)
            result += current_page['data']
        return result

    @staticmethod
    def _get_reach_from_batches(
        batches: List[dict], since: datetime, until: datetime
    ) -> List[Tuple[datetime, int]]:
        reach_by_date = []
        for batch in batches:
            for value_info in batch['values']:
                end_time = dateparser.isoparse(value_info['end_time'])
                if end_time < since or end_time > until:
                    continue
                reach_by_date.append((end_time, value_info['value']))
        return reach_by_date
