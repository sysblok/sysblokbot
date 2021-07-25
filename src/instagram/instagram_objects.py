from datetime import datetime
import logging

logger = logging.getLogger(__name__)


TIMESTAMP_FORMAT = '%Y-%m-%dT%H:%M:%S%z'


class InstagramPage:
    # https://developers.facebook.com/docs/instagram-api/reference/ig-user
    def __init__(self):
        self.id = None
        self.name = None
        self.username = None

        self._ok = True

    @classmethod
    def from_dict(cls, data):
        page = cls()
        try:
            page.id = data['id']
            page.name = data['name']
            page.username = data['username']
        except Exception as e:
            page._ok = False
            logger.error(f"Bad Instagram page json {data}: {e}")
        return page

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'username': self.username,
        }


class InstagramMedia:
    # https://developers.facebook.com/docs/instagram-api/reference/ig-media
    def __init__(self):
        self.id = None
        self.ig_id = None
        self.media_url = None
        self.timestamp = None
        self.media_type = None  # Can be CAROUSEL_ALBUM, IMAGE, or VIDEO.
        # media_product_type doesn't work, strange. Wants API > v10.0..
        self.media_product_type = None  # Can be AD, FEED, IGTV, or STORY.
        self.like_count = None
        self.comments_count = None

        self._ok = True

    @classmethod
    def from_dict(cls, data):
        page = cls()
        try:
            page.id = data['id']
            page.ig_id = data['ig_id']
            # Might be omitted in response, e.g. for copyrighted items
            page.media_url = data.get('media_url', '')
            page.timestamp = datetime.strptime(data['timestamp'], TIMESTAMP_FORMAT)
            page.media_type = data['media_type']
            # page.media_product_type = data['media_product_type']
            page.like_count = data['like_count']
            page.comments_count = data['comments_count']
        except Exception as e:
            page._ok = False
            logger.error(f"Bad Instagram media json {data}: {e}")
        return page

    def to_dict(self):
        return {
            'id': self.id,
            'ig_id': self.ig_id,
            'media_url': self.media_url,
            'timestamp': self.timestamp,
            'media_type': self.media_type,
            # 'media_product_type': self.media_product_type,
            'like_count': self.like_count,
            'comments_count': self.comments_count,
        }
