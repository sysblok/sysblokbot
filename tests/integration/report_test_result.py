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


async def report_test_result(passed: bool):
    client = TelegramClient(
        StringSession(session_str), api_id, api_hash,
        sequential_updates=True
    )
    # Connect to the server
    await client.connect()
    # Issue a high level command to start receiving message
    await client.get_me()

    async with client.conversation(telegram_chat_id, timeout=30) as conv:
        message = 'Протестировано, ок на выкладку.' if passed else 'Тестинг разломан, не катимся.'
        await conv.send_message(message)

    await client.disconnect()
    await client.disconnected


if __name__ == '__main__':
    asyncio.run(report_test_result(sys.argv[1] == '0'))
