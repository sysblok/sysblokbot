import logging
import re
from typing import Callable, List

from sheetfu import Table
from sheetfu.modules.table import Item

from ..app_context import AppContext
from ..roles.roles import Roles
from ..strings import load
from ..tg.sender import pretty_send, TelegramSender
from .base_job import BaseJob

logger = logging.getLogger(__name__)

PHONE_REGEX = r"[\+\-\(\)0-9]{10}?"


class HRGetMembersWithoutTelegramJob(BaseJob):
    @staticmethod
    async def _execute(
        app_context: AppContext,
        send: Callable[[str], None],
        called_from_handler=False,
        *args,
        **kwargs
    ):
        # get Active members
        active_members = app_context.role_manager.get_members_for_role(
            Roles.ACTIVE_MEMBER
        )

        members_without_telegram = [
            f"{user.name}"
            for user in active_members
            if (
                user.telegram is None
                or not user.telegram.strip()
                or user.telegram == "#N/A"
                or re.search(r".*[а-яА-ЯёЁ].*", user.telegram)  # damn this Unicode ё
            )
        ]
        members_with_phone_number = [
            f"{user.name} {user.telegram}"
            for user in active_members
            if user.telegram and re.match(PHONE_REGEX, user.telegram)
        ]
        paragraphs = [
            load(
                "hr_get_members_without_telegram__message",
                members_without_telegram="\n".join(members_without_telegram),
                members_with_phone_number="\n".join(members_with_phone_number),
            ),
        ]
        await pretty_send(
            paragraphs,
            TelegramSender().bot,
            kwargs['chat_id'],
            disable_notification=False,
            disable_web_page_preview=False,
        )
