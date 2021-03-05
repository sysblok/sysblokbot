from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class VkGroup:
    # Docs: https://vk.com/dev/objects/group
    @classmethod
    def from_dict(cls, data):
        group = cls()
        try:
            group.id = data['id']
            group.name = data['name']
            group.url = f'https://vk.com/{data["screen_name"]}'
            group.members_count = data['members_count']
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
            stats.comments = data['activity']['comments']
            stats.likes = data['activity']['likes']
            stats.subscribed = data['activity']['subscribed']
            stats.unsubscribed = data['activity']['unsubscribed']
            stats.reposts = data['activity']['copies']
            stats.total_reach = data['reach']['reach']
            stats.reach_subscribers = data['reach']['reach_subscribers']
            stats.mobile_reach = data['reach']['mobile_reach']
            stats.views = data['visitors']['views']
            stats.visitors = data['visitors']['visitors']
        except Exception as e:
            logger.error(f"Bad VK stats json {data}: {e}")
        finally:
            return stats


class VkPost:
    # Docs: https://vk.com/dev/objects/post
    @classmethod
    def from_dict(cls, data):
        post = cls()
        try:
            post.id = data['id']
            post.text = data['text']
            post.date = datetime.fromtimestamp(data['date'])
            post.comments = data['comments']['count']
            post.likes = data['likes']['count']
            post.reposts = data['reposts']['count']
        except Exception as e:
            logger.error(f"Bad VK post json {data}: {e}")
        finally:
            return post


class VkPostStats:
    # Docs: https://vk.com/dev/stats.getPostReach
    @classmethod
    def from_dict(cls, data):
        stats = cls()
        try:
            stats.reach_total = data['reach_total']
            stats.reach_subscribers = data['reach_subscribers']
            stats.reach_ads = data['reach_ads']
            stats.reach_viral = data['reach_viral']
            stats.reports = data['report']
            stats.hides = data['hide']
            stats.unsubscribed = data['unsubscribe']
            stats.links = data['links']
        except Exception as e:
            logger.error(f"Bad VK stats json {data}: {e}")
        finally:
            return stats
