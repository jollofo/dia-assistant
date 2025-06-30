"""
Base Agent Module - Abstract base class for all action agents
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseAgent(ABC):
    """
    Abstract base class for all action agents.
    
    All agents must inherit from this class and implement the execute method.
    """
    
    def __init__(self, config: dict):
        """
        Initialize the base agent with configuration.
        
        Args:
            config: Dictionary containing configuration settings
        """
        self.config = config
    
    @abstractmethod
    def execute(self, entities: Dict[str, Any]) -> bool:
        """
        Execute the agent's action based on the provided entities.
        
        Args:
            entities: Dictionary containing extracted entities for the action
            
        Returns:
            bool: True if action was successful, False otherwise
        """
        pass
    
    def validate_entities(self, entities: Dict[str, Any], required_keys: list) -> bool:
        """
        Validate that all required entity keys are present.
        
        Args:
            entities: Dictionary containing entities
            required_keys: List of required entity keys
            
        Returns:
            bool: True if all required keys are present, False otherwise
        """
        for key in required_keys:
            if key not in entities or not entities[key]:
                print(f"Missing required entity: {key}")
                return False
        return True
    
    def log_action(self, action: str, success: bool, details: str = ""):
        """
        Log an action for debugging and monitoring.
        
        Args:
            action: Description of the action performed
            success: Whether the action was successful
            details: Additional details about the action
        """
        status = "SUCCESS" if success else "FAILED"
        message = f"[{self.__class__.__name__}] {action}: {status}"
        if details:
            message += f" - {details}"
        print(message) 