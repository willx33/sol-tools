"""
Integration test for dependency requirements.

This test ensures that all required dependencies are available for the application to run.
It performs two types of checks:
1. Direct import tests for critical dependencies
2. Importing key application modules to ensure they load properly
3. Verifying that all dependencies are properly listed in requirements.txt
"""

import sys
import importlib
import pytest
import re
from pathlib import Path

# List of direct dependencies to check with package name and import name
REQUIRED_DEPENDENCIES = [
    ('jsonschema', 'jsonschema'),      # Used by config_registry for schema validation
    ('python-dotenv', 'dotenv'),       # Used for environment variable loading
    ('pyyaml', 'yaml'),                # Used for YAML config support
    ('rich', 'rich'),                  # Used for rich console output
    ('inquirer', 'inquirer'),          # Used for interactive prompts
    ('colorama', 'colorama')           # Used for colored terminal output
]

# List of core application modules to import test
CORE_MODULES = [
    'sol_tools.core.config_registry',
    'sol_tools.core.di_container',
    'sol_tools.core.base_adapter',
    'sol_tools.cli'  # This imports the main CLI entry point
]


def test_direct_dependencies():
    """Test that all required direct dependencies can be imported."""
    missing_deps = []
    
    for package_name, import_name in REQUIRED_DEPENDENCIES:
        try:
            importlib.import_module(import_name)
        except ImportError as e:
            missing_deps.append((package_name, str(e)))
    
    if missing_deps:
        error_msg = "Missing required dependencies:\n"
        for dep, err in missing_deps:
            error_msg += f"- {dep}: {err}\n"
        pytest.fail(error_msg)


def test_core_module_imports():
    """Test that all core application modules can be imported."""
    missing_modules = []
    
    for module in CORE_MODULES:
        try:
            importlib.import_module(module)
        except ImportError as e:
            missing_modules.append((module, str(e)))
    
    if missing_modules:
        error_msg = "Failed to import core modules:\n"
        for module, err in missing_modules:
            error_msg += f"- {module}: {err}\n"
        pytest.fail(error_msg)


def test_application_startup():
    """Test that the application can be started (imported) without errors."""
    try:
        from sol_tools.cli import main
    except Exception as e:
        pytest.fail(f"Failed to import application entry point: {e}")


def test_requirements_completeness():
    """Test that all required dependencies are listed in requirements.txt."""
    # Find the requirements.txt file
    project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
    requirements_path = project_root / "requirements.txt"
    
    assert requirements_path.exists(), "requirements.txt file not found"
    
    # Read the requirements file
    with open(requirements_path, "r") as f:
        requirements_content = f.read()
    
    # Check if each required dependency is in the requirements file
    missing_from_requirements = []
    
    for package_name, _ in REQUIRED_DEPENDENCIES:
        # Use regex to find the package, allowing for version specifiers
        if not re.search(rf"^{re.escape(package_name)}[=<>~!]", requirements_content, re.MULTILINE):
            # Also check without version specifier
            if not re.search(rf"^{re.escape(package_name)}$", requirements_content, re.MULTILINE):
                missing_from_requirements.append(package_name)
    
    if missing_from_requirements:
        error_msg = "The following dependencies are used but not listed in requirements.txt:\n"
        for dep in missing_from_requirements:
            error_msg += f"- {dep}\n"
        pytest.fail(error_msg) 