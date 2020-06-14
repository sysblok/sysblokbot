import pytest

import os
from typing import List

from telethon import TelegramClient
from telethon.tl.custom.message import Message


telegram_bot_name = os.environ["TELEGRAM_BOT_NAME"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'command, possible_response_parts',
    (
        (
            '/start',
            (('Привет', ))
        ),
        (
            '/get_trello_board_state',
            ((
                'Всем привет!',
                'Не указан автор в карточке',
                'Не указан срок в карточке',
                'Не указан тег рубрики в карточке',
                'Пропущен дедлайн'
            ))
        ),
        (
            '/get_publication_plans',
            ((
                'Всем привет!',
                'Не указан автор в карточке',
                'Не указан срок в карточке',
                'Не указан тег рубрики в карточке',
                'Пропущен дедлайн'
            ))
        ),
        (
            '/get_editorial_report',
            ((
                'Всем привет!',
                'Не указан автор в карточке',
                'Не указан срок в карточке',
                'Не указан тег рубрики в карточке',
                'Пропущен дедлайн'
            ))
        ),
    )
)
async def test_not_failing(client: TelegramClient, command: str,
                           possible_response_parts: List[str]):
    # Create a conversation
    async with client.conversation(telegram_bot_name, timeout=30) as conv:
        await conv.send_message(command)
        resp: Message = await conv.get_response()
        text = resp.raw_text
        assert any([
            all([part in text for part in alternative]) for alternative in possible_response_parts
        ])
