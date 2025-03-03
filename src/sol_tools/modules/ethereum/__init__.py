"""
Ethereum modules for SOL Tools.
"""

# Import modules with proper error handling
import logging
import os
from typing import Any, Type

# Setup logging
logger = logging.getLogger(__name__)

# Remove any existing handlers to prevent duplication
for handler in list(logger.handlers):
    logger.removeHandler(handler)

# Add a NullHandler by default to prevent logging warnings
logger.addHandler(logging.NullHandler())

# Check if we're in test mode
IN_TEST_MODE = os.environ.get("TEST_MODE") == "1"

# Configure logging based on test mode
if IN_TEST_MODE:
    # Set critical+1 level (higher than any standard level)
    logger.setLevel(logging.CRITICAL + 1)
else:
    # In non-test mode, add a StreamHandler for console output
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(console_handler)
    logger.setLevel(logging.INFO)

# Define placeholders for failed imports
class PlaceholderEthWalletChecker:
    """Placeholder for EthWalletChecker when the real implementation cannot be imported."""
    def __init__(self, *args: Any, **kwargs: Any):
        raise ImportError(
            "EthWalletChecker implementation is not available. "
            "This usually means either:\n"
            "1. The eth_wallet.py module failed to import\n"
            "2. There was an error in the eth_wallet.py module\n"
            "Please check the ethereum module's log files for detailed error messages."
        )

class PlaceholderEthTopTraders:
    """Placeholder for EthTopTraders when the real implementation cannot be imported."""
    def __init__(self, *args: Any, **kwargs: Any):
        raise ImportError(
            "EthTopTraders implementation is not available. "
            "This usually means either:\n"
            "1. The eth_traders.py module failed to import\n"
            "2. There was an error in the eth_traders.py module\n"
            "Please check the ethereum module's log files for detailed error messages."
        )

class PlaceholderEthScanAllTx:
    """Placeholder for EthScanAllTx when the real implementation cannot be imported."""
    def __init__(self, *args: Any, **kwargs: Any):
        raise ImportError(
            "EthScanAllTx implementation is not available. "
            "This usually means either:\n"
            "1. The eth_scan.py module failed to import\n"
            "2. There was an error in the eth_scan.py module\n"
            "Please check the ethereum module's log files for detailed error messages."
        )

class PlaceholderEthTimestampTransactions:
    """Placeholder for EthTimestampTransactions when the real implementation cannot be imported."""
    def __init__(self, *args: Any, **kwargs: Any):
        raise ImportError(
            "EthTimestampTransactions implementation is not available. "
            "This usually means either:\n"
            "1. The eth_timestamp.py module failed to import\n"
            "2. There was an error in the eth_timestamp.py module\n"
            "Please check the ethereum module's log files for detailed error messages."
        )

# Try to import each module individually with better error logging
try:
    from .eth_wallet import EthWalletChecker
except ImportError as e:
    if not IN_TEST_MODE:
        logger.error(f"Failed to import EthWalletChecker: {str(e)}")
        logger.error("Please check that eth_wallet.py exists and is properly formatted")
    EthWalletChecker = PlaceholderEthWalletChecker  # type: ignore

try:
    from .eth_traders import EthTopTraders
except ImportError as e:
    if not IN_TEST_MODE:
        logger.error(f"Failed to import EthTopTraders: {str(e)}")
        logger.error("Please check that eth_traders.py exists and is properly formatted")
    EthTopTraders = PlaceholderEthTopTraders  # type: ignore

try:
    from .eth_scan import EthScanAllTx
except ImportError as e:
    if not IN_TEST_MODE:
        logger.error(f"Failed to import EthScanAllTx: {str(e)}")
        logger.error("Please check that eth_scan.py exists and is properly formatted")
    EthScanAllTx = PlaceholderEthScanAllTx  # type: ignore

try:
    from .eth_timestamp import EthTimestampTransactions
except ImportError as e:
    if not IN_TEST_MODE:
        logger.error(f"Failed to import EthTimestampTransactions: {str(e)}")
        logger.error("Please check that eth_timestamp.py exists and is properly formatted")
    EthTimestampTransactions = PlaceholderEthTimestampTransactions  # type: ignore

# Define package exports
__all__ = [
    'EthWalletChecker',
    'EthTopTraders',
    'EthScanAllTx',
    'EthTimestampTransactions'
] 