import datetime
import json
import logging

from src import consts
from src.utils.singleton import Singleton

logger = logging.getLogger(__name__)


REDACTED_KEYS = ('key', 'token')


class ConfigManager(Singleton):
    def __init__(self, config_path: str = '', config_override_path: str = ''):
        if self.was_initialized():
            return

        self.config_path = config_path
        self.config_override_path = config_override_path
        self._latest_config = {}
        self._latest_config_override = {}
        self._latest_config_ts = None

    def load_config_with_override(self) -> dict:
        main_config = self._load_config(self.config_path) or {}
        override_config = self._load_config(self.config_override_path) or {}
        ConfigManager.join_configs(main_config, override_config)
        self._latest_config = main_config
        self._latest_config_override = override_config
        self._latest_config_ts = datetime.datetime.now()
        return main_config

    def get_latest_config(self):
        """
        Recommended way to access config without re-reading from disk.
        Freshness of the config depends on jobs.config_checker_job
        """
        logger.debug(f'Got config, last updated: {self._latest_config_ts}')
        return self._latest_config

    def get_trello_config(self):
        return self.get_latest_config().get(consts.TRELLO_CONFIG, {})

    def get_telegram_config(self):
        return self.get_latest_config().get(consts.TELEGRAM_CONFIG, {})

    def get_sheets_config(self):
        return self.get_latest_config().get(consts.SHEETS_CONFIG, {})

    def get_strings_db_config(self):
        return self.get_latest_config().get(consts.STRINGS_DB_CONFIG, {})

    def get_drive_config(self):
        return self.get_latest_config().get(consts.DRIVE_CONFIG, {})

    def get_facebook_config(self):
        return self.get_latest_config().get(consts.FACEBOOK_CONFIG, {})

    def get_vk_config(self):
        return self.get_latest_config().get(consts.VK_CONFIG, {})

    def get_jobs_config(self, job_key=None):
        config = self.get_latest_config().get(consts.JOBS_CONFIG, {})
        if job_key is None:
            return config
        if job_key not in config:
            raise ValueError(f'Trying to get job config for {job_key}, config does not exist')
        return config[job_key]

    def get_db_config(self):
        return self.get_latest_config().get(consts.DB_CONFIG, {})

    def get_job_send_to(self, job_name: str):
        return self.get_jobs_config().get(job_name, {}).get(consts.SEND_TO, [])

    def set_value_to_config_override(self, config_path: str, new_value):
        """
        Sets a new value to config_override and writes it to the disk.
        config_path example: jobs.sample_job.at
        Note: no sanity checks performed inside the method!
        """
        new_config_piece = new_value
        for config_item in config_path.split('.')[::-1]:
            new_config_piece = {config_item: new_config_piece}
        config_override = self._latest_config_override
        ConfigManager.join_configs(config_override, new_config_piece)
        self._write_config_override(config_override)

    @staticmethod
    def join_configs(main_config: dict, override_config: dict):
        """Recursively override values from the main config (in place)"""
        for key in override_config:
            if key in main_config and isinstance(main_config[key], dict):
                # recursively do the same
                ConfigManager.join_configs(
                    main_config[key], override_config[key]
                )
            else:
                # rewrite if key is absent, or is list/str/int/bool
                main_config[key] = override_config[key]

    @staticmethod
    def redact(config: dict) -> dict:
        """Returns redacted config copy"""
        if not isinstance(config, dict):
            return config

        redacted_config = {}
        for key, value in config.items():
            if isinstance(value, dict):
                redacted_config[key] = ConfigManager.redact(value)
            else:
                redacted_config[key] = value
                for redacted_key in REDACTED_KEYS:
                    if redacted_key in key:
                        redacted_config[key] = 'XXXXX'
                        break
        return redacted_config

    def _load_config(self, config_path: str) -> dict:
        try:
            with open(config_path, encoding="utf-8") as fin:
                try:
                    return json.loads(fin.read())
                except json.JSONDecodeError as e:
                    logger.error(e)
        except IOError:
            logger.warning(f'Config file at {config_path} not found')

    def _write_config_override(self, config_override: dict):
        with open(self.config_override_path, 'w') as fout:
            fout.write(json.dumps(config_override, indent=4))
