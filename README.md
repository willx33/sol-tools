# Sol Tools - Ultimate Crypto Toolkit

A comprehensive toolkit for blockchain and cryptocurrency analysis, combining multiple specialized tools into a single CLI interface.

## Features

- **Dragon Analysis Tools**: Advanced wallet, trader, and token analysis for Solana, Ethereum, and GMGN
- **Dune Analytics Integration**: Query the Dune API and parse results
- **Sharp Tools**: Wallet processing, CSV merging, and PnL analysis utilities
- **Solana Monitoring**: Real-time monitoring and alerts for Solana transactions
- **Telegram Integration**: Send alerts and scrape data from Telegram channels
- **Wallet Utilities**: Check, filter, split, and analyze wallet addresses
- **Interactive CLI**: User-friendly menu-based interface with keyboard navigation

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/sol-tools.git
cd sol-tools

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

## Usage

```bash
# Launch the interactive CLI
sol-tools

# Get help information
sol-tools --help
```

## First-time Setup

On first run, the application will guide you through setting up required API keys and configuration options.

You can also manually create a `.env` file in the root directory with the following variables:

```
# Required API Keys
DUNE_API_KEY=your_dune_api_key
HELIUS_API_KEY=your_helius_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# Optional Configuration
PROXY_ENABLED=false
DATA_DIRECTORY=data
```

## Module Documentation

Each module has specific functionalities and requirements. See the detailed documentation for each:

- [Dragon Tools](docs/dragon.md)
- [Dune Tools](docs/dune.md)
- [Sharp Tools](docs/sharp.md)
- [Solana Tools](docs/solana.md)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.