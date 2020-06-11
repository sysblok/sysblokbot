import asyncio
import os
import sys

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.custom.message import Message


# Your API ID, hash and session string here
api_id = int(os.environ["TELEGRAM_APP_ID"])
api_hash = os.environ["TELEGRAM_APP_HASH"]
session_str = os.environ["TELETHON_SESSION"]
telegram_chat_id = int(os.environ["TELEGRAM_ERROR_CHAT_ID"])


async def report_test_result(passed: bool, failed_tests: str=''):
    client = TelegramClient(
        StringSession(session_str), api_id, api_hash,
        sequential_updates=True
    )
    # Connect to the server
    await client.connect()
    # Issue a high level command to start receiving message
    await client.get_me()

    async with client.conversation(telegram_chat_id, timeout=30) as conv:
        if passed:
            message = 'Протестировано, ок на выкладку.'
        else:
            message = f'Тестинг разломан, не катимся.\n{failed_tests}'
        await conv.send_message(message)

    await client.disconnect()
    await client.disconnected


if __name__ == '__main__':
    if len(argv) > 2:
        with open(sys.argv[2]) as failed_tests_file:
            failed_tests = failed_tests_file.read()
    else:
        failed_tests = ''
    asyncio.run(report_test_result(sys.argv[1] == '0', failed_tests=failed_tests)
