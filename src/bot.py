import logging
import os
from typing import Callable

from telegram.ext import (CallbackQueryHandler, CommandHandler, Filters,
                          MessageHandler, PicklePersistence, Updater)

from .app_context import AppContext
from .config_manager import ConfigManager
from .jobs.utils import get_job_runnable
from .tg import handlers, sender
from .tg.handlers.utils import admin_only, direct_message_only, manager_only

logger = logging.getLogger(__name__)


class SysBlokBot:
    def __init__(self, config_manager: ConfigManager, signal_handler):
        self.config_manager = config_manager
        tg_config = config_manager.get_telegram_config()
        self.updater = Updater(
            tg_config['token'],
            use_context=True,
            user_sig_handler=signal_handler,
            persistence=PicklePersistence(filename='persistent_storage.pickle')
        )
        self.dp = self.updater.dispatcher
        self.app_context = AppContext(config_manager)
        self.telegram_sender = sender.TelegramSender(bot=self.dp.bot, tg_config=tg_config)
        self.user_handlers = {}
        self.admin_handlers = {}
        self.manager_handlers = {}
        logger.info('SysBlokBot successfully initialized')

    def init_handlers(self):
        # all command handlers defined here
        # business logic cmds
        self.add_admin_handler(
            'send_trello_board_state',
            self.admin_broadcast_handler('trello_board_state_job'),
            'рассылка сводки о состоянии доски')
        self.add_manager_handler(
            'get_trello_board_state',
            self.manager_reply_handler('trello_board_state_job'),
            'получить сводку о состоянии доски')
        self.add_manager_handler(
            'get_main_stats',
            self.manager_reply_handler('main_stats_job'),
            'получить статистику изменений за неделю'
        )
        self.add_admin_handler(
            'send_publication_plans',
            self.admin_broadcast_handler('publication_plans_job'),
            'рассылка сводки о публикуемых на неделе постах'
        )
        self.add_manager_handler(
            'get_publication_plans',
            self.manager_reply_handler('publication_plans_job'),
            'получить сводку о публикуемых на неделе постах'
        )
        self.add_manager_handler(
            'fill_posts_list',
            direct_message_only(
                self.manager_reply_handler('fill_posts_list_job')
            ),
            'заполнить реестр постов'
        )
        self.add_admin_handler(
            'send_editorial_report',
            self.admin_broadcast_handler('editorial_report_job'),
            'рассылка сводки по результатам редакторского созвона'
        )
        self.add_manager_handler(
            'get_editorial_report',
            self.manager_reply_handler('editorial_report_job'),
            'получить сводку по результатам редакторского созвона'
        )
        self.add_manager_handler(
            'get_illustrative_report',
            self.manager_reply_handler('illustrative_report_job'),
            'получить сводку для созвона иллюстраторов'
        )
        self.add_manager_handler(
            'get_tasks_report',
            direct_message_only(handlers.get_tasks_report),
            'получить список задач из Trello'
        )
        self.add_manager_handler(
            'get_chat_id',
            handlers.get_chat_id,
            'получить chat_id (свой или группы)'
        )
        self.add_manager_handler(
            'manage_reminders',
            handlers.manage_reminders,
            'настроить напоминания'
        )

        # admin-only technical cmds
        self.add_admin_handler(
            'update_config',
            self.admin_reply_handler('config_updater_job'),
            'обновить конфиг вне расписания'
        )
        self.add_admin_handler(
            'list_jobs',
            handlers.list_jobs,
            'показать статус асинхронных задач'
        )
        self.add_admin_handler(
            'set_log_level',
            handlers.set_log_level,
            'изменить уровень логирования (info / debug)'
        )
        self.add_admin_handler(
            'mute_errors',
            handlers.mute_errors,
            'отключить логирование ошибок в телеграм'
        )
        self.add_admin_handler(
            'unmute_errors',
            handlers.unmute_errors,
            'включить логирование ошибок в телеграм'
        )
        self.add_admin_handler(
            'get_config',
            handlers.get_config,
            'получить текущий конфиг (частично или полностью)'
        )
        self.add_admin_handler(
            'set_config',
            handlers.set_config,
            'установить новое значение в конфиге'
        )
        self.add_admin_handler(
            'add_manager',
            handlers.add_manager,
            'добавить менеджера в список'
        )
        self.add_admin_handler(
            'change_board',
            handlers.change_board,
            'изменить Trello board_id'
        )
        self.add_admin_handler(
            'send_reminders',
            self.admin_reply_handler('send_reminders_job'),
            'отослать напоминания вне расписания'
        )
        self.add_admin_handler(
            'manage_all_reminders',
            handlers.manage_all_reminders,
            'настроить все напоминания'
        )

        # sample handler
        self.add_handler(
            'sample_handler',
            self.admin_reply_handler('sample_job'),
        )

        # admin-only DB cmds
        self.add_admin_handler(
            'db_fetch_authors_sheet',
            self.admin_reply_handler('db_fetch_authors_sheet_job'),
            'обновить таблицу с авторами из Google Sheets'
        )
        self.add_admin_handler(
            'db_fetch_curators_sheet',
            self.admin_reply_handler('db_fetch_curators_sheet_job'),
            'обновить таблицу с кураторами из Google Sheets'
        )
        self.add_admin_handler(
            'db_fetch_strings_sheet',
            self.admin_reply_handler('db_fetch_strings_sheet_job'),
            'обновить таблицу со строками из Google Sheets'
        )

        # general purpose cmds
        self.add_admin_handler('start', handlers.start, 'начать чат с ботом')
        self.add_admin_handler(
            'help',
            lambda update, context: handlers.help(
                update, context, self.admin_handlers, self.manager_handlers, self.user_handlers
            ),
            'получить список доступных команд'
        )

        # on non-command user message
        self.dp.add_handler(MessageHandler(
            Filters.text,
            handlers.handle_user_message)
        )
        self.dp.add_handler(CallbackQueryHandler(handlers.handle_callback_query))
        self.dp.add_handler(MessageHandler(
            Filters.status_update.new_chat_members,
            handlers.handle_new_members
        ))

        # log all errors
        self.dp.add_error_handler(handlers.error)

    def run(self):
        # Start the Bot
        logger.info("Starting polling...")
        self.updater.start_polling()

        # Run the bot until you press Ctrl-C or the process receives SIGINT,
        # SIGTERM or SIGABRT. start_polling() is non-blocking and will
        # stop the bot gracefully.
        self.updater.idle()

    # Methods, adding command handlers and setting them to /help cmd for proper audience
    def add_handler(self, handler_cmd: str, handler_func: Callable):
        """Adds handler silently. Noone will see it in /help output"""
        self.dp.add_handler(CommandHandler(handler_cmd, handler_func))

    def add_admin_handler(self, handler_cmd: str, handler_func: Callable, description: str = ''):
        """
        Adds handler. It will be listed in /help for admins only
        Note: method does not automatically handle invokation restrictions.
        See tg.utils#admin_only
        """
        self.add_handler(handler_cmd, handler_func)
        self.admin_handlers[f'/{handler_cmd}'] = description

    def add_manager_handler(self, handler_cmd: str, handler_func: Callable, description: str = ''):
        """
        Adds handler. It will be listed in /help for admins and managers only
        Note: method does not automatically handle invokation restrictions.
        See tg.utils#manager_only
        """
        self.add_handler(handler_cmd, handler_func)
        self.manager_handlers[f'/{handler_cmd}'] = description

    def add_user_handler(self, handler_cmd: str, handler_func: Callable, description: str = ''):
        """Adds handler. It will be listed in /help for everybody"""
        self.add_handler(handler_cmd, handler_func)
        self.user_handlers[f'/{handler_cmd}'] = description

    # Methods, creating handlers from jobs with proper invocation restrictions
    def admin_broadcast_handler(self, job_name: str) -> Callable:
        """
        Handler that invokes the job as configured in settings, if called by admin.
        Can possibly send message to multiple chat ids, if configured in settings.
        """
        return admin_only(self._create_broadcast_handler(job_name))

    def admin_reply_handler(self, job_name: str) -> Callable:
        """
        Handler that invokes the job as configured in settings, if called by admin.
        Replies to the admin that invoked it.
        """
        return admin_only(self._create_reply_handler(job_name))

    def manager_reply_handler(self, job_name: str) -> Callable:
        """
        Handler that replies if manager invokes it (DM or chat).
        """
        return manager_only(self._create_reply_handler(job_name, ))

    def user_handler(self, job_name: str) -> Callable:
        """
        Handler that replies to any user.
        """
        return self._create_reply_handler(job_name)

    def _create_reply_handler(self, job_name: str) -> Callable:
        """
        Creates a handler that replies to a message of given user.
        """
        return lambda update, tg_context: get_job_runnable(job_name)(
                app_context=self.app_context,
                send=self.telegram_sender.create_reply_send(update),
                called_from_handler=True
            )

    def _create_broadcast_handler(self, job_name: str) -> Callable:
        """
        Creates a handler that sends message to list of chat ids.
        """
        chat_ids = self.config_manager.get_job_send_to(job_name)
        return lambda update, tg_context: get_job_runnable(job_name)(
                app_context=self.app_context,
                send=self.telegram_sender.create_chat_ids_send(chat_ids),
                called_from_handler=True
            )
