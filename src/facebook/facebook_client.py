import logging
from datetime import datetime
from enum import Enum
from typing import List, Tuple
from urllib.parse import parse_qs, urlparse

import dateutil.parser as dateparser
import facebook
import requests

from ..consts import ReportPeriod
from ..utils.singleton import Singleton
from .facebook_objects import FacebookPage

logger = logging.getLogger(__name__)
BASE_URL = 'https://graph.facebook.com'
API_VERSION = 'v19.0'


class FacebookClient(Singleton):
    def __init__(self, facebook_config=None):
        if self.was_initialized():
            return

        self._facebook_config = facebook_config
        self._update_from_config()
        logger.info("FacebookClient successfully initialized")

    def update_config(self, new_facebook_config: dict):
        """To be called after config automatic update"""
        self._facebook_config = new_facebook_config
        self._update_from_config()

    def _update_from_config(self):
        self._api_client = facebook.GraphAPI(self._facebook_config["token"], 7.0)
        self._page_id = self._facebook_config["page_id"]

    def _make_graph_api_call(self, uri: str, params: dict) -> dict:
        params['access_token'] = self._facebook_config["token"]
        response = requests.get(
            '/'.join([BASE_URL, API_VERSION, uri]) + '?' +
            '&'.join(f"{key}={value}" for key, value in params.items()))
        return response.json()

    def get_page(self) -> FacebookPage:
        """
        Get facebook page
        """
        page_dict = self._make_graph_api_call(str(self._page_id), {
            'fields': 'link,name,followers_count,fan_count'
        })
        return FacebookPage.from_dict(page_dict)

    def get_new_posts_count(self, since: datetime, until: datetime) -> int:
        """
        Get the number of new posts for the period.
        """
        result = self._make_graph_api_call(
            str(self._page_id) + '/published_posts',
            {
                'summary': 'total_count',
                'since': int(datetime.timestamp(since)),
                'until': int(datetime.timestamp(until)),
                'limit': 0,
                # 'access_token': f"{self._facebook_config['token']}"
            }
        )
        return result["summary"]["total_count"]

    def get_total_reach(
        self, since: datetime, until: datetime, period: ReportPeriod
    ) -> List[Tuple[datetime, int]]:
        """
        Get statistics on the total reach of new posts.
        """
        batches = self._get_all_batches(
            connection_name="insights",
            metric="page_posts_impressions_unique",
            period=period.value,
            since=since,
            until=until,
        )
        total_reach = self._get_values_from_batches(
            batches=batches, since=since, until=until
        )
        return total_reach

    def get_organic_reach(
        self, since: datetime, until: datetime, period: ReportPeriod
    ) -> List[Tuple[datetime, int]]:
        """
        Get statistics on the organic reach of new posts.
        """
        batches = self._get_all_batches(
            connection_name="insights",
            metric="page_posts_impressions_organic_unique",
            period=period.value,
            since=since,
            until=until,
        )
        organic_reach = self._get_values_from_batches(
            batches=batches, since=since, until=until
        )
        return organic_reach

    def get_new_follower_count(
        self, since: datetime, until: datetime, period: ReportPeriod
    ) -> List[Tuple[datetime, int]]:
        """
        Get the number of new followers for the period.
        """
        batches = self._get_all_batches(
            connection_name="insights",
            metric="page_daily_follows_unique",
            period=period.value,
            since=since,
            until=until,
        )
        result = self._get_values_from_batches(
            batches=batches, since=since, until=until
        )
        return result

    def get_new_fan_count(
        self, since: datetime, until: datetime, period: ReportPeriod
    ) -> List[Tuple[datetime, int]]:
        """
        Get the number of new people who liked the page for the period.
        """
        batches = self._get_all_batches(
            connection_name="insights",
            metric="page_fan_adds_unique",
            period=period.value,
            since=since,
            until=until,
        )
        result = self._get_values_from_batches(
            batches=batches, since=since, until=until
        )
        return result

    def _get_all_batches(
        self, connection_name: str, since: datetime, until: datetime, **args
    ) -> List[dict]:
        result = []
        args["since"] = since
        args["until"] = until
        page = self._api_client.get_connections(self._page_id, connection_name, **args)
        result += page["data"]
        # process next
        result += self._iterate_over_pages(connection_name, since, until, page, True)
        # process previous
        result += self._iterate_over_pages(connection_name, since, until, page, False)
        return result

    def _iterate_over_pages(
        self,
        connection_name: str,
        since: datetime,
        until: datetime,
        previous_page: str,
        go_next: bool,
    ) -> List[dict]:
        result = []
        current_page = previous_page
        while True:
            direction_tag = "previous"
            if go_next:
                direction_tag = "next"
            next = current_page.get("paging", {}).get(direction_tag)
            if not next:
                break
            args = parse_qs(urlparse(next).query)
            if go_next:
                page_since = args.get("since")
                if (
                    not page_since
                    or datetime.fromtimestamp(int(page_since[0]), tz=until.tzinfo)
                    > until
                ):
                    break
            else:
                page_until = args.get("until")
                if (
                    not page_until
                    or datetime.fromtimestamp(int(page_until[0]), tz=since.tzinfo)
                    < since
                ):
                    break
            args.pop("access_token", None)
            current_page = self._api_client.get_connections(
                self._page_id, connection_name, **args
            )
            result += current_page["data"]
        return result

    @staticmethod
    def _get_values_from_batches(
        batches: List[dict], since: datetime, until: datetime
    ) -> List[Tuple[datetime, int]]:
        value_by_date = []
        for batch in batches:
            for value_info in batch["values"]:
                end_time = dateparser.isoparse(value_info["end_time"])
                if end_time < since or end_time > until:
                    continue
                value_by_date.append((end_time, value_info["value"]))
        return value_by_date
