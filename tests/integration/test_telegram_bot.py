import pytest

import asyncio
import os
from typing import List

from telethon import TelegramClient
from telethon.tl.custom.message import Message

from conftest import telegram_bot_name, PytestReportState


async def _test_command(report_state, conversation, command: str, timeout=120):
    try:
        await conversation.send_message(command)
        resp: Message = await conversation.get_response(timeout=timeout)
        report_state.full_report_strings += [
            '>>>',
            command,
            '<<<',
            resp.raw_text,
            '\n'
        ]
        await asyncio.sleep(1)
        assert resp.raw_text
    except ValueError:
        assert not "Please add your bot name to config_override['telegram']['handle'] field"


class Test:
    report_state = PytestReportState()
    loop = asyncio.get_event_loop()

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
    def test_not_failing_health(self, conversation, command: str):
        Test.loop.run_until_complete(_test_command(Test.report_state, conversation, command))

    @pytest.mark.parametrize(
        'command',
        (
            '/db_fetch_authors_sheet',
            '/db_fetch_curators_sheet',
            '/db_fetch_strings_sheet',
            '/db_fetch_team_sheet',
        )
    )
    def test_not_failing_db_update(self, conversation, command: str):
        Test.loop.run_until_complete(_test_command(Test.report_state, conversation, command))

    @pytest.mark.parametrize(
        'command',
        (
            '/get_articles_arts',
            '/get_articles_rubric arts',
            '/get_editorial_report',
            '/get_illustrative_report_columns',
            '/get_illustrative_report_members',
            '/get_publication_plans',
            '/get_tasks_report',
            '/get_trello_board_state'
        )
    )
    def test_not_failing_reports(self, conversation, command: str):
        Test.loop.run_until_complete(_test_command(Test.report_state, conversation, command))

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
    def test_not_failing_analytics(self, conversation, command: str):
        Test.loop.run_until_complete(_test_command(Test.report_state, conversation, command))

    @pytest.mark.parametrize(
        'command',
        (
            '/create_folders_for_illustrators',
            '/fill_posts_list',
        )
    )
    def test_not_failing_fill_registers(self, conversation, command: str):
        Test.loop.run_until_complete(_test_command(Test.report_state, conversation, command))

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
    def test_not_failing_hr(self, conversation, command: str):
        Test.loop.run_until_complete(
            _test_command(Test.report_state, conversation, command, timeout=180)
        )

    @pytest.mark.parametrize(
        'command',
        (
            '/get_chat_data',
            '/clean_chat_data',
        )
    )
    def test_clean_chat_data(self, conversation, command: str):
        Test.loop.run_until_complete(
            _test_command(Test.report_state, conversation, command, timeout=120)
        )

    @pytest.mark.xfail
    @pytest.mark.parametrize(
        'command',
        (
            '/bad_cmd',
        )
    )
    def test_failing(self, conversation, command: str):
        Test.loop.run_until_complete(
            _test_command(Test.report_state, conversation, command, timeout=10)
        )
