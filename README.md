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
- **Visual Indicators**: Red dots show menu options with missing required environment variables
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

## Testing

Sol-Tools includes a comprehensive testing framework to ensure all components function correctly. The tests use mock data to simulate APIs and blockchain interactions without making actual external calls.

### Running Tests

```bash
# Run all tests
sol-tools --test

# Run individual test modules (for developers)
python -m src.sol_tools.tests.test_modules.test_dragon
python -m src.sol_tools.tests.test_modules.test_solana
python -m src.sol_tools.tests.test_core.test_file_ops
```

### Test Framework Structure

- **Core Tests**: Test basic functionality like file operations and configuration
- **Module Tests**: Test each module (Dragon, Solana, GMGN, etc.) individually
- **Integration Tests**: Test cross-module workflows and interactions
- **Mock Data**: Uses realistic mock data to simulate API responses

All tests run in isolated temporary directories and clean up after themselves.

## Configuration

The application uses environment variables for configuration. You can set these in a `.env` file in the project root or use the Settings menu in the application. Menu options requiring environment variables that aren't set are marked with a red dot (🔴) for easy identification.

Required environment variables by module:

- **Dune**: `DUNE_API_KEY`
- **Solana**: `HELIUS_API_KEY`
- **Telegram**: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- **GMGN**: No API key required
- **BullX**: No API key required

## Requirements

- Python 3.9+
- See requirements.txt for package dependencies

## License

MIT License