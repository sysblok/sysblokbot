import logging
import os
from collections import defaultdict
from typing import Callable

from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    filters,
    MessageHandler,
    PicklePersistence,
    Updater,
)

from .app_context import AppContext
from .config_manager import ConfigManager
from .consts import (
    APP_SOURCE,
    COMMIT_HASH,
    COMMIT_URL,
    USAGE_LOG_LEVEL,
    CommandCategories,
)
from .jobs.utils import get_job_runnable
from .tg import handlers, sender
from .tg.handlers.utils import admin_only, direct_message_only, manager_only

logging.addLevelName(USAGE_LOG_LEVEL, "NOTICE")


def usage(self, message, *args, **kws):
    self._log(USAGE_LOG_LEVEL, message, args, **kws)


logging.Logger.usage = usage
logger = logging.getLogger(__name__)


class SysBlokBot:
    def __init__(
        self,
        config_manager: ConfigManager,
        signal_handler,
        skip_db_update: bool = False,
    ):
        self.config_manager = config_manager
        tg_config = config_manager.get_telegram_config()
        self.application = (
            ApplicationBuilder()
            .persistence(PicklePersistence(filepath="persistent_storage.pickle"))
            .token(tg_config["token"])
            # .post_shutdown(signal_handler)
            .concurrent_updates(True)
            .build()
        )
        self.telegram_sender = sender.TelegramSender(
            bot=self.application.bot, tg_config=tg_config
        )
        try:
            self.app_context = AppContext(config_manager, skip_db_update)
        except BaseException as e:
            # todo infra for such messages
            app_context_broken_msg = (
                f"[{APP_SOURCE}] Bot failed to initialise AppContext"
            )
            if COMMIT_HASH:
                app_context_broken_msg += (
                    f', revision <a href="{COMMIT_URL}">{COMMIT_HASH}</a>.'
                )
            app_context_broken_msg += f"\n{str(e)}"
            self.telegram_sender.send_error_log(app_context_broken_msg)
            raise
        self.handlers_info = defaultdict(lambda: defaultdict(dict))
        logger.info("SysBlokBot successfully initialized")

    def init_handlers(self):
        # all command handlers defined here
        # business logic cmds
        self.add_admin_handler(
            "send_trello_board_state",
            CommandCategories.BROADCAST,
            self.admin_broadcast_handler("trello_board_state_job"),
            "рассылка сводки о состоянии доски",
        )
        self.add_manager_handler(
            "get_trello_board_state",
            CommandCategories.SUMMARY,
            self.manager_reply_handler("trello_board_state_job"),
            "получить сводку о состоянии доски",
        )
        self.add_admin_handler(
            "send_publication_plans",
            CommandCategories.BROADCAST,
            self.admin_broadcast_handler("publication_plans_job"),
            "рассылка сводки о публикуемых на неделе постах",
        )
        self.add_manager_handler(
            "get_manager_status",
            CommandCategories.SUMMARY,
            direct_message_only(self.manager_reply_handler("board_my_cards_razvitie_job")),
            "получить мои карточки из доски Развитие",
        )
        self.add_manager_handler(
            "fill_posts_list",
            CommandCategories.DEBUG,
            direct_message_only(self.manager_reply_handler("fill_posts_list_job")),
            "заполнить реестр постов (пока не работает)",
        )
        self.add_manager_handler(
            "fill_posts_list_focalboard",
            CommandCategories.DEBUG,
            direct_message_only(
                self.manager_reply_handler("fill_posts_list_focalboard_job")
            ),
            "заполнить реестр постов из Focalboard (пока не работает)",
        )
        self.add_admin_handler(
            "hr_acquisition",
            CommandCategories.HR,
            self.manager_reply_handler("hr_acquisition_job"),
            "обработать новые анкеты",
        )
        self.add_admin_handler(
            "hr_acquisition_pt",
            CommandCategories.HR,
            self.manager_reply_handler("hr_acquisition_pt_job"),
            "обработать новые анкеты Пишу Тебе",
        )
        self.add_manager_handler(
            "get_hr_status",
            CommandCategories.HR,
            self.manager_reply_handler("hr_status_job"),
            "получить статус по работе hr (по новичкам и участникам на испытательном)",
        )
        self.add_admin_handler(
            "send_hr_status",
            CommandCategories.BROADCAST,
            self.admin_broadcast_handler("hr_status_job"),
            "разослать статус по работе hr (по новичкам и участинкам на испытательном)",
        )
        self.add_manager_handler(
            "create_folders_for_illustrators",
            CommandCategories.REGISTRY,
            self.manager_reply_handler("create_folders_for_illustrators_job"),
            "создать папки для иллюстраторов",
        )
        self.add_manager_handler(
            "get_tasks_report_focalboard",
            CommandCategories.MOST_USED,
            # CommandCategories.SUMMARY,
            direct_message_only(handlers.get_tasks_report_focalboard),
            "получить список задач из Focalboard",
        )
        self.add_manager_handler(
            "get_articles_rubric",
            CommandCategories.SUMMARY,
            self.manager_reply_handler("trello_get_articles_rubric_job"),
            "получить карточки по названию рубрики в трелло",
        )
        self.add_manager_handler(
            "get_chat_id",
            CommandCategories.MOST_USED,
            handlers.get_chat_id,
            "получить chat_id (свой или группы)",
        )
        self.add_manager_handler(
            "manage_reminders",
            CommandCategories.MOST_USED,
            handlers.manage_reminders,
            "настроить напоминания",
        )
        self.add_manager_handler(
            "get_fb_analytics_report",
            CommandCategories.STATS,
            self.manager_reply_handler("fb_analytics_report_job"),
            "получить статистику facebook страницы за неделю",
        )
        self.add_manager_handler(
            "get_ig_analytics_report",
            CommandCategories.STATS,
            self.manager_reply_handler("ig_analytics_report_job"),
            "получить статистику instagram страницы за неделю",
        )
        self.add_manager_handler(
            "get_tg_analytics_report",
            CommandCategories.STATS,
            self.manager_reply_handler("tg_analytics_report_job"),
            "получить статистику telegram канала за неделю",
        )
        self.add_manager_handler(
            "get_report_from_sheet",
            CommandCategories.SUMMARY,
            self.manager_reply_handler("sheet_report_job"),
            "получить статистику по табличке (например, оцифровка открыток)",
        )
        # hidden from /help command for curator enrollment
        self.add_manager_handler("enroll_curator", CommandCategories.HR, handlers.enroll_curator)

        # admin-only technical cmds
        self.add_admin_handler(
            "update_config",
            CommandCategories.CONFIG,
            self.admin_reply_handler("config_updater_job"),
            "обновить конфиг вне расписания",
        )
        self.add_admin_handler(
            "list_jobs",
            CommandCategories.CONFIG,
            handlers.list_jobs,
            "показать статус асинхронных задач",
        )
        self.add_admin_handler(
            "get_usage_list",
            CommandCategories.CONFIG,
            handlers.list_chats,
            "показать места использование бота: пользователи и чаты",
        )
        self.add_admin_handler(
            "set_log_level",
            CommandCategories.LOGGING,
            handlers.set_log_level,
            "изменить уровень логирования (info / debug)",
        )
        self.add_admin_handler(
            "mute_errors",
            CommandCategories.LOGGING,
            handlers.mute_errors,
            "отключить логирование ошибок в телеграм",
        )
        self.add_admin_handler(
            "unmute_errors",
            CommandCategories.LOGGING,
            handlers.unmute_errors,
            "включить логирование ошибок в телеграм",
        )
        self.add_admin_handler(
            "get_config",
            CommandCategories.CONFIG,
            handlers.get_config,
            "получить текущий конфиг (частично или полностью)",
        )
        self.add_admin_handler(
            "get_config_jobs",
            CommandCategories.CONFIG,
            handlers.get_config_jobs,
            "получить текущий конфиг джобов (частично или полностью)",
        )
        self.add_admin_handler(
            "reload_config_jobs",
            CommandCategories.CONFIG,
            handlers.reload_config_jobs,
            "обновить конфиг джобов с Google-диска",
        )
        self.add_admin_handler(
            "set_config",
            CommandCategories.CONFIG,
            handlers.set_config,
            "установить новое значение в конфиге",
        )
        self.add_admin_handler(
            "add_manager",
            CommandCategories.MOST_USED,
            handlers.add_manager,
            "добавить менеджера в список",
        )
        self.add_admin_handler(
            "change_board",
            CommandCategories.CONFIG,
            handlers.change_board,
            "изменить Trello board_id",
        )
        self.add_admin_handler(
            "send_reminders",
            CommandCategories.BROADCAST,
            self.admin_reply_handler("send_reminders_job"),
            "отослать напоминания вне расписания",
        )
        self.add_admin_handler(
            "send_trello_curator_notification",
            CommandCategories.BROADCAST,
            self.admin_reply_handler("trello_board_state_notifications_job"),
            "разослать кураторам состояние их карточек вне расписания",
        )
        self.add_admin_handler(
            "manage_all_reminders",
            CommandCategories.MOST_USED,
            handlers.manage_all_reminders,
            "настроить все напоминания",
        )
        self.add_admin_handler(
            "get_roles_for_member",
            # CommandCategories.HR,
            CommandCategories.DEBUG,
            handlers.get_roles_for_member,
            "показать роли для участника",
        )
        self.add_admin_handler(
            "get_members_for_role",
            # CommandCategories.HR,
            CommandCategories.DEBUG,
            handlers.get_members_for_role,
            "показать участников для роли",
        )
        self.add_admin_handler(
            "check_chat_consistency",
            CommandCategories.HR,
            self.admin_reply_handler("hr_check_chat_consistency_job"),
            "консистентность чата редакции",
        )
        self.add_admin_handler(
            "check_chat_consistency_frozen",
            CommandCategories.HR,
            self.admin_reply_handler("hr_check_chat_consistency_frozen_job"),
            "консистентность чата редакции (замороженные участники)",
        )
        self.add_admin_handler(
            "get_members_without_telegram",
            CommandCategories.HR,
            self.admin_reply_handler("hr_get_members_without_telegram_job"),
            (
                "активные участники без указанного телеграма"
                "(телефон это 10+ цифр+-(), отсутствие включает #N/A и кириллицу)"
            ),
        )
        self.add_admin_handler(
            "check_site_health",
            CommandCategories.DATA_SYNC,
            self.admin_reply_handler("site_health_check_job"),
            "проверка статуса сайта",
        )
        self.add_admin_handler(
            "get_chat_data",
            CommandCategories.DEBUG,
            handlers.get_chat_data,
            "get_chat_data",
        )
        self.add_admin_handler(
            "clean_chat_data",
            CommandCategories.DEBUG,
            handlers.clean_chat_data,
            "clean_chat_data",
        )
        self.add_admin_handler(
            "get_managers",
            CommandCategories.MOST_USED,
            handlers.get_managers,
            "get_managers",
        )

        # sample handler
        self.add_handler(
            "sample_handler",
            self.admin_reply_handler("sample_job"),
        )

        # db commands hidden from /help command
        self.add_handler(
            "db_fetch_authors_sheet",
            self.admin_reply_handler("db_fetch_authors_sheet_job"),
        )
        self.add_handler(
            "db_fetch_curators_sheet",
            self.admin_reply_handler("db_fetch_curators_sheet_job"),
        )
        self.add_handler(
            "db_fetch_team_sheet",
            self.admin_reply_handler("db_fetch_team_sheet_job"),
        )
        self.add_handler(
            "db_fetch_strings_sheet",
            self.admin_reply_handler("db_fetch_strings_sheet_job"),
        )
        self.add_admin_handler(
            "db_fetch_all_team_members",
            CommandCategories.MOST_USED,
            self.admin_reply_handler("db_fetch_all_team_members_job"),
            "db_fetch_all_team_members",
        )

        # general purpose cmds
        self.add_admin_handler(
            "start", CommandCategories.DEBUG, handlers.start, "начать чат с ботом"
        )
        self.add_admin_handler(
            "get_board_credentials",
            CommandCategories.DEBUG,
            # CommandCategories.MOST_USED,
            lambda update, context: handlers.get_board_credentials(update, context),
            "получить пароль от Focalboard",
        )
        self.add_admin_handler(
            "help",
            CommandCategories.DEBUG,
            # CommandCategories.MOST_USED,
            lambda update, context: handlers.help(update, context, self.handlers_info),
            "получить список доступных команд",
        )
        self.add_admin_handler(
            "shrug",
            CommandCategories.DEBUG,
            # CommandCategories.MOST_USED,
            self.admin_reply_handler("shrug_job"),
            "¯\\_(ツ)_/¯",
        )

        # on non-command user message

        def asyncify(func):
            async def wrapper(*args, **kwargs):
                results = func(*args, **kwargs)
                return results

            return wrapper

        self.application.add_handler(
            MessageHandler(filters.TEXT, asyncify(handlers.handle_user_message))
        )
        self.application.add_handler(
            CallbackQueryHandler(asyncify(handlers.handle_callback_query))
        )
        self.application.add_handler(
            MessageHandler(
                filters.StatusUpdate.NEW_CHAT_MEMBERS, asyncify(handlers.handle_new_members)
            )
        )

        # log all errors
        self.application.add_error_handler(asyncify(handlers.error))

    def run(self):
        # Start the Bot
        logger.info("Starting polling...")
        # TODO add non-blocking runtime (graceful termination for SIGTERM etc)
        self.application.run_polling()

    # Methods, adding command handlers and setting them to /help cmd for proper audience
    def add_handler(self, handler_cmd: str, handler_func: Callable):
        """Adds handler silently. Noone will see it in /help output"""

        def add_usage_logging(func):
            async def wrapper(*args, **kwargs):
                try:
                    update = args[0]
                    username = update.message.from_user.username or update.message.from_user.id
                    logger.usage(f"Handler {handler_cmd} was called by {username}...")
                except BaseException:
                    logger.usage(f"Handler {handler_cmd} was called...")
                results = func(*args, **kwargs)
                logger.usage(f"Handler {handler_cmd} finished")
                return results

            return wrapper

        self.application.add_handler(
            CommandHandler(handler_cmd, add_usage_logging(handler_func))
        )

    def add_admin_handler(
        self,
        handler_cmd: str,
        handler_category: CommandCategories,
        handler_func: Callable,
        description: str = "",
    ):
        """
        Adds handler. It will be listed in /help for admins only
        Note: method does not automatically handle invokation restrictions.
        See tg.utils#admin_only
        """
        self.add_handler(handler_cmd, handler_func)
        self.handlers_info[handler_category]["admin"][
            f"/{handler_cmd}"
        ] = description

    def add_manager_handler(
        self,
        handler_cmd: str,
        handler_category: CommandCategories,
        handler_func: Callable,
        description: str = "",
    ):
        """
        Adds handler. It will be listed in /help for admins and managers only
        Note: method does not automatically handle invokation restrictions.
        See tg.utils#manager_only
        """
        self.add_handler(handler_cmd, handler_func)
        self.handlers_info[handler_category]["manager"][
            f"/{handler_cmd}"
        ] = description

    def add_user_handler(
        self,
        handler_cmd: str,
        handler_category: CommandCategories,
        handler_func: Callable,
        description: str = "",
    ):
        """Adds handler. It will be listed in /help for everybody"""
        self.add_handler(handler_cmd, handler_func)
        self.handlers_info[handler_category]["user"][
            f"/{handler_cmd}"
        ] = description

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
        return manager_only(
            self._create_reply_handler(
                job_name,
            )
        )

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
            called_from_handler=True,
            args=update.message.text.split()[1:],
            kwargs={'called_from_chat_username': update.message.chat.username},
        )

    def _create_broadcast_handler(self, job_name: str) -> Callable:
        """
        Creates a handler that sends message to list of chat ids.
        """
        chat_ids = self.config_manager.get_job_send_to(job_name)
        return lambda update, tg_context: get_job_runnable(job_name)(
            app_context=self.app_context,
            send=self.telegram_sender.create_chat_ids_send(chat_ids),
            called_from_handler=True,
        )
