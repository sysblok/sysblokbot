import pytest

import asyncio
import os
import time
from typing import List

from telethon import TelegramClient
from telethon.tl.custom.message import Message

from conftest import telegram_bot_name
from pytest_report import PytestReport, PytestTestStatus


async def _test_command(report_state, conversation, command: str, timeout=120):
    test_report = {
        'cmd': command
    }
    start_time = time.time()
    try:
        await conversation.send_message(command)
        resp: Message = await conversation.get_response(timeout=timeout)
        await asyncio.sleep(1)
        test_report['response'] = "\\n".join(resp.raw_text.splitlines())
        assert resp.raw_text
        test_report['status'] = PytestTestStatus.OK
    except BaseException as e:
        test_report['status'] = PytestTestStatus.FAILED
        test_report['exception_class'] = str(e.__class__)
        test_report['exception_message'] = str(e)

        raise
    finally:
        test_report['time_elapsed'] = time.time() - start_time
        report_state.data['tests'].append(test_report)


class Test:
    report_state = PytestReport()
    loop = asyncio.get_event_loop()

    @pytest.mark.parametrize(
        'command',
        (
            '/mute_errors',
        )
    )
    def test_mute(self, conversation, command: str):
        Test.loop.run_until_complete(_test_command(Test.report_state, conversation, command))

    @pytest.mark.parametrize(
        'command',
        (
            '/start',
            '/check_site_health prod',
            '/help',
            '/get_config',
            '/get_config_jobs',
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
            '/get_editorial_board_stats',
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
        try:
            Test.loop.run_until_complete(
                _test_command(Test.report_state, conversation, command, timeout=10)
            )
        except BaseException as e:
            print(f'Swallowed {str(e.__class__)}: {str(e)} on xfail test')

    @pytest.mark.parametrize(
        'command',
        (
            '/unmute_errors',
        )
    )
    def test_unmute(self, conversation, command: str):
        Test.loop.run_until_complete(_test_command(Test.report_state, conversation, command))
