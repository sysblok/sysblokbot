import pytest

import os
from typing import List

from telethon import TelegramClient
from telethon.tl.custom.message import Message


telegram_bot_name = os.environ["TELEGRAM_BOT_NAME"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'command, response_parts',
    (
        ('/start', ('Хэллоу')),
        ('/get_trello_board_state', ('Еженедельная сводка')),
        ('/get_publication_plans', ('Всем чвак')),
        ('/get_editorial_report', ('Всем привет')),
    )
)
async def test_not_failing(client: TelegramClient, command: str, response_parts: List[str]):
    # Create a conversation
    async with client.conversation(telegram_bot_name, timeout=30) as conv:
        await conv.send_message(command)
        resp: Message = await conv.get_response()
        text = resp.raw_text
        for part in response_parts:
            assert part in text
