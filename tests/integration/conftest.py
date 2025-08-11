import asyncio
import json
import os
import logging

import pytest
from pytest_report import PytestReport, PytestTestStatus
from telethon import TelegramClient
from telethon.sessions import StringSession

from src.config_manager import ConfigManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

config_manager = ConfigManager("./config.json", "./config_override_integration_tests.json")
config_manager.load_config_with_override()
config = config_manager.get_telegram_config()

api_id = int(config["api_id"])
api_hash = config["api_hash"]
api_session = config["api_session"]
telegram_chat_id = int(config["error_logs_recipients"][0])
telegram_bot_name = config.get("handle", "")

@pytest.fixture(scope="function")
async def conversation():
    """
    Provides a completely fresh Telegram client and conversation for each test function.
    """
    client = TelegramClient(StringSession(api_session), api_id, api_hash, sequential_updates=True)
    await client.connect()
    try:
        bot_entity = await client.get_entity(telegram_bot_name)
        async with client.conversation(bot_entity, timeout=10) as conv:
            yield conv
    finally:
        await client.disconnect()

def pytest_sessionfinish(session, exitstatus):
    passed = exitstatus == 0
    logger.info(f"Pytest session finished with status code: {exitstatus}")
    PytestReport().mark_finish()
    try:
        asyncio.run(report_test_result(passed))
    except Exception:
        logger.error("FATAL: Could not send test report to Telegram.", exc_info=True)


async def report_test_result(passed: bool):
    """
    Sends the test report using a new, completely isolated client.
    """
    report_client = TelegramClient(StringSession(api_session), api_id, api_hash)
    try:
        await report_client.connect()
        report_chat_entity = await report_client.get_entity(telegram_chat_id)
        
        telegram_bot_mention = f"@{telegram_bot_name}"
        
        report_path = "./integration_test_report.txt"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(PytestReport().data, f, indent=4, ensure_ascii=False)

        if passed:
            caption = f"{telegram_bot_mention} протестирован. Все тесты пройдены успешно."
            await report_client.send_file(report_chat_entity, report_path, caption=caption)
        else:
            caption = f"{telegram_bot_mention} разломан. Подробности в файле и в сообщении ниже."
            
            failure_details = "\n".join(
                ["Сломались тесты:"]
                + [
                    f'\n--- FAIL: {test["cmd"]}\n'
                    f'-> {test["exception_class"]}\n'
                    f'-> {test["exception_message"]}'
                    for test in PytestReport().data.get("tests", [])
                    if test.get("status") == PytestTestStatus.FAILED
                ]
            )
            if not failure_details.strip() or len(PytestReport().data.get("tests", [])) == 0:
                 failure_details = "Детали в логах. Вероятно, тесты не были собраны, или ошибка произошла в фикстуре."

            await report_client.send_file(report_chat_entity, report_path, caption=caption)
            if failure_details:
                await report_client.send_message(report_chat_entity, failure_details)
    finally:
        if report_client.is_connected():
            await report_client.disconnect()