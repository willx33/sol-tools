"""
Placeholder for Dragon modules package.
This placeholder allows importing of the Dragon module name even when the actual
implementation is not available. It facilitates the use of fallback implementations.
"""

def __getattr__(name):
    raise ImportError(f"Dragon module '{name}' is not available")