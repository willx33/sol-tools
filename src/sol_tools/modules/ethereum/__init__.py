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
        raise ImportError("EthWalletChecker implementation is not available")

class PlaceholderEthTopTraders:
    """Placeholder for EthTopTraders when the real implementation cannot be imported."""
    def __init__(self, *args: Any, **kwargs: Any):
        raise ImportError("EthTopTraders implementation is not available")

class PlaceholderEthScanAllTx:
    """Placeholder for EthScanAllTx when the real implementation cannot be imported."""
    def __init__(self, *args: Any, **kwargs: Any):
        raise ImportError("EthScanAllTx implementation is not available")

class PlaceholderEthTimestampTransactions:
    """Placeholder for EthTimestampTransactions when the real implementation cannot be imported."""
    def __init__(self, *args: Any, **kwargs: Any):
        raise ImportError("EthTimestampTransactions implementation is not available")

# Try to import each module individually to prevent cascading failures
try:
    from .eth_wallet import EthWalletChecker
except Exception as e:
    if not IN_TEST_MODE:  # Only log if not in test mode
        logger.warning(f"Could not import EthWalletChecker: {str(e)}")
    EthWalletChecker = PlaceholderEthWalletChecker  # type: ignore

try:
    from .eth_traders import EthTopTraders
except Exception as e:
    if not IN_TEST_MODE:  # Only log if not in test mode
        logger.warning(f"Could not import EthTopTraders: {str(e)}")
    EthTopTraders = PlaceholderEthTopTraders  # type: ignore

try:
    from .eth_scan import EthScanAllTx
except Exception as e:
    if not IN_TEST_MODE:  # Only log if not in test mode
        logger.warning(f"Could not import EthScanAllTx: {str(e)}")
    EthScanAllTx = PlaceholderEthScanAllTx  # type: ignore

try:
    from .eth_timestamp import EthTimestampTransactions
except Exception as e:
    if not IN_TEST_MODE:  # Only log if not in test mode
        logger.warning(f"Could not import EthTimestampTransactions: {str(e)}")
    EthTimestampTransactions = PlaceholderEthTimestampTransactions  # type: ignore

# Define package exports
__all__ = [
    'EthWalletChecker',
    'EthTopTraders',
    'EthScanAllTx',
    'EthTimestampTransactions'
] 