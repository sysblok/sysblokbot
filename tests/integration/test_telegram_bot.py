import asyncio
import nest_asyncio
import time
from typing import List, Dict
import re
import os

import pytest
from telethon.tl.custom.message import Message
from telethon.errors import TimeoutError
from telethon.tl.custom.conversation import Conversation
from telethon import events

from pytest_report import PytestReport, PytestTestStatus
from src.config_manager import ConfigManager
from src.sheets.sheets_client import GoogleSheetsClient
from src.strings import StringsDBClient, load

def strip_html(text: str) -> str:
    """A simple helper to remove HTML tags for plain text comparison."""
    return re.sub('<[^<]+?>', '', text)

def setup_strings_for_test_run():
    """Initializes and populates the string DB right before a test."""
    ConfigManager.drop_instance()
    StringsDBClient.drop_instance()
    GoogleSheetsClient.drop_instance()

    config_manager = ConfigManager("./config.json", "./config_override_integration_tests.json")
    config_manager.load_config_with_override()
    
    strings_db_config = config_manager.get_strings_db_config()
    sheets_config = config_manager.get_sheets_config()

    if not (strings_db_config and sheets_config):
        pytest.skip("Skipping test: strings_db_config or sheets_config is missing.")

    strings_db_client = StringsDBClient(strings_db_config)
    sheets_client = GoogleSheetsClient(sheets_config)
    strings_db_client.fetch_strings_sheet(sheets_client)

async def _test_command_flow(report_state: PytestReport, conversation: Conversation, command_flow: List[Dict], timeout=120):
    """
    Tests a sequence of user actions using the dictionary-based schema.
    """
    setup_strings_for_test_run()

    command_str = " -> ".join([f"{step['type']}: '{step['input']}'" for step in command_flow])
    test_report = {"cmd": command_str}
    start_time = time.time()
    
    last_bot_message: Message = None

    try:
        await conversation.send_message("/clean_chat_data")
        await conversation.get_response()

        for step in command_flow:
            action_type = step['type']
            action_input = step['input']
            expected_response_id = step['expected']

            if action_type == 'message':
                await conversation.send_message(action_input)
                last_bot_message = await conversation.get_response(timeout=timeout)
            
            elif action_type == 'click':
                if not last_bot_message or not last_bot_message.buttons:
                    pytest.fail(f"Action failed: Tried to click '{action_input}', but the last bot message had no buttons.")
                
                new_message_task = asyncio.create_task(
                    conversation.wait_event(events.NewMessage(incoming=True), timeout=timeout)
                )
                edited_message_task = asyncio.create_task(
                    conversation.wait_event(
                        events.MessageEdited(incoming=True, func=lambda e: e.message.id == last_bot_message.id),
                        timeout=timeout
                    )
                )

                await last_bot_message.click(text=action_input)

                done, pending = await asyncio.wait([new_message_task, edited_message_task], return_when=asyncio.FIRST_COMPLETED)
                for task in pending:
                    task.cancel()

                event = done.pop().result()
                last_bot_message = event.message
            else:
                pytest.fail(f"Unknown action type in test flow: '{action_type}'")

            # Assertion logic for both action types
            expected_html = load(expected_response_id)
            expected_plain = strip_html(expected_html)
            actual_plain = last_bot_message.raw_text.strip()

            assert expected_plain in actual_plain, \
                f"Action {step} failed. Expected response containing '{expected_plain}' but got '{actual_plain}'"

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
            ([{'type': 'message', 'input': "/start", 'expected': "start_handler__message"}]),
            ([{'type': 'message', 'input': "/help", 'expected': "help__commands_list"}]),
            (
                [
                    {'type': 'message', 'input': "/manage_reminders", 'expected': "manage_reminders_handler__no_reminders"},
                    {'type': 'click', 'input': "Создать новое", 'expected': "manager_reminders_handler__enter_chat_id"},
                ]
            ),
            (
                [
                    {'type': 'message', 'input': "/manage_all_reminders", 'expected': "manage_reminders_handler__no_reminders"},
                ]
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_command_flows(self, conversation: Conversation, command_flow: List[Dict]):
        await _test_command_flow(self.report_state, conversation, command_flow)

    @pytest.mark.xfail
    @pytest.mark.parametrize("command", ("/bad_cmd",))
    @pytest.mark.asyncio
    async def test_failing_command(self, conversation: Conversation, command: str):
        try:
            await conversation.send_message(command)
            await conversation.get_response(timeout=10)
        except TimeoutError:
            pass
        except Exception as e:
            pytest.fail(f"Test for failing command failed with unexpected exception: {e}")