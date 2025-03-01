# Sol-Tools: Ultimate Crypto Analysis Toolkit

A comprehensive command-line toolkit that unifies multiple cryptocurrency analysis and operations tools into a single powerful interface. This project brings together functionality from Dragon, Sharp-Tools, Solana analytics, Dune API integration, GMGN data, and more.

## Features

### Cross-Chain Analytics
- **Solana Analytics**: Bundle checker, wallet analysis, top traders, transaction scanning, copy wallet finder, top holders, early buyers
- **Ethereum Analytics**: Wallet checker, top traders, transaction scanning, timestamp finder
- **API Integrations**: GMGN, Dune Analytics, BullX, and more

### API Modules
- **Dune Analytics**: Execute Dune queries and save results to CSV, parse query results
- **GMGN Integration**: Fetch token data, market cap data, token listings (new, completing, soaring, bonded)

### Blockchain Modules
- **Solana Tools**: Token monitoring, wallet tracking, transaction analysis, telegram integration
- **Ethereum Tools**: Transaction analysis, wallet analysis, token tracking

### Sharp-Tools
- **Wallet Checker**: Analyze wallet statistics via BullX API with real-time progress tracking and export
- **Wallet Splitter**: Break large wallet lists into smaller chunks with validation and detailed reporting
- **CSV Processing**: Merge, filter, and analyze CSV data with comprehensive metadata

### Core Features
- **Interactive CLI**: User-friendly menu with keyboard navigation (arrow keys)
- **Environment Manager**: GUI for adding/editing API keys and environment variables
- **Unified Data Structure**: Organized by blockchain and module type for clarity
- **Cross-blockchain Support**: Works with Solana, Ethereum, and other networks
- **Progress Tracking**: Real-time progress bars with ETA for all operations
- **Export Functionality**: Export results in JSON, CSV, and Excel formats with detailed metadata
- **Workflow Management**: Comprehensive tracking of inputs, outputs, and statistics for all operations

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/sol-tools.git
cd sol-tools

# Install with pip
pip install -e .
```

## Usage

```bash
# Launch the CLI with curses interface (default)
sol-tools

# Show help information and available commands
sol-tools --help  # Shows usage, all available flags and their descriptions

# Launch with text-based menu instead of curses interface
sol-tools --text-menu

# Check version
sol-tools --version

# Run in test mode (no API calls or real transactions)
sol-tools --test

# Clean cache and temporary files
sol-tools --clean
```

## Configuration

The application uses environment variables for configuration. You can set these in a `.env` file in the project root or use the Settings menu in the application.

Required environment variables by module:

- **Dragon**: `SOLSCAN_API_KEY`, `ETHERSCAN_API_KEY`
- **Solana**: `HELIUS_API_KEY`, `SOLANA_RPC_URL`, `SOLANA_WEBSOCKET_URL`
- **Ethereum**: `ETHEREUM_RPC_URL`, `ETHERSCAN_API_KEY`
- **Dune**: `DUNE_API_KEY`
- **Telegram**: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- **GMGN**: No API key required
- **BullX**: No API key required

## Requirements

- Python 3.9+
- See requirements.txt for package dependencies

## License

MIT License