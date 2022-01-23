import asyncio
import json
import pytest
import os
import re
from typing import List

from telethon import TelegramClient
from telethon.sessions import StringSession

from src.utils.singleton import Singleton


if os.path.exists('config_override_integration_tests.json'):
    with open('config_override_integration_tests.json') as config_override:
        config = json.load(config_override)['telegram']
else:
    config = json.loads(os.environ['CONFIG_OVERRIDE'])['telegram']

api_id = int(config['api_id'])
api_hash = config['api_hash']
api_session = config["api_session"]
telegram_chat_id = int(config["error_logs_recipients"][0])
telegram_bot_name = config.get("handle", '')


class PytestReportState(Singleton):
    def __init__(self):
        if self.was_initialized():
            return
        self.full_report_strings = []


@pytest.fixture(scope='session')
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


@pytest.fixture(scope='session')
async def conversation(telegram_client):
    async with telegram_client.conversation(telegram_bot_name) as conv:
        yield conv


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
    passed_tests_cnt = len([
        result for result in session.results.values() if result.passed
    ])
    failed_tests = [
        get_test_result_cmd(result) for result in session.results.values() if result.failed
    ]
    print(f'{passed_tests_cnt} tests passed')
    print(f'{len(failed_tests)} tests failed\n{", ".join(failed_tests)}')
    asyncio.run(report_test_result(passed, failed_tests))


def get_test_result_cmd(result) -> str:
    cmd_pattern = r'.*?\[(.*)].*'
    match = re.search(cmd_pattern, result.nodeid)
    if match:
        return match.group(1)
    return result.nodeid


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
        telegram_bot_mention = f'@{telegram_bot_name}' if telegram_bot_name else 'Бот'
        if passed:
            message = f'{telegram_bot_mention} протестирован.'
        else:
            failed_cmds = '\n'.join(
                f'{cmd.strip()}{telegram_bot_mention}'
                for cmd in failed_tests
            )
            message = f'{telegram_bot_mention} разломан.\nСломались команды:\n{failed_cmds}'
        await conv.send_message(message)
        with open('./integration_test_report.txt', 'w') as integration_test_report:
            integration_test_report.write('report\n')
            integration_test_report.write('\n'.join(PytestReportState().full_report_strings))
            integration_test_report.write('/EOF')
        await conv.send_file('./integration_test_report.txt')
    # disconnect
    await client.disconnect()
    await client.disconnected
