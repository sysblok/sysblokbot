from collections import defaultdict

from .db.db_client import DBClient


def load(string_id: str, **kwargs) -> str:
    db_client = DBClient()
    return db_client.get_string(string_id).format_map(defaultdict(lambda: '?', kwargs)).strip()
