import time
from typing import List
import re

import pytest
from telethon.errors import TimeoutError
from telethon.tl.custom.conversation import Conversation

from pytest_report import PytestReport, PytestTestStatus
from src.config_manager import ConfigManager
from src.sheets.sheets_client import GoogleSheetsClient
from src.strings import StringsDBClient, load


def strip_html(text: str) -> str:
    return re.sub("<[^<]+?>", "", text)


def setup_strings_for_test_run():
    ConfigManager.drop_instance()
    StringsDBClient.drop_instance()
    GoogleSheetsClient.drop_instance()

    config_manager = ConfigManager(
        "./config.json", "./config_override_integration_tests.json"
    )
    config_manager.load_config_with_override()

    strings_db_config = config_manager.get_strings_db_config()
    sheets_config = config_manager.get_sheets_config()

    if not (strings_db_config and sheets_config):
        pytest.skip("Skipping test: strings_db_config or sheets_config is missing.")

    strings_db_client = StringsDBClient(strings_db_config)
    sheets_client = GoogleSheetsClient(sheets_config)
    strings_db_client.fetch_strings_sheet(sheets_client)


async def _test_conversation_step(
    conversation: Conversation,
    message_to_send: str,
    expected_response_id: str,
    timeout: int,
):
    await conversation.send_message(message_to_send)
    resp = await conversation.get_response(timeout=timeout)

    expected_html_response = load(expected_response_id)
    expected_plain_text_response = strip_html(expected_html_response)

    actual_response = resp.raw_text.strip()

    assert expected_plain_text_response in actual_response, (
        f"Expected response containing '{expected_plain_text_response}' but got '{actual_response}'"
    )
    return resp


async def _test_command_flow(
    report_state: PytestReport,
    conversation: Conversation,
    command_flow: list,
    timeout=120,
):
    setup_strings_for_test_run()

    command_str = " -> ".join([item[0] for item in command_flow])
    test_report = {"cmd": command_str}
    start_time = time.time()

    try:
        await conversation.send_message("/clean_chat_data")
        await conversation.get_response()

        for message_to_send, expected_response_id in command_flow:
            await _test_conversation_step(
                conversation, message_to_send, expected_response_id, timeout
            )

        test_report["status"] = PytestTestStatus.OK
    except BaseException as e:
        test_report["status"] = PytestTestStatus.FAILED
        test_report["exception_class"] = str(e.__class__)
        test_report["exception_message"] = str(e)
        raise
    finally:
        test_report["time_elapsed"] = time.time() - start_time
        report_state.data["tests"].append(test_report)


class TestTelegramBot:
    report_state = PytestReport()

    @pytest.mark.parametrize(
        "command_flow",
        [
            ([("/start", "start_handler__message")]),
            ([("/help", "help__commands_list")]),
            (
                [
                    ("/manage_reminders", "manage_reminders_handler__no_reminders"),
                    ("1", "manage_reminders_handler__reminder_number_bad"),
                ]
            ),
            (
                [
                    ("/manage_all_reminders", "manage_reminders_handler__no_reminders"),
                ]
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_command_flows(
        self, conversation: Conversation, command_flow: List[tuple]
    ):
        await _test_command_flow(self.report_state, conversation, command_flow)

    @pytest.mark.xfail
    @pytest.mark.parametrize("command", ("/bad_cmd",))
    @pytest.mark.asyncio
    async def test_failing_command(self, conversation: Conversation, command: str):
        try:
            await _test_conversation_step(
                conversation, command, "should_not_matter", timeout=10
            )
        except TimeoutError:
            pass
        except Exception as e:
            pytest.fail(
                f"Test for failing command failed with unexpected exception: {e}"
            )
