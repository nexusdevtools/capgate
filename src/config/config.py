# config.py — Centralized Configuration Loader for CapGate

import os
from pathlib import Path
import yaml

CONFIG_DIR = Path(__file__).resolve().parent.parent / "configs"

class Config:
    """
    Loads YAML config files and caches them for reuse.
    """
    _cache = {}

    @classmethod
    def load(cls, name: str):
        if name in cls._cache:
            return cls._cache[name]

        path = CONFIG_DIR / name
        if not path.exists():
            raise FileNotFoundError(f"Missing config file: {path}")

        with open(path, "r") as f:
            data = yaml.safe_load(f)
            cls._cache[name] = data
            return data

    @classmethod
    def clear_cache(cls):
        cls._cache.clear()

# Usage Example:
# sdr_config = Config.load("sdr_config.yaml")
