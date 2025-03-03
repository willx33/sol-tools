"""Core handlers module."""

from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class BaseHandler:
    """Base class for all handlers."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize base handler.
        
        Args:
            config: Optional configuration dictionary
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = config or {}
    
    def handle(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """
        Base handle method to be implemented by subclasses.
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Response data
        """
        raise NotImplementedError("Subclasses must implement handle()")
    
    def validate(self, data: Any) -> bool:
        """
        Validate input data.
        
        Args:
            data: Data to validate
            
        Returns:
            True if valid, False otherwise
        """
        return True
    
    def cleanup(self) -> None:
        """Clean up any resources."""
        pass 