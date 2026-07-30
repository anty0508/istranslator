import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

if getattr(sys, "frozen", False):
    # an external .env next to the exe takes precedence (update the key without rebuilding)
    load_dotenv(Path(sys.executable).parent / ".env")
    # the .env baked into the exe at build time is the fallback (load_dotenv won't override)
    bundled = getattr(sys, "_MEIPASS", None)
    if bundled:
        load_dotenv(Path(bundled) / ".env")
load_dotenv()

CONFIG_DIR = Path.home() / ".istranslater"
CONFIG_PATH = CONFIG_DIR / "config.json"

ENV_FALLBACK = {
    "api_key": "OPENAI_API_KEY",
    "base_url": "OPENAI_BASE_URL",
    "model": "OPENAI_MODEL",
}

DEFAULTS = {
    "api_key": "",
    "base_url": "https://api.openai.com/v1",
    "model": "gpt-5-nano",
    "lang1": "English",
    "lang2": "Chinese (Simplified)",
    "hotkey_translate": "double-ctrl",
    "hotkey_replace": "ctrl+'",
    "overlay_timeout_ms": 8000,
    "restore_clipboard": True,
}


class Config:
    def __init__(self, data=None):
        self._data = dict(DEFAULTS)
        if data:
            self._data.update({k: v for k, v in data.items() if k in DEFAULTS})

    def __getitem__(self, key):
        return self._data[key]

    def effective(self, key):
        if key in ENV_FALLBACK:
            env_val = os.environ.get(ENV_FALLBACK[key], "").strip()
            if env_val:
                return env_val
        return self._data.get(key)

    @classmethod
    def load(cls):
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    return cls(json.load(f))
            except (json.JSONDecodeError, OSError):
                pass
        return cls()
