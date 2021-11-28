import asyncio
import json
import pytest
import os
from typing import List

from telethon import TelegramClient
from telethon.sessions import StringSession


if os.path.exists('config_override.json'):
    with open('config_override.json') as config_override:
        config = json.load(config_override)['telegram']
else:
    config = json.loads(os.environ['CONFIG_OVERRIDE'])['telegram']

api_id = int(config['api_id'])
api_hash = config['api_hash']
api_session = config["api_session"]
telegram_chat_id = int(config["error_logs_recipients"][0])
telegram_bot_name = config.get("handle", '')


@pytest.fixture
async def telegram_client() -> TelegramClient:
    client = TelegramClient(
        StringSession(api_session), api_id, api_hash,
        sequential_updates=True
    )
    # Connect to the server
    await client.connect()
    # Issue a high level command to start receiving message
    await client.get_me()

    yield client

    await client.disconnect()
    await client.disconnected


def pytest_sessionstart(session):
    session.results = dict()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    result = outcome.get_result()

    if result.when == 'call':
        item.session.results[item] = result


def pytest_sessionfinish(session, exitstatus):
    passed = exitstatus == pytest.ExitCode.OK
    print('run status code:', exitstatus)
    passed_tests = [
        result.longreprtext for result in session.results.values() if result.passed
    ]
    failed_tests = [
        result.longreprtext for result in session.results.values() if result.failed
    ]
    print(f'{len(passed_tests)} passed\n{", ".join(failed_tests)}\n')
    print(f'{len(failed_tests)} failed\n{", ".join(failed_tests)}\n')
    asyncio.run(report_test_result(passed, failed_tests))


async def report_test_result(passed: bool, failed_tests: List[str] = []):
    client = TelegramClient(
        StringSession(api_session), api_id, api_hash,
        sequential_updates=True
    )
    # Connect to the server
    await client.connect()
    # Issue a high level command to start receiving message
    await client.get_me()
    async with client.conversation(telegram_chat_id, timeout=30) as conv:
        if passed:
            message = f'@{telegram_bot_name} протестирован.'
        else:
            failed_cmds = '\n'.join(
                f'{cmd.strip()}@{telegram_bot_name}'
                for cmd in failed_tests
            )
            message = f'@{telegram_bot_name} разломан.\nСломались команды:\n{failed_cmds}'
        await conv.send_message(message)
    # disconnect
    await client.disconnect()
    await client.disconnected
