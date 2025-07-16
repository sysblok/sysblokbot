import asyncio
import time

import nest_asyncio
import pytest
from pytest_report import PytestReport, PytestTestStatus
from telethon.tl.custom.message import Message


async def _test_command(report_state, conversation, command: str, timeout=120):
    test_report = {"cmd": command}
    start_time = time.time()
    try:
        await conversation.send_message(command)
        resp: Message = await conversation.get_response(timeout=timeout)
        await asyncio.sleep(1)
        test_report["response"] = "\\n".join(resp.raw_text.splitlines())
        assert resp.raw_text
        test_report["status"] = PytestTestStatus.OK
    except BaseException as e:
        test_report["status"] = PytestTestStatus.FAILED
        test_report["exception_class"] = str(e.__class__)
        test_report["exception_message"] = str(e)

        raise
    finally:
        test_report["time_elapsed"] = time.time() - start_time
        report_state.data["tests"].append(test_report)


class Test:
    report_state = PytestReport()
    loop = asyncio.get_event_loop()
    nest_asyncio.apply(loop)

    @pytest.mark.parametrize("command", ("/mute_errors",))
    def test_mute(self, conversation, command: str):
        Test.loop.run_until_complete(
            _test_command(Test.report_state, conversation, command)
        )

    @pytest.mark.parametrize(
        "command",
        (
            "/start",
            "/help",
        ),
    )
    def test_start_help(self, conversation, command: str):
        Test.loop.run_until_complete(
            _test_command(Test.report_state, conversation, command)
        )

    @pytest.mark.parametrize(
        "command",
        (
            "/get_sheets_report",
            "/get_tasks_report_focalboard",
        ),
    )
    def test_not_failing_reports(self, conversation, command: str):
        Test.loop.run_until_complete(
            _test_command(Test.report_state, conversation, command)
        )

    @pytest.mark.parametrize(
        "command",
        ("/get_tg_analytics_report",),
    )
    def test_not_failing_analytics(self, conversation, command: str):
        Test.loop.run_until_complete(
            _test_command(Test.report_state, conversation, command)
        )

    @pytest.mark.parametrize(
        "command",
        (
            "/manage_reminders",
            "/manage_all_reminders",
        ),
    )
    def test_reminder(self, conversation, command: str):
        Test.loop.run_until_complete(
            _test_command(Test.report_state, conversation, command)
        )
