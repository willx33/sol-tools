"""Test the Dragon GMGN token info functionality."""

import asyncio
import logging
from pathlib import Path
from src.sol_tools.modules.dragon.dragon_adapter import DragonAdapter, TokenDataHandler, GMGN_Client

# Set up logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("dragon-test")

async def test_token_info():
    """Test the token_info functionality."""
    print("Testing Dragon GMGN token info...")
    
    # Initialize the adapter
    adapter = DragonAdapter()
    success = await adapter.initialize()
    
    if not success:
        print("❌ Failed to initialize adapter")
        return False
    
    print("✅ Adapter initialized successfully")
    
    # Check if token_data_handler is properly initialized
    if adapter.token_data_handler is None:
        print("❌ token_data_handler is None")
        
        # Try to initialize it manually
        print("Attempting to initialize token_data_handler manually...")
        adapter.token_data_handler = TokenDataHandler()
    else:
        print("✅ token_data_handler is initialized")
    
    # Test address - replace with a valid Solana token address
    test_address = "7rdeLkyfmxujFthUNYZM7jWGEKZnT9mkeSGG1c9hpump"
    
    # Test token info function
    try:
        print(f"Getting token info for {test_address}...")
        token_info = adapter.get_token_info_sync(test_address)
        
        if token_info:
            print("Token info received:")
            print(f"  Error: {token_info.get('error', 'None')}")
            print(f"  Name: {token_info.get('name', 'Unknown')}")
            print(f"  Symbol: {token_info.get('symbol', 'Unknown')}")
            return True
        else:
            print("❌ No token info received")
            return False
    except Exception as e:
        print(f"❌ Error getting token info: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_token_info()) 