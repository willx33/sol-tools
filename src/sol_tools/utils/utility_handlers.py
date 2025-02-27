"""Utility handlers for Sol-Tools CLI."""

from typing import Dict, Callable, Any

from ..core.config import edit_env_variables
from .common import clear_terminal, clear_cache, test_telegram


def handle_clear_cache() -> None:
    """Handler for clearing the cache."""
    clear_terminal()
    print("🗑️  Clearing cache...")
    clear_cache()


def handle_test_telegram() -> None:
    """Handler for testing Telegram integration."""
    clear_terminal()
    print("📱 Testing Telegram integration...")
    test_telegram()


def get_handlers() -> Dict[str, Callable[[], Any]]:
    """Return all handlers for utilities."""
    return {
        'utils_clear_cache': handle_clear_cache,
        'utils_test_telegram': handle_test_telegram,
        'edit_env_variables': edit_env_variables,
    }