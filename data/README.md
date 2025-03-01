# Sol Tools Data Directory Structure

This directory contains input and output data for all Sol Tools modules. The directory structure is organized by blockchain, API, and module type for better organization and maintenance.

## Directory Structure

```
data/
├── input-data/                # Input data organized by source
│   ├── api/                   # API-related input data
│   │   ├── dune/              # Dune Analytics input data
│   │   │   └── query-configs/ # Dune query configurations
│   │   └── gmgn/              # GMGN API input data
│   │       └── token-lists/   # Token address lists for GMGN
│   ├── ethereum/              # Ethereum blockchain input data
│   │   ├── token-lists/       # Ethereum token address lists
│   │   └── wallet-lists/      # Ethereum wallet address lists
│   ├── proxies/               # Proxy server configurations
│   │   └── proxies.txt        # List of proxies for API requests
│   ├── sharp/                 # Sharp tools input data
│   └── solana/                # Solana blockchain input data
│       ├── token-lists/       # Solana token address lists
│       └── wallet-lists/      # Solana wallet address lists
│
├── output-data/               # Output data organized by type
│   ├── api/                   # API module outputs
│   │   ├── dune/              # Dune Analytics output
│   │   │   ├── csv/           # Raw CSV query results
│   │   │   └── parsed/        # Parsed query results
│   │   └── gmgn/              # GMGN API output
│   │       ├── token-listings/   # Token listings data
│   │       ├── market-cap-data/  # Market cap data
│   │       └── token-info/       # Token information
│   ├── ethereum/              # Ethereum blockchain outputs
│   │   ├── transaction-data/  # Transaction data
│   │   ├── wallet-data/       # Wallet data
│   │   └── dragon/            # Dragon module output for Ethereum
│   │       ├── wallet-analysis/ # Wallet analysis results
│   │       ├── top-traders/     # Top traders analysis
│   │       ├── top-holders/     # Top holders analysis
│   │       └── early-buyers/    # Early buyers analysis
│   ├── sharp-tools/           # Sharp tools output data
│   │   ├── wallets/           # Wallet data from Sharp tools
│   │   │   └── split/         # Split wallet lists
│   │   └── csv/               # CSV processing results
│   │       ├── merged/        # Merged CSV files
│   │       ├── unmerged/      # Unmerged CSV files
│   │       ├── filtered/      # Filtered CSV files
│   │       └── unfiltered/    # Unfiltered CSV files
│   └── solana/                # Solana blockchain outputs
│       ├── transaction-data/  # Transaction data
│       ├── wallet-data/       # Wallet data
│       ├── telegram/          # Telegram data
│       └── dragon/            # Dragon module output for Solana
│           ├── wallet-analysis/ # Wallet analysis results
│           ├── top-traders/     # Top traders analysis
│           ├── top-holders/     # Top holders analysis
│           ├── early-buyers/    # Early buyers analysis
│           └── token-info/      # Token information
└── cache/                     # Cache directory for temporary files
```

## Module Data Usage

### Blockchain Modules (Solana, Ethereum)

- **Input Data**:
  - `ethereum/wallet-lists/wallets.txt`: Ethereum wallet addresses for analysis
  - `ethereum/token-lists/`: Ethereum token addresses for tracking
  - `solana/wallet-lists/wallets.txt`: Solana wallet addresses for analysis
  - `solana/token-lists/tokens.txt`: Solana token addresses for tracking

- **Output Data**:
  - `ethereum/transaction-data/`: Transaction data from Ethereum
  - `ethereum/wallet-data/`: Wallet data from Ethereum
  - `ethereum/dragon/`: Dragon module outputs for Ethereum (wallet analysis, top traders, etc.)
  - `solana/transaction-data/`: Transaction data from Solana
  - `solana/wallet-data/`: Wallet data from Solana
  - `solana/telegram/`: Data extracted from Telegram
  - `solana/dragon/`: Dragon module outputs for Solana (wallet analysis, top traders, etc.)

### API Modules (Dune, GMGN)

- **Input Data**:
  - `api/dune/query-configs/`: Configuration files for Dune queries
  - `api/gmgn/token-lists/token_addresses.txt`: Token addresses for GMGN queries

- **Output Data**:
  - `api/dune/csv/`: Raw CSV results from Dune queries
  - `api/dune/parsed/`: Parsed results from Dune queries
  - `api/gmgn/token-listings/`: Token listings data (new, completing, soaring, bonded)
  - `api/gmgn/market-cap-data/`: Market capitalization data
  - `api/gmgn/token-info/`: Detailed token information

### Sharp-Tools

- **Output Data**:
  - `sharp-tools/wallets/`: Wallet data processed by Sharp tools
  - `sharp-tools/csv/merged/`: Merged CSV files
  - `sharp-tools/csv/unmerged/`: Original unmerged CSV files
  - `sharp-tools/csv/filtered/`: Filtered CSV data
  - `sharp-tools/csv/unfiltered/`: Unfiltered CSV data

### Common Resources

- **Input Data**:
  - `proxies/proxies.txt`: Proxy server configuration for API requests

- **Cache**:
  - `cache/`: Temporary storage for logs, interim results, and other ephemeral data

## Notes

- This directory structure organizes data first by type (input/output), then by source (blockchain/API)
- Dragon outputs are included within their respective blockchain directories (solana/ethereum)
- API-related data is consolidated under the api/ directory
- All paths in the application use this consistent structure
- Input data files are generally text files with one item per line
- Output data files are typically JSON or CSV with timestamp-based filenames
- Paths are relative to the project root, ensuring portability across different environments
- The directory structure is automatically created when the application starts