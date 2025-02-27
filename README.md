# Sol-Tools: Ultimate Crypto God Tools

A comprehensive command-line toolkit that unifies multiple cryptocurrency analysis and operations tools into a single powerful interface. This project brings together functionality from Dragon, Sharp-Setup, Solana-Token-Bot, Dune API tools, CSV processing, and more.

## Features

### Dragon Tools
- **Solana Analytics**: Bundle checker, wallet analysis, top traders, transaction scanning, copy wallet finder, top holders, early buyers
- **Ethereum Analytics**: Wallet checker, top traders, transaction scanning, timestamp finder
- **GMGN Integration**: New tokens, completing tokens, soaring tokens, bonded tokens

### Solana Tools
- **Token Monitoring**: Real-time monitoring of new transactions for specific tokens
- **Wallet Monitoring**: Watch transactions for specific wallets
- **Telegram Scraper**: Extract token data from Telegram channels

### Dune Analytics
- **Query Runner**: Execute Dune queries and save results to CSV
- **Result Parser**: Extract token addresses from query results

### Sharp Tools
- **Wallet Checker**: Analyze wallet statistics via BullX API
- **Wallet Splitter**: Break large wallet lists into smaller chunks
- **CSV Merger**: Combine multiple CSV files into a single file
- **PnL Checker**: Filter wallet CSVs based on performance metrics

### Core Features
- **Interactive CLI**: User-friendly menu with keyboard navigation (arrow keys)
- **Environment Manager**: GUI for adding/editing API keys and environment variables
- **Unified Configuration**: Centralized settings across all tools
- **Cross-blockchain Support**: Works with Solana, Ethereum, and other networks

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

# Launch with text-based menu
sol-tools --text-menu

# Check version
sol-tools --version
```

## Configuration

The application uses environment variables for configuration. You can set these in a `.env` file in the project root or use the Settings menu in the application.

Required environment variables by module:

- **Dragon**: `SOLSCAN_API_KEY`, `ETHERSCAN_API_KEY`
- **Solana**: `HELIUS_API_KEY`, `SOLANA_RPC_URL`, `SOLANA_WEBSOCKET_URL`
- **Ethereum**: `ETHEREUM_RPC_URL`, `ETHERSCAN_API_KEY`
- **Dune**: `DUNE_API_KEY`
- **Telegram**: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- **GMGN**: `PUMPFUN_API_KEY`, `MOONSHOT_API_KEY`
- **BullX**: `BULLX_API_KEY`

## Requirements

- Python 3.9+
- See requirements.txt for package dependencies

## License

MIT License