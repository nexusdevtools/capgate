import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler


class LoggerManager:
    """
    Centralized logger that:
    - Logs to console with color (via Rich)
    - Logs to file with rotation
    - Supports different verbosity levels
    - Tagging by plugin/component
    """

    def __init__(self, name: str = "capgate", log_dir: str = "logs", level: str = "VERBOSE", silent: bool = False):
        self.name = name
        self.silent = silent
        self.log_dir = Path(__file__).resolve().parent.parent / log_dir
        self.log_dir.mkdir(exist_ok=True)
        self.log_file = self.log_dir / f"{name}.log"
        self.level = getattr(logging, level.upper(), logging.DEBUG)

        self.console = Console()
        self.logger = logging.getLogger(name)
        self.logger.setLevel(self.level)
        self._setup_handlers()

    def _setup_handlers(self):
        self.logger.handlers.clear()

        if not self.silent:
            console_handler = RichHandler(
                console=self.console,
                show_time=False,
                show_level=True,
                show_path=False,
                markup=True
            )
            console_handler.setLevel(self.level)
            self.logger.addHandler(console_handler)

        file_handler = RotatingFileHandler(
            self.log_file, maxBytes=5 * 1024 * 1024, backupCount=3
        )
        file_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] (%(name)s) %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG)
        self.logger.addHandler(file_handler)

    def get_logger(self, submodule: Optional[str] = None):
        """
        Return a logger with optional submodule tagging (e.g. 'core.plugin_loader')
        """
        return self.logger.getChild(submodule) if submodule else self.logger
# capgate/src/capgate/core/logger.py

# Module-level default logger
logger_manager = LoggerManager()
logger = logger_manager.get_logger()

# Convenience aliases
def get_logger(submodule: Optional[str] = None):
    """Get a logger instance, optionally with submodule tagging."""
    return logger_manager.get_logger(submodule)

log = logger  # Quick alias for default logger