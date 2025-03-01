# Menu Environment Variable Indicators

The Sol Tools menu system now includes visual indicators to show which modules are missing required environment variables.

## Visual Indicators

- 🔴 (Red dot): Indicates a menu option that requires environment variables that are not currently set
- Menu options without a red dot: All required environment variables are available

## How It Works

The menu system checks for required environment variables for each module as defined in `core/config.py`. If any required variables are missing, a red dot is displayed next to the menu option.

Top-level menu options show a red dot if any of their child menu options require missing environment variables. This makes it easy to identify which sections need configuration.

## Required Environment Variables by Module

The following environment variables are required for different modules:

1. **Solana Module**
   - `HELIUS_API_KEY`: Used for Solana blockchain API access

2. **Dune Module**
   - `DUNE_API_KEY`: Used for Dune Analytics API access

3. **Telegram Integration**
   - `TELEGRAM_BOT_TOKEN`: Used to authenticate with the Telegram API
   - `TELEGRAM_CHAT_ID`: Defines where to send messages

4. **Other Modules**
   - Dragon, Ethereum, GMGN, BullX, Sharp: Currently no required environment variables

## Adding New Environment Variables

When adding new modules or features that require environment variables:

1. Update `REQUIRED_ENV_VARS` in `src/sol_tools/core/config.py`
2. The menu system will automatically detect the new requirements
3. Visual indicators will display for any missing variables

## Testing Menu Indicators

You can test the environment variable indicators using:

```bash
python -m src.sol_tools.tests.test_menu
```

This displays the current status of all environment variables and shows how the menu will appear to users. 