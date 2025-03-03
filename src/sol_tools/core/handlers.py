"""Base handler class for Sol Tools modules."""

from typing import Dict, Any, Optional, Callable

class BaseHandler:
    """Base class for all handlers in Sol Tools."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the handler with optional config."""
        self.config = config or {}
        self.test_mode = False
    
    def setup(self) -> bool:
        """Set up the handler. Override in subclasses."""
        return True
    
    def run(self) -> bool:
        """Run the handler. Override in subclasses."""
        return True
    
    def cleanup(self) -> bool:
        """Clean up resources. Override in subclasses."""
        return True
    
    def __call__(self) -> Any:
        """Make the handler callable. This will run setup, run, and cleanup in sequence."""
        try:
            if not self.setup():
                return False
            result = self.run()
            self.cleanup()
            return result
        except Exception as e:
            print(f"Error in handler: {str(e)}")
            return False 