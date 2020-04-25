import datetime
import json
import logging

from src.utils.singleton import Singleton

logger = logging.getLogger(__name__)


class ConfigManager(Singleton):
    def __init__(self, config_path: str = '', config_override_path: str = ''):
        if self.was_initialized():
            return

        self.config_path = config_path
        self.config_override_path = config_override_path
        self._latest_config = {}
        self._latest_config_ts = None

    def load_config_with_override(self) -> dict:
        main_config = self._load_config(self.config_path) or {}
        override_config = self._load_config(self.config_override_path) or {}
        ConfigManager.join_configs(main_config, override_config)
        self._latest_config = main_config
        self._latest_config_ts = datetime.datetime.now()
        return main_config

    def get_latest_config(self):
        """
        Recommended way to access config without re-reading from disk.
        Freshness of the config depends on scheduler.config_checker_job
        """
        logger.info(f'Got config, last updated {self._latest_config_ts}')
        return self._latest_config

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

    def _load_config(self, config_path: str) -> dict:
        try:
            with open(config_path) as fin:
                try:
                    return json.loads(fin.read())
                except json.JSONDecodeError as e:
                    logger.error(e)
        except IOError:
            logger.warning(f'Config file at {config_path} not found')
