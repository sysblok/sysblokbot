from collections import defaultdict

from .app_context import AppContext


def load(string_id: str, **kwargs) -> str:
    app_context = AppContext()
    return app_context.db_client.get_string(string_id).format_map(
        defaultdict(lambda: '?', kwargs)
    ).strip()
