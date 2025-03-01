"""
Integration tests for the command-line interface and application startup.

This test module verifies that the CLI components work correctly:
1. Tests that the main function can be invoked without errors
2. Tests that check_requirements can be called without errors
3. Tests for required imports in CLI module
4. Tests that menu classes are properly initialized with handlers
"""

import pytest
import inspect
import sys
from unittest.mock import patch, MagicMock

def test_cli_imports():
    """Test that the CLI module imports all required dependencies."""
    # Import the CLI module
    from src.sol_tools import cli
    
    # Check that load_config is imported or defined
    assert hasattr(cli, 'load_config'), "load_config should be imported in cli.py"
    
    # Check other critical imports
    critical_imports = ['parse_args', 'check_requirements', 'setup_application']
    for import_name in critical_imports:
        assert hasattr(cli, import_name), f"{import_name} should be imported or defined in cli.py"


def test_check_requirements_function():
    """Test that the check_requirements function calls load_config."""
    # Import the check_requirements function
    from src.sol_tools.cli import check_requirements
    
    # Get the source code of the function
    source = inspect.getsource(check_requirements)
    
    # Check if load_config is called
    assert "load_config" in source, "check_requirements should call load_config"


def test_main_function_structure():
    """Test the structure of the main function."""
    # Import the main function
    from src.sol_tools.cli import main
    
    # Get the source code of the function
    source = inspect.getsource(main)
    
    # Check for critical function calls
    critical_calls = [
        "parse_args()",
        "logging.basicConfig",
        "check_requirements()",
        "setup_application"
    ]
    
    for call in critical_calls:
        assert call in source, f"main function should call {call}"


def test_menu_initialization():
    """Test that menu classes are initialized with handlers."""
    # Import the main function from cli.py
    from src.sol_tools.cli import main, create_handlers
    
    # Mock the menu classes and other dependencies
    with patch('src.sol_tools.cli.CursesMenu') as mock_curses_menu, \
         patch('src.sol_tools.cli.InquirerMenu') as mock_inquirer_menu, \
         patch('src.sol_tools.cli.curses.wrapper') as mock_wrapper, \
         patch('src.sol_tools.cli.parse_args') as mock_parse_args, \
         patch('src.sol_tools.cli.check_requirements') as mock_check_req, \
         patch('src.sol_tools.cli.setup_application') as mock_setup_app, \
         patch('src.sol_tools.cli.logging.basicConfig') as mock_logging:
        
        # Configure mock to return args with text_menu=False to use CursesMenu
        mock_args = MagicMock()
        mock_args.text_menu = False  # Changed from use_curses=True
        mock_args.verbose = False
        mock_args.test = False
        mock_parse_args.return_value = mock_args
        
        # Configure mock_setup_application to return registry and container
        mock_registry = MagicMock()
        mock_container = MagicMock()
        mock_setup_app.return_value = (mock_registry, mock_container)
        
        # Call the main function
        main()
        
        # Verify create_handlers is called
        assert mock_curses_menu.call_count == 1
        # Verify CursesMenu is initialized with handlers
        args, kwargs = mock_curses_menu.call_args
        assert len(args) == 1, "CursesMenu should be initialized with handlers"
        
        # Verify run method is called via curses.wrapper
        assert mock_wrapper.call_count == 1
        # Get the function passed to curses.wrapper
        wrapper_func = mock_wrapper.call_args[0][0]
        # Verify it's the menu's run method
        assert wrapper_func == mock_curses_menu.return_value.run
        
        # Reset mocks for testing non-curses path
        mock_curses_menu.reset_mock()
        mock_wrapper.reset_mock()
        
        # Configure mock to return args with text_menu=True to use InquirerMenu
        mock_args.text_menu = True  # Changed from use_curses=False
        
        # Call the main function again
        main()
        
        # Verify InquirerMenu is initialized with handlers
        assert mock_inquirer_menu.call_count == 1
        args, kwargs = mock_inquirer_menu.call_args
        assert len(args) == 1, "InquirerMenu should be initialized with handlers"
        
        # Verify run method is called
        assert mock_inquirer_menu.return_value.run.call_count == 1


def test_main_function_execution():
    """Test that the main function executes without errors."""
    # Import the main function
    from src.sol_tools.cli import main
    
    # Mock all the functions called by main to prevent actual execution
    with patch('src.sol_tools.cli.parse_args') as mock_parse_args, \
         patch('src.sol_tools.cli.logging.basicConfig') as mock_logging, \
         patch('src.sol_tools.cli.check_requirements') as mock_check_requirements, \
         patch('src.sol_tools.cli.setup_application') as mock_setup_application, \
         patch('src.sol_tools.cli.create_handlers') as mock_create_handlers, \
         patch('src.sol_tools.cli.CursesMenu') as mock_curses_menu, \
         patch('src.sol_tools.cli.InquirerMenu') as mock_inquirer_menu, \
         patch('src.sol_tools.cli.curses.wrapper') as mock_wrapper:
        
        # Configure mock to return args with use_curses=False
        mock_args = MagicMock()
        mock_args.use_curses = False
        mock_args.verbose = False
        mock_args.test = False
        mock_parse_args.return_value = mock_args
        
        # Configure mock_setup_application to return registry and container
        mock_registry = MagicMock()
        mock_container = MagicMock()
        mock_setup_application.return_value = (mock_registry, mock_container)
        
        # Configure mock_create_handlers to return a dict
        mock_handlers = {'exit_app': MagicMock()}
        mock_create_handlers.return_value = mock_handlers
        
        # Call the main function
        main()
        
        # Verify all expected functions were called
        mock_parse_args.assert_called_once()
        mock_logging.assert_called_once()
        mock_check_requirements.assert_called_once()
        mock_setup_application.assert_called_once_with(mock_args)
        mock_create_handlers.assert_called_once()
        mock_inquirer_menu.assert_called_once_with(mock_handlers)
        mock_inquirer_menu.return_value.run.assert_called_once() 