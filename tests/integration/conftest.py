import asyncio
import json
import os

import pytest
from pytest_report import PytestReport, PytestTestStatus
from telethon import TelegramClient
from telethon.sessions import StringSession

from src.utils.singleton import Singleton

if os.path.exists("config_override_integration_tests.json"):
    with open("config_override_integration_tests.json") as config_override:
        config = json.load(config_override)["telegram"]
else:
    config = json.loads(os.environ["CONFIG_OVERRIDE"])["telegram"]

api_id = int(config["api_id"])
api_hash = config["api_hash"]
api_session = config["api_session"]
telegram_chat_id = int(config["error_logs_recipients"][0])
telegram_bot_name = config.get("handle", "")


class WrappedTelegramClientAsync(Singleton):
    def __init__(self):
        self.client = TelegramClient(
            StringSession(api_session), api_id, api_hash, sequential_updates=True
        )

    async def __aenter__(self):
        await self.client.connect()
        await self.client.get_me()
        return self.client

    async def __aexit__(self, exc_t, exc_v, exc_tb):
        await self.client.disconnect()
        await self.client.disconnected


@pytest.fixture(scope="session")
async def telegram_client() -> TelegramClient:
    async with WrappedTelegramClientAsync() as client:
        yield client


@pytest.fixture(scope="session")
async def conversation(telegram_client):
    async with telegram_client.conversation(telegram_bot_name) as conv:
        yield conv


def pytest_sessionfinish(session, exitstatus):
    passed = exitstatus == pytest.ExitCode.OK
    print("\nrun status code:", exitstatus)
    PytestReport().mark_finish()
    asyncio.run(report_test_result(passed))


async def report_test_result(passed: bool):
    async with WrappedTelegramClientAsync() as client:
        async with client.conversation(telegram_chat_id, timeout=30) as conv:
            telegram_bot_mention = (
                f"@{telegram_bot_name}" if telegram_bot_name else "Бот"
            )
            if passed:
                message = f"{telegram_bot_mention} протестирован."
            else:
                message = "\n".join(
                    [f"{telegram_bot_mention} разломан.", "Сломались команды:"]
                    + [
                        f"{test['cmd']}{telegram_bot_mention}\n"
                        f"{test['exception_class']}\n{test['exception_message']}"
                        for test in PytestReport().data["tests"]
                        if test["status"] == PytestTestStatus.FAILED
                    ]
                )
            with open("./integration_test_report.txt", "w") as integration_test_report:
                json.dump(
                    PytestReport().data,
                    integration_test_report,
                    indent=4,
                    sort_keys=True,
                    ensure_ascii=False,
                )
            await conv.send_file("./integration_test_report.txt", caption=message)
