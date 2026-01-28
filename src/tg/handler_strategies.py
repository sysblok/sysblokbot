from abc import ABC, abstractmethod
from typing import Callable

from .handlers.utils import admin_only, manager_only
from ..jobs.utils import get_job_runnable
from ..app_context import AppContext
from ..tg.sender import TelegramSender


class HandlerFactory(ABC):
    @abstractmethod
    def create(
        self,
        job_name: str,
        app_context: AppContext,
        telegram_sender: TelegramSender,
        config_manager,
    ) -> Callable:
        pass


class AdminBroadcastFactory(HandlerFactory):
    def create(
        self,
        job_name: str,
        app_context: AppContext,
        telegram_sender: TelegramSender,
        config_manager,
    ) -> Callable:
        chat_ids = config_manager.get_job_send_to(job_name)

        def handler(update, tg_context):
            return get_job_runnable(job_name)(
                app_context=app_context,
                send=telegram_sender.create_chat_ids_send(chat_ids),
                called_from_handler=True,
            )

        return admin_only(handler)


class AdminReplyFactory(HandlerFactory):
    def create(
        self,
        job_name: str,
        app_context: AppContext,
        telegram_sender: TelegramSender,
        config_manager,
    ) -> Callable:
        def handler(update, tg_context):
            return get_job_runnable(job_name)(
                app_context=app_context,
                send=telegram_sender.create_reply_send(update),
                called_from_handler=True,
                args=update.message.text.split()[1:],
            )

        return admin_only(handler)


class ManagerReplyFactory(HandlerFactory):
    def create(
        self,
        job_name: str,
        app_context: AppContext,
        telegram_sender: TelegramSender,
        config_manager,
    ) -> Callable:
        def handler(update, tg_context):
            return get_job_runnable(job_name)(
                app_context=app_context,
                send=telegram_sender.create_reply_send(update),
                called_from_handler=True,
                args=update.message.text.split()[1:],
            )

        return manager_only(handler)


class UserReplyFactory(HandlerFactory):
    def create(
        self,
        job_name: str,
        app_context: AppContext,
        telegram_sender: TelegramSender,
        config_manager,
    ) -> Callable:
        def handler(update, tg_context):
            return get_job_runnable(job_name)(
                app_context=app_context,
                send=telegram_sender.create_reply_send(update),
                called_from_handler=True,
                args=update.message.text.split()[1:],
            )

        return handler
