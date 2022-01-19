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
        '/check_site_health',
        '/help',
        '/get_config',
        '/list_jobs',
        '/get_chat_id',
    )
)
async def test_not_failing_health(telegram_client: TelegramClient, command: str):
    try:
        async with telegram_client.conversation(telegram_bot_name, timeout=120) as conv:
            await conv.send_message(command)
            resp: Message = await conv.get_response()
            assert resp.raw_text
    except ValueError:
        assert not "Please add your bot name to config_override['telegram']['handle'] field"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'command',
    (
        '/db_fetch_authors_sheet',
        '/db_fetch_curators_sheet',
        '/db_fetch_strings_sheet',
        '/db_fetch_team_sheet',
    )
)
async def test_not_failing_db_update(telegram_client: TelegramClient, command: str):
    try:
        async with telegram_client.conversation(telegram_bot_name, timeout=120) as conv:
            await conv.send_message(command)
            resp: Message = await conv.get_response()
            assert resp.raw_text
    except ValueError:
        assert not "Please add your bot name to config_override['telegram']['handle'] field"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'command',
    (
        '/get_articles_arts',
        '/get_articles_rubric',
        '/get_editorial_report',
        '/get_illustrative_report_columns',
        '/get_illustrative_report_members',
        '/get_publication_plans',
        '/get_report_from_sheet',
        '/get_tasks_report',
        '/get_trello_board_state'
    )
)
async def test_not_failing_reports(telegram_client: TelegramClient, command: str):
    try:
        async with telegram_client.conversation(telegram_bot_name, timeout=120) as conv:
            await conv.send_message(command)
            resp: Message = await conv.get_response()
            assert resp.raw_text
    except ValueError:
        assert not "Please add your bot name to config_override['telegram']['handle'] field"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'command',
    (
        '/get_fb_analytics_report',
        '/get_ig_analytics_report',
        '/get_main_stats',
        '/get_tg_analytics_report',
        '/get_vk_analytics_report',
    )
)
async def test_not_failing_analytics(telegram_client: TelegramClient, command: str):
    try:
        async with telegram_client.conversation(telegram_bot_name, timeout=120) as conv:
            await conv.send_message(command)
            resp: Message = await conv.get_response()
            assert resp.raw_text
    except ValueError:
        assert not "Please add your bot name to config_override['telegram']['handle'] field"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'command',
    (
        '/create_folders_for_illustrators',
        '/fill_posts_list',
    )
)
async def test_not_failing_fill_registers(telegram_client: TelegramClient, command: str):
    try:
        async with telegram_client.conversation(telegram_bot_name, timeout=120) as conv:
            await conv.send_message(command)
            resp: Message = await conv.get_response()
            assert resp.raw_text
    except ValueError:
        assert not "Please add your bot name to config_override['telegram']['handle'] field"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'command',
    (
        '/check_chat_consistency',
        '/check_chat_consistency_frozen',
        '/check_trello_consistency',
        '/check_trello_consistency_frozen',
        '/get_hr_status',
    )
)
async def test_not_failing_hr(telegram_client: TelegramClient, command: str):
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
