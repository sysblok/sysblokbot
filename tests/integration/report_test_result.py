import asyncio
import os
import sys

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.custom.message import Message

from conftest import api_id, api_hash, api_session, telegram_bot_name, telegram_chat_id


async def report_test_result(passed: bool, failed_tests: str = ''):
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

    await client.disconnect()
    await client.disconnected


if __name__ == '__main__':
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as failed_tests_file:
            failed_tests = failed_tests_file.readlines()
    else:
        failed_tests = []
    asyncio.run(report_test_result(len(failed_tests) == 0, failed_tests=failed_tests))
