import logging
from datetime import datetime
from typing import Iterable, List

import vk_api

from ..consts import ReportPeriod
from ..utils.singleton import Singleton
from .vk_objects import VkGroup, VkGroupStats, VkPost, VkPostStats

logger = logging.getLogger(__name__)


class VkClient(Singleton):
    def __init__(self, vk_config=None):
        if self.was_initialized():
            return

        self._vk_config = vk_config
        self._update_from_config()
        logger.info("VkClient successfully initialized")

    def update_config(self, new_vk_config: dict):
        """To be called after config automatic update"""
        self._vk_config = new_vk_config
        self._update_from_config()

    def _update_from_config(self):
        api_session = vk_api.VkApi(token=self._vk_config["group_admin_token"])
        self._api_client = api_session.get_api()
        self._group_alias = self._vk_config["group_alias"]

    def get_group_info(self) -> VkGroup:
        return VkGroup.from_dict(
            self._api_client.groups.getById(
                group_id=self._group_alias, fields="members_count"
            )[0]
        )

    def get_group_stats(self, group_id: int, period: ReportPeriod) -> VkGroupStats:
        return VkGroupStats.from_dict(
            self._api_client.stats.get(
                group_id=group_id, interval=period.value, intervals_count=1
            )[0]
        )

    def get_post_stats(
        self, group_id: int, posts: Iterable[VkPost], period: ReportPeriod
    ) -> List[VkPostStats]:
        return [
            VkPostStats.from_dict(data, post)
            for post, data in zip(
                posts,
                self._api_client.stats.getPostReach(
                    owner_id=-group_id, post_ids=[post.id for post in posts]
                ),
            )
        ]

    def get_posts(self, group_id, count=100) -> List[VkPost]:
        return [
            VkPost.from_dict(post_data, group_id, self._group_alias)
            for post_data in self._api_client.wall.get(
                domain=self._group_alias, count=count
            )["items"]
        ]

    def get_posts_per_period(
        self, posts: Iterable[VkPost], since: datetime, until: datetime
    ) -> List[VkPost]:
        assert since <= until
        return [post for post in posts if since <= post.date <= until]
