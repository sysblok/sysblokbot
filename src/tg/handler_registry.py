from dataclasses import dataclass
from typing import Callable, Optional, Literal

from ..consts import CommandCategories
from . import handlers


@dataclass
class HandlerConfig:
    command: str
    description: str = ""
    category: Optional[CommandCategories] = None
    access_level: Literal["admin", "manager", "user", "hidden"] = "hidden"

    # Logic configuration
    handler_func: Optional[Callable] = None
    job_name: Optional[str] = None
    job_type: Literal[
        "admin_broadcast", "admin_reply", "manager_reply", "user_reply"
    ] = "manager_reply"

    # Modifiers
    direct_only: bool = False


HANDLER_REGISTRY = [
    # Business logic cmds
    HandlerConfig(
        command="send_trello_board_state",
        category=CommandCategories.BROADCAST,
        access_level="admin",
        job_name="trello_board_state_job",
        job_type="admin_broadcast",
        description="рассылка сводки о состоянии доски",
    ),
    HandlerConfig(
        command="get_trello_board_state",
        category=CommandCategories.SUMMARY,
        access_level="manager",
        job_name="trello_board_state_job",
        job_type="manager_reply",
        description="получить сводку о состоянии доски",
    ),
    HandlerConfig(
        command="get_publication_plans",
        category=CommandCategories.SUMMARY,
        access_level="manager",
        job_name="publication_plans_job",
        job_type="manager_reply",
        description="получить сводку о публикуемыми на неделе постами",
    ),
    HandlerConfig(
        command="send_publication_plans",
        category=CommandCategories.BROADCAST,
        access_level="admin",
        job_name="publication_plans_job",
        job_type="admin_broadcast",
        description="рассылка сводки о публикуемых на неделе постах",
    ),
    HandlerConfig(
        command="get_manager_status",
        category=CommandCategories.SUMMARY,
        access_level="manager",
        job_name="board_my_cards_razvitie_job",
        job_type="manager_reply",
        direct_only=True,
        description="получить мои карточки из доски Развитие",
    ),
    HandlerConfig(
        command="fill_posts_list",
        category=CommandCategories.DEBUG,
        access_level="manager",
        job_name="fill_posts_list_job",
        job_type="manager_reply",
        direct_only=True,
        description="заполнить реестр постов (пока не работает)",
    ),
    HandlerConfig(
        command="fill_posts_list_focalboard",
        category=CommandCategories.DEBUG,
        access_level="manager",
        job_name="fill_posts_list_focalboard_job",
        job_type="manager_reply",
        direct_only=True,
        description="заполнить реестр постов из Focalboard (пока не работает)",
    ),
    HandlerConfig(
        command="hr_acquisition",
        category=CommandCategories.HR,
        access_level="admin",
        job_name="hr_acquisition_job",
        job_type="manager_reply",
        description="обработать новые анкеты",
    ),
    HandlerConfig(
        command="hr_acquisition_pt",
        category=CommandCategories.HR,
        access_level="admin",
        job_name="hr_acquisition_pt_job",
        job_type="manager_reply",
        description="обработать новые анкеты Пишу Тебе",
    ),
    HandlerConfig(
        command="get_hr_status",
        category=CommandCategories.HR,
        access_level="manager",
        job_name="hr_status_job",
        job_type="manager_reply",
        description="получить статус по работе hr (по новичкам и участникам на испытательном)",
    ),
    HandlerConfig(
        command="send_hr_status",
        category=CommandCategories.BROADCAST,
        access_level="admin",
        job_name="hr_status_job",
        job_type="admin_broadcast",
        description="разослать статус по работе hr (по новичкам и участинкам на испытательном)",
    ),
    HandlerConfig(
        command="create_folders_for_illustrators",
        category=CommandCategories.REGISTRY,
        access_level="manager",
        job_name="create_folders_for_illustrators_job",
        job_type="manager_reply",
        description="создать папки для иллюстраторов",
    ),
    HandlerConfig(
        command="get_tasks_report_focalboard",
        category=CommandCategories.MOST_USED,
        access_level="manager",
        handler_func=handlers.get_tasks_report_focalboard,
        direct_only=True,
        description="получить список задач из Focalboard",
    ),
    HandlerConfig(
        command="get_rubrics",
        category=CommandCategories.MOST_USED,
        access_level="manager",
        handler_func=handlers.get_rubrics,
        direct_only=True,
        description="получить рубрики из доски Редакция",
    ),
    HandlerConfig(
        command="get_articles_rubric",
        category=CommandCategories.DEBUG,
        access_level="manager",
        job_name="trello_get_articles_rubric_job",
        job_type="manager_reply",
        description="получить карточки по названию рубрики в трелло",
    ),
    HandlerConfig(
        command="get_chat_id",
        category=CommandCategories.MOST_USED,
        access_level="manager",
        handler_func=handlers.get_chat_id,
        description="получить chat_id (свой или группы)",
    ),
    HandlerConfig(
        command="manage_reminders",
        category=CommandCategories.MOST_USED,
        access_level="manager",
        handler_func=handlers.manage_reminders,
        description="настроить напоминания",
    ),
    HandlerConfig(
        command="get_fb_analytics_report",
        category=CommandCategories.STATS,
        access_level="manager",
        job_name="fb_analytics_report_job",
        job_type="manager_reply",
        description="получить статистику facebook страницы за неделю",
    ),
    HandlerConfig(
        command="get_ig_analytics_report",
        category=CommandCategories.STATS,
        access_level="manager",
        job_name="ig_analytics_report_job",
        job_type="manager_reply",
        description="получить статистику instagram страницы за неделю",
    ),
    HandlerConfig(
        command="get_tg_analytics_report",
        category=CommandCategories.STATS,
        access_level="manager",
        job_name="tg_analytics_report_job",
        job_type="manager_reply",
        description="получить статистику telegram канала за неделю",
    ),
    HandlerConfig(
        command="get_report_from_sheet",
        category=CommandCategories.SUMMARY,
        access_level="manager",
        job_name="sheet_report_job",
        job_type="manager_reply",
        description="получить статистику по табличке (например, оцифровка открыток)",
    ),
    HandlerConfig(
        command="enroll_curator",
        category=CommandCategories.HR,
        access_level="manager",
        handler_func=handlers.enroll_curator,
        description="",  # hidden from help
    ),
    # Admin-only technical cmds
    HandlerConfig(
        command="update_config",
        category=CommandCategories.CONFIG,
        access_level="admin",
        job_name="config_updater_job",
        job_type="admin_reply",
        description="обновить конфиг вне расписания",
    ),
    HandlerConfig(
        command="list_jobs",
        category=CommandCategories.CONFIG,
        access_level="admin",
        handler_func=handlers.list_jobs,
        description="показать статус асинхронных задач",
    ),
    HandlerConfig(
        command="get_usage_list",
        category=CommandCategories.CONFIG,
        access_level="admin",
        handler_func=handlers.list_chats,
        description="показать места использование бота: пользователи и чаты",
    ),
    HandlerConfig(
        command="set_log_level",
        category=CommandCategories.LOGGING,
        access_level="admin",
        handler_func=handlers.set_log_level,
        description="изменить уровень логирования (info / debug)",
    ),
    HandlerConfig(
        command="mute_errors",
        category=CommandCategories.LOGGING,
        access_level="admin",
        handler_func=handlers.mute_errors,
        description="отключить логирование ошибок в телеграм",
    ),
    HandlerConfig(
        command="unmute_errors",
        category=CommandCategories.LOGGING,
        access_level="admin",
        handler_func=handlers.unmute_errors,
        description="включить логирование ошибок в телеграм",
    ),
    HandlerConfig(
        command="get_config",
        category=CommandCategories.CONFIG,
        access_level="admin",
        handler_func=handlers.get_config,
        description="получить текущий конфиг (частично или полностью)",
    ),
    HandlerConfig(
        command="get_config_jobs",
        category=CommandCategories.CONFIG,
        access_level="admin",
        handler_func=handlers.get_config_jobs,
        description="получить текущий конфиг джобов (частично или полностью)",
    ),
    HandlerConfig(
        command="reload_config_jobs",
        category=CommandCategories.CONFIG,
        access_level="admin",
        handler_func=handlers.reload_config_jobs,
        description="обновить конфиг джобов с Google-диска",
    ),
    HandlerConfig(
        command="set_config",
        category=CommandCategories.CONFIG,
        access_level="admin",
        handler_func=handlers.set_config,
        description="установить новое значение в конфиге",
    ),
    HandlerConfig(
        command="add_manager",
        category=CommandCategories.MOST_USED,
        access_level="admin",
        handler_func=handlers.add_manager,
        description="добавить менеджера в список",
    ),
    HandlerConfig(
        command="change_board",
        category=CommandCategories.CONFIG,
        access_level="admin",
        handler_func=handlers.change_board,
        description="изменить Trello board_id",
    ),
    HandlerConfig(
        command="send_reminders",
        category=CommandCategories.BROADCAST,
        access_level="admin",
        job_name="send_reminders_job",
        job_type="admin_reply",
        description="отослать напоминания вне расписания",
    ),
    HandlerConfig(
        command="send_trello_curator_notification",
        category=CommandCategories.BROADCAST,
        access_level="admin",
        job_name="trello_board_state_notifications_job",
        job_type="admin_reply",
        description="разослать кураторам состояние их карточек вне расписания",
    ),
    HandlerConfig(
        command="manage_all_reminders",
        category=CommandCategories.MOST_USED,
        access_level="admin",
        handler_func=handlers.manage_all_reminders,
        description="настроить все напоминания",
    ),
    HandlerConfig(
        command="get_roles_for_member",
        category=CommandCategories.DEBUG,
        access_level="admin",
        handler_func=handlers.get_roles_for_member,
        description="показать роли для участника",
    ),
    HandlerConfig(
        command="get_members_for_role",
        category=CommandCategories.DEBUG,
        access_level="admin",
        handler_func=handlers.get_members_for_role,
        description="показать участников для роли",
    ),
    HandlerConfig(
        command="check_chat_consistency",
        category=CommandCategories.HR,
        access_level="admin",
        job_name="hr_check_chat_consistency_job",
        job_type="admin_reply",
        description="консистентность чата редакции",
    ),
    HandlerConfig(
        command="check_chat_consistency_frozen",
        category=CommandCategories.HR,
        access_level="admin",
        job_name="hr_check_chat_consistency_frozen_job",
        job_type="admin_reply",
        description="консистентность чата редакции (замороженные участники)",
    ),
    HandlerConfig(
        command="get_members_without_telegram",
        category=CommandCategories.HR,
        access_level="admin",
        job_name="hr_get_members_without_telegram_job",
        job_type="admin_reply",
        description="активные участники без указанного телеграма(телефон это 10+ цифр+-(), отсутствие включает #N/A и кириллицу)",
    ),
    HandlerConfig(
        command="check_site_health",
        category=CommandCategories.DATA_SYNC,
        access_level="admin",
        job_name="site_health_check_job",
        job_type="admin_reply",
        description="проверка статуса сайта",
    ),
    HandlerConfig(
        command="get_chat_data",
        category=CommandCategories.DEBUG,
        access_level="admin",
        handler_func=handlers.get_chat_data,
        description="get_chat_data",
    ),
    HandlerConfig(
        command="clean_chat_data",
        category=CommandCategories.DEBUG,
        access_level="admin",
        handler_func=handlers.clean_chat_data,
        description="clean_chat_data",
    ),
    HandlerConfig(
        command="get_managers",
        category=CommandCategories.MOST_USED,
        access_level="admin",
        handler_func=handlers.get_managers,
        description="get_managers",
    ),
    # Sample and DB commands
    HandlerConfig(
        command="sample_handler",
        access_level="hidden",
        job_name="sample_job",
        job_type="admin_reply",
    ),
    HandlerConfig(
        command="db_fetch_authors_sheet",
        access_level="hidden",
        job_name="db_fetch_authors_sheet_job",
        job_type="admin_reply",
    ),
    HandlerConfig(
        command="db_fetch_curators_sheet",
        access_level="hidden",
        job_name="db_fetch_curators_sheet_job",
        job_type="admin_reply",
    ),
    HandlerConfig(
        command="db_fetch_team_sheet",
        access_level="hidden",
        job_name="db_fetch_team_sheet_job",
        job_type="admin_reply",
    ),
    HandlerConfig(
        command="db_fetch_strings_sheet",
        access_level="hidden",
        job_name="db_fetch_strings_sheet_job",
        job_type="admin_reply",
    ),
    HandlerConfig(
        command="db_fetch_all_team_members",
        category=CommandCategories.MOST_USED,
        access_level="admin",
        job_name="db_fetch_all_team_members_job",
        job_type="admin_reply",
        description="db_fetch_all_team_members",
    ),
    HandlerConfig(
        command="backfill_telegram_user_ids",
        category=CommandCategories.DATA_SYNC,
        access_level="admin",
        job_name="backfill_telegram_user_ids_job",
        job_type="admin_reply",
        description="backfill Telegram user IDs from team member usernames",
    ),
    # General purpose
    HandlerConfig(
        command="start",
        category=CommandCategories.DEBUG,
        access_level="admin",
        handler_func=handlers.start,
        description="начать чат с ботом",
    ),
    HandlerConfig(
        command="shrug",
        category=CommandCategories.DEBUG,
        access_level="admin",
        job_name="shrug_job",
        job_type="admin_reply",
        description="¯\\_(ツ)_/¯",
    ),
    # HELP is handled specially or requires lambda
]
