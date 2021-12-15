import pytest

import os
from typing import List

from telethon import TelegramClient
from telethon.tl.custom.message import Message

from conftest import telegram_bot_name


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'command',
    (
        '/start',
        '/get_ig_analytics_report',
        '/get_trello_board_state',
        '/get_publication_plans',
        '/get_editorial_report',
    )
)
async def test_not_failing(telegram_client: TelegramClient, command: str):
    try:
        async with telegram_client.conversation(telegram_bot_name, timeout=120) as conv:
            await conv.send_message(command)
            resp: Message = await conv.get_response()
            assert resp.raw_text
    except ValueError:
        assert not "Please add your bot name to config_override['telegram']['handle'] field"


@pytest.mark.asyncio
@pytest.mark.xfail
@pytest.mark.parametrize(
    'command',
    (
        '/bad_cmd',
    )
)
async def test_failing(telegram_client: TelegramClient, command: str):
    async with telegram_client.conversation(telegram_bot_name, timeout=10) as conv:
        await conv.send_message(command)
        resp: Message = await conv.get_response()
        assert resp.raw_text is None
