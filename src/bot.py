from collections import defaultdict
import logging
import os
from typing import Callable

from telegram.ext import (CallbackQueryHandler, CommandHandler, Filters,
                          MessageHandler, PicklePersistence, Updater)
from telegram.ext.dispatcher import run_async

from .app_context import AppContext
from .config_manager import ConfigManager
from .consts import CommandCategories, USAGE_LOG_LEVEL
from .jobs.utils import get_job_runnable
from .tg import handlers, sender
from .tg.handlers.utils import admin_only, direct_message_only, manager_only

logging.addLevelName(USAGE_LOG_LEVEL, "USAGE")


def usage(self, message, *args, **kws):
    self._log(USAGE_LOG_LEVEL, message, args, **kws)


logging.Logger.usage = usage
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
        self.handlers_info = defaultdict(lambda: defaultdict(dict))
        logger.info('SysBlokBot successfully initialized')

    def init_handlers(self):
        # all command handlers defined here
        # business logic cmds
        self.add_admin_handler(
            'send_trello_board_state',
            CommandCategories.BROADCAST,
            self.admin_broadcast_handler('trello_board_state_job'),
            'рассылка сводки о состоянии доски')
        self.add_manager_handler(
            'get_trello_board_state',
            CommandCategories.SUMMARY,
            self.manager_reply_handler('trello_board_state_job'),
            'получить сводку о состоянии доски')
        self.add_manager_handler(
            'get_main_stats',
            CommandCategories.STATS,
            self.manager_reply_handler('main_stats_job'),
            'получить статистику изменений за неделю'
        )
        self.add_admin_handler(
            'send_publication_plans',
            CommandCategories.BROADCAST,
            self.admin_broadcast_handler('publication_plans_job'),
            'рассылка сводки о публикуемых на неделе постах'
        )
        self.add_manager_handler(
            'get_publication_plans',
            CommandCategories.SUMMARY,
            self.manager_reply_handler('publication_plans_job'),
            'получить сводку о публикуемых на неделе постах'
        )
        self.add_manager_handler(
            'fill_posts_list',
            CommandCategories.REGISTRY,
            direct_message_only(
                self.manager_reply_handler('fill_posts_list_job')
            ),
            'заполнить реестр постов'
        )
        self.add_admin_handler(
            'send_editorial_report',
            CommandCategories.BROADCAST,
            self.admin_broadcast_handler('editorial_report_job'),
            'рассылка сводки по результатам редакторского созвона'
        )
        self.add_admin_handler(
            'hr_acquisition',
            CommandCategories.HR,
            self.manager_reply_handler('hr_acquisition_job'),
            'обработать новые анкеты'
        )
        self.add_manager_handler(
            'get_editorial_report',
            CommandCategories.SUMMARY,
            self.manager_reply_handler('editorial_report_job'),
            'получить сводку по результатам редакторского созвона'
        )
        self.add_manager_handler(
            'create_folders_for_illustrators',
            CommandCategories.REGISTRY,
            self.manager_reply_handler('create_folders_for_illustrators_job'),
            'создать папки для иллюстраторов'
        )
        self.add_manager_handler(
            'get_illustrative_report',
            CommandCategories.SUMMARY,
            self.manager_reply_handler('illustrative_report_job'),
            'получить сводку с папками для иллюстраторов'
        )
        self.add_manager_handler(
            'get_illustrative_report_old',
            CommandCategories.SUMMARY,
            self.manager_reply_handler('illustrative_report_old_job'),
            'получить сводку с папками для иллюстраторов(версия 1.0)'
        )
        self.add_manager_handler(
            'get_tasks_report',
            CommandCategories.SUMMARY,
            direct_message_only(handlers.get_tasks_report),
            'получить список задач из Trello'
        )
        self.add_manager_handler(
            'get_chat_id',
            CommandCategories.REMINDERS,
            handlers.get_chat_id,
            'получить chat_id (свой или группы)'
        )
        self.add_manager_handler(
            'manage_reminders',
            CommandCategories.REMINDERS,
            handlers.manage_reminders,
            'настроить напоминания'
        )
        self.add_manager_handler(
            'get_fb_analytics_report',
            CommandCategories.STATS,
            self.manager_reply_handler('fb_analytics_report_job'),
            'получить статистику facebook страницы за неделю'
        )
        self.add_manager_handler(
            'get_ig_analytics_report',
            CommandCategories.STATS,
            self.manager_reply_handler('ig_analytics_report_job'),
            'получить статистику instagram страницы за неделю'
        )
        self.add_manager_handler(
            'get_vk_analytics_report',
            CommandCategories.STATS,
            self.manager_reply_handler('vk_analytics_report_job'),
            'получить статистику паблика VK за неделю'
        )
        # hidden from /help command for curator enrollment
        self.add_handler(
            'enroll_curator',
            handlers.enroll_curator
        )

        # admin-only technical cmds
        self.add_admin_handler(
            'update_config',
            CommandCategories.CONFIG,
            self.admin_reply_handler('config_updater_job'),
            'обновить конфиг вне расписания'
        )
        self.add_admin_handler(
            'list_jobs',
            CommandCategories.CONFIG,
            handlers.list_jobs,
            'показать статус асинхронных задач'
        )
        self.add_admin_handler(
            'get_usage_list',
            CommandCategories.CONFIG,
            handlers.list_chats,
            'показать места использование бота: пользователи и чаты'
        )
        self.add_admin_handler(
            'set_log_level',
            CommandCategories.LOGGING,
            handlers.set_log_level,
            'изменить уровень логирования (info / debug)'
        )
        self.add_admin_handler(
            'mute_errors',
            CommandCategories.LOGGING,
            handlers.mute_errors,
            'отключить логирование ошибок в телеграм'
        )
        self.add_admin_handler(
            'unmute_errors',
            CommandCategories.LOGGING,
            handlers.unmute_errors,
            'включить логирование ошибок в телеграм'
        )
        self.add_admin_handler(
            'get_config',
            CommandCategories.CONFIG,
            handlers.get_config,
            'получить текущий конфиг (частично или полностью)'
        )
        self.add_admin_handler(
            'set_config',
            CommandCategories.CONFIG,
            handlers.set_config,
            'установить новое значение в конфиге'
        )
        self.add_admin_handler(
            'add_manager',
            CommandCategories.MOST_USED,
            handlers.add_manager,
            'добавить менеджера в список'
        )
        self.add_admin_handler(
            'change_board',
            CommandCategories.CONFIG,
            handlers.change_board,
            'изменить Trello board_id'
        )
        self.add_admin_handler(
            'send_reminders',
            CommandCategories.BROADCAST,
            self.admin_reply_handler('send_reminders_job'),
            'отослать напоминания вне расписания'
        )
        self.add_admin_handler(
            'send_trello_curator_notification',
            CommandCategories.BROADCAST,
            self.admin_reply_handler('trello_board_state_notifications_job'),
            'разослать кураторам состояние их карточек вне расписания'
        )
        self.add_admin_handler(
            'manage_all_reminders',
            CommandCategories.MOST_USED,
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
            CommandCategories.DATA_SYNC,
            self.admin_reply_handler('db_fetch_authors_sheet_job'),
            'обновить таблицу с авторами из Google Sheets'
        )
        self.add_admin_handler(
            'db_fetch_curators_sheet',
            CommandCategories.DATA_SYNC,
            self.admin_reply_handler('db_fetch_curators_sheet_job'),
            'обновить таблицу с кураторами из Google Sheets'
        )
        self.add_admin_handler(
            'db_fetch_strings_sheet',
            CommandCategories.DATA_SYNC,
            self.admin_reply_handler('db_fetch_strings_sheet_job'),
            'обновить таблицу со строками из Google Sheets'
        )

        # general purpose cmds
        self.add_admin_handler(
            'start',
            CommandCategories.MOST_USED,
            handlers.start,
            'начать чат с ботом'
        )
        self.add_admin_handler(
            'help',
            CommandCategories.MOST_USED,
            lambda update, context: handlers.help(update, context, self.handlers_info),
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
        def add_usage_logging(func):
            def wrapper(*args, **kwargs):
                logger.usage(f'Handler {handler_cmd} was called...')
                results = func(*args, **kwargs)
                logger.usage(f'Handler {handler_cmd} finished')
                return results
            return wrapper

        self.dp.add_handler(
            CommandHandler(handler_cmd, run_async(add_usage_logging(handler_func)))
        )

    def add_admin_handler(
            self,
            handler_cmd: str,
            handler_category: CommandCategories,
            handler_func: Callable,
            description: str = ''
    ):
        """
        Adds handler. It will be listed in /help for admins only
        Note: method does not automatically handle invokation restrictions.
        See tg.utils#admin_only
        """
        self.add_handler(handler_cmd, handler_func)
        self.handlers_info[handler_category.value]['admin'][f'/{handler_cmd}'] = description

    def add_manager_handler(
            self,
            handler_cmd: str,
            handler_category: CommandCategories,
            handler_func: Callable,
            description: str = ''
    ):
        """
        Adds handler. It will be listed in /help for admins and managers only
        Note: method does not automatically handle invokation restrictions.
        See tg.utils#manager_only
        """
        self.add_handler(handler_cmd, handler_func)
        self.handlers_info[handler_category.value]['manager'][f'/{handler_cmd}'] = description

    def add_user_handler(
            self,
            handler_cmd: str,
            handler_category: CommandCategories,
            handler_func: Callable,
            description: str = ''
    ):
        """Adds handler. It will be listed in /help for everybody"""
        self.add_handler(handler_cmd, handler_func)
        self.handlers_info[handler_category.value]['user'][f'/{handler_cmd}'] = description

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
