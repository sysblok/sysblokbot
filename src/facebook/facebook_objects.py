import logging

logger = logging.getLogger(__name__)


class FacebookPage:
    def __init__(self):
        self.id = None
        self.name = None
        self.link = None
        self.followers_count = None
        self.fan_count = None

        self._ok = True

    @classmethod
    def from_dict(cls, data):
        page = cls()
        try:
            page.id = data["id"]
            page.name = data["name"]
            page.link = data["link"]
            page.followers_count = data["followers_count"]
            page.fan_count = data["fan_count"]

        except Exception as e:
            page._ok = False
            logger.error(f"Bad Facebook page json {data}: {e}")
        return page

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "link": self.link,
            "followers_count": self.followers_count,
            "fan_count": self.fan_count,
        }
