#!/bin/bash
#
# Script to clean cache and __pycache__ directories
#

echo "🧹 Cleaning cache and __pycache__ directories..."

# Create data/cache and data/__pycache__ directories if they don't exist
mkdir -p data/cache data/__pycache__

# Clear data/cache
echo "Clearing data/cache directory..."
rm -rf data/cache/*
echo "✅ Cache directory cleared"

# Clear data/__pycache__
echo "Clearing data/__pycache__ directory..."
rm -rf data/__pycache__/*
echo "✅ __pycache__ directory cleared"

# Find and remove all __pycache__ directories except in venv
echo "Finding and removing all other __pycache__ directories..."
find . -type d -name "__pycache__" ! -path "*/venv/*" -exec rm -rf {} +
# The plus sign might cause the command to fail to delete directories themselves, just their content
# This is fine as the directories will be recreated with the correct permissions when needed
find . -type d -name "__pycache__" ! -path "*/venv/*" -exec echo "  Removed: {}" \;

echo "✅ Done! All cache directories have been cleared."