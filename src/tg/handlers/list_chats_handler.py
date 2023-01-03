from typing import Iterable

from ...app_context import AppContext
from ...db.db_client import DBClient
from ...strings import load
from .utils import admin_only, direct_message_only, reply


@admin_only
@direct_message_only
def list_chats(update, tg_context):
    chats = DBClient().get_all_chats()
    app_context = AppContext()
    admins = app_context.admin_chat_ids
    managers = app_context.manager_chat_ids
    curators = []
    groups = []
    for chat in chats:
        if chat.is_curator:
            curators.append(chat.title)
        if chat.id < 0:
            groups.append(chat.title)
    text = load(
        "get_usage_list__message",
        admins=_format_tg_usernames(admins),
        managers=_format_tg_usernames(managers),
        curators=_format_tg_usernames(curators),
        groups="\n".join(
            [
                load("get_usage_list__username_format", username=group)
                for group in sorted(groups)
            ]
        ),
    )
    reply(text, update)


def _format_tg_usernames(usernames: Iterable[str]) -> str:
    formatted_usernames = []
    for username in usernames:
        try:
            # check if username is actually a chat_id, that can happen in admin/moderator list
            int_username = int(username)
            # if it is, we try to determine a username from DB
            try:
                username = f"@{DBClient().get_chat_name(int_username)}"
            except ValueError:
                # if no name was found, just leave it as is
                pass
        except ValueError:
            if not username.startswith("@"):
                username = f"@{username}"
        formatted_usernames.append(
            load("get_usage_list__username_format", username=username)
        )
    return "\n".join(sorted(formatted_usernames))
