import os
import yaml
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Handles loading and parsing of the central config.yaml file.
    Supports environment variable expansion.
    """
    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        # Default path relative to this file
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 1. Try to load .env from base_dir if it exists
        env_path = os.path.join(base_dir, ".env")
        if os.path.exists(env_path):
            try:
                with open(env_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            k, v = line.split('=', 1)
                            os.environ[k.strip()] = v.strip().strip('"').strip("'")
                logger.debug(f"Loaded environment from {env_path}")
            except Exception as e:
                logger.warning(f"Failed to parse .env file: {e}")

        config_path = os.getenv("SUTRADHARA_CONFIG", os.path.join(base_dir, "config.yaml"))
        
        if not os.path.exists(config_path):
            logger.warning(f"Config file not found at {config_path}. Using hardcoded defaults.")
            self._config = {}
            return

        try:
            with open(config_path, 'r') as f:
                content = f.read()
                
                # 2. Simple environment variable expansion: ${VAR}
                # We do this for ALL variables currently in os.environ
                for key, val in os.environ.items():
                    content = content.replace(f"${{{key}}}", val)
                
                # 3. Handle missing placeholders (set to empty string to avoid LiteLLM issues)
                import re
                content = re.sub(r"\${[A-Z_]+}", "", content)
                
                self._config = yaml.safe_load(content)
                logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self._config = {}

    def get(self, path: str, default: Any = None) -> Any:
        """
        Retrieves a value from the config using a dot-separated path (e.g., 'llm.main_model').
        """
        keys = path.split('.')
        val = self._config
        try:
            for key in keys:
                val = val[key]
            return val
        except (KeyError, TypeError):
            return default

# Global instance
config = ConfigManager()
