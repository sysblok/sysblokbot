from datetime import datetime
import logging
from typing import Iterable, List, Set

from ..consts import VK_POST_LINK
from ..sheets.sheets_objects import PostRegistryItem

logger = logging.getLogger(__name__)


class VkGroup:
    # Docs: https://vk.com/dev/objects/group
    @classmethod
    def from_dict(cls, data):
        group = cls()
        try:
            group.id = data["id"]
            group.name = data["name"]
            group.url = f'https://vk.com/{data["screen_name"]}'
            group.members_count = data["members_count"]
        except Exception as e:
            logger.error(f"Bad VK group json {data}: {e}")
        return group


class VkGroupStats:
    # Docs: https://vk.com/dev/stats.get
    # https://vk.com/dev/objects/stats_format
    @classmethod
    def from_dict(cls, data):
        stats = cls()
        try:
            stats.comments = data["activity"]["comments"]
            stats.likes = data["activity"]["likes"]
            stats.subscribed = data["activity"]["subscribed"]
            stats.unsubscribed = data["activity"]["unsubscribed"]
            stats.reposts = data["activity"]["copies"]
            stats.total_reach = data["reach"]["reach"]
            stats.reach_subscribers = data["reach"]["reach_subscribers"]
            stats.mobile_reach = data["reach"]["mobile_reach"]
            stats.views = data["visitors"]["views"]
            stats.visitors = data["visitors"]["visitors"]
        except Exception as e:
            logger.error(f"Bad VK stats json {data}: {e}")
        finally:
            return stats


class VkPost:
    # Docs: https://vk.com/dev/objects/post
    @classmethod
    def from_dict(cls, data, group_id: int, group_alias: str):
        post = cls()
        try:
            post.id = data["id"]
            # if post was postponed, that's the original post id
            post.postponed_id = data.get("postponed_id")
            post.group_id = group_id
            post.url = VK_POST_LINK.format(
                group_id=group_id, post_id=post.id, group_alias=group_alias
            )
            post.postponed_url = (
                None
                if post.postponed_id is None
                else VK_POST_LINK.format(
                    group_id=group_id,
                    post_id=post.postponed_id,
                    group_alias=group_alias,
                )
            )
            # if post is a native article, we use its url for registry instead of post_url
            post.links = post._get_post_links(data.get("attachments", []))
            post.text = data["text"]
            post.date = datetime.fromtimestamp(data["date"])
            post.comments = data["comments"]["count"]
            post.likes = data["likes"]["count"]
            post.reposts = data["reposts"]["count"]
        except Exception as e:
            logger.error(f"Bad VK post json {data}: {e}")
        finally:
            return post

    def get_registry_name(self, post_registry_items: Iterable[PostRegistryItem]) -> str:
        post_urls = self._get_possible_urls()
        for post_registry_item in post_registry_items:
            if post_registry_item.vk_link in post_urls:
                return post_registry_item.name
        return "unknown"

    def _get_post_links(self, attachments: List[dict]) -> List[str]:
        urls = []
        for attachment in attachments:
            if attachment["type"] == "link":
                url = attachment["link"]["url"]
                url = url.replace("//m.vk.com", "//vk.com")
                urls.append(url[:-1] if url.endswith("/") else url)
        return urls

    def _get_possible_urls(self) -> Set[str]:
        """
        Gather possible links to match with post registry vk urls. That might be:
        * actual post url
        * post url at the moment it was set to postponed
        * one of the attachment links (when it's a longread article)
        """
        links = set()
        links.add(self.url)
        links.add(self.postponed_url)
        links.update(self.links)
        return links


class VkPostStats:
    # Docs: https://vk.com/dev/stats.getPostReach
    @classmethod
    def from_dict(cls, data, post: VkPost):
        stats = cls()
        try:
            stats.post = post
            stats.reach_total = data["reach_total"]
            stats.reach_subscribers = data["reach_subscribers"]
            stats.reach_ads = data["reach_ads"]
            stats.reach_viral = data["reach_viral"]
            stats.reports = data["report"]
            stats.hides = data["hide"]
            stats.unsubscribed = data["unsubscribe"]
            stats.links = data["links"]
        except Exception as e:
            logger.error(f"Bad VK stats json {data}: {e}")
        finally:
            return stats
