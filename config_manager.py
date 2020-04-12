import json
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self, config_path: str, config_override_path: str):
        self.config_path = config_path
        self.config_override_path = config_override_path

    def load_config_with_override(self) -> dict:
        main_config = self._load_config(self.config_path) or {}
        override_config = self._load_config(self.config_override_path) or {}
        self._join_configs(main_config, override_config)
        return main_config
        
    def _join_configs(self, main_config: dict, override_config: dict):
        """Recursively override values from the main config (in place)"""
        for key in override_config:
            if key in main_config and isinstance(main_config[key], dict):
                # recursively do the same
                self._join_configs(main_config[key], override_config[key])
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