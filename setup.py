"""Setup script for sol-tools."""

from setuptools import setup, find_packages
import os

# Read the content of README.md
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read version from __init__.py
with open(os.path.join("src", "sol_tools", "__init__.py"), "r") as f:
    for line in f:
        if line.startswith("__version__"):
            version = line.strip().split("=")[1].strip(" '\"")

setup(
    name="sol-tools",
    version=version,
    author="Will",
    author_email="will@example.com",
    description="Ultimate CLI toolkit for cryptocurrency analysis and operations",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/username/sol-tools",
    project_urls={
        "Bug Tracker": "https://github.com/username/sol-tools/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "sol-tools=sol_tools.cli:main",
            "start=sol_tools.cli:main",
        ],
    },
    install_requires=[
        "inquirer>=3.1.3",
        "python-dotenv>=1.0.0",
        "requests>=2.31.0",
        "web3>=6.11.3",
        "solders>=0.18.1",
        "solana>=0.29.2",
        "aiohttp>=3.8.5",
        "pandas>=2.0.3",
        "colorama>=0.4.6",
        "cryptography>=41.0.4",
        "python-telegram-bot>=13.15",
        "tabulate>=0.9.0",
        "rich>=13.5.3",
    ],
)