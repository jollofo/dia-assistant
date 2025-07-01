"""
Base Agent Module
Abstract base class for all agents in the system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    Defines the common interface that all agents must implement.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the base agent.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(f"Initialized {self.__class__.__name__}")
        
    @abstractmethod
    def execute(self, entities: Dict[str, Any]) -> Optional[str]:
        """
        Execute the agent's primary function.
        
        Args:
            entities: Dictionary containing relevant entities and parameters
            
        Returns:
            Result string from the execution, or None if failed
        """
        pass
        
    def validate_entities(self, entities: Dict[str, Any], required_keys: list) -> bool:
        """
        Validate that required entities are present.
        
        Args:
            entities: Dictionary to validate
            required_keys: List of required keys
            
        Returns:
            True if all required keys are present, False otherwise
        """
        missing_keys = [key for key in required_keys if key not in entities]
        if missing_keys:
            self.logger.error(f"Missing required entities: {missing_keys}")
            return False
        return True
        
    def get_agent_info(self) -> Dict[str, str]:
        """
        Get information about this agent.
        
        Returns:
            Dictionary with agent name and description
        """
        return {
            "name": self.__class__.__name__,
            "description": "Base agent class"
        } 