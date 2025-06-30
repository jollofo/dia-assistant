"""
Agent Manager Module - Manages and dispatches actions to appropriate agents
"""
from typing import Dict, Any, Optional
from modules.agents.base_agent import BaseAgent
from modules.agents.email_agent import BrowserbaseEmailAgent


class AgentManager:
    """
    AgentManager manages different action agents and dispatches intents to the appropriate agent.
    """
    
    def __init__(self, config: dict):
        """
        Initialize the AgentManager with configuration and available agents.
        
        Args:
            config: Dictionary containing configuration settings
        """
        self.config = config
        
        # Initialize agent registry - maps intent names to agent classes
        self.agent_registry = {
            "SEND_EMAIL": BrowserbaseEmailAgent
        }
        
        # Cache for instantiated agents
        self.agent_cache = {}
        
        print("Agent manager initialized with agents:", list(self.agent_registry.keys()))
    
    def dispatch(self, intent: str, entities: Dict[str, Any]) -> bool:
        """
        Dispatch an intent to the appropriate agent for execution.
        
        Args:
            intent: The intent name (e.g., "SEND_EMAIL")
            entities: Dictionary containing extracted entities for the intent
            
        Returns:
            bool: True if action was successful, False otherwise
        """
        try:
            print(f"Dispatching intent: {intent}")
            print(f"Entities: {entities}")
            
            # Check if we have an agent for this intent
            if intent not in self.agent_registry:
                print(f"No agent registered for intent: {intent}")
                return False
            
            # Get or create agent instance
            agent = self._get_agent(intent)
            if not agent:
                print(f"Failed to instantiate agent for intent: {intent}")
                return False
            
            # Execute the action
            result = agent.execute(entities)
            
            if result:
                print(f"Successfully executed {intent}")
            else:
                print(f"Failed to execute {intent}")
            
            return result
            
        except Exception as e:
            print(f"Error dispatching intent {intent}: {e}")
            return False
    
    def _get_agent(self, intent: str) -> Optional[BaseAgent]:
        """
        Get an agent instance for the given intent, using caching for efficiency.
        
        Args:
            intent: The intent name
            
        Returns:
            BaseAgent instance or None if error
        """
        try:
            # Check cache first
            if intent in self.agent_cache:
                return self.agent_cache[intent]
            
            # Get agent class
            agent_class = self.agent_registry.get(intent)
            if not agent_class:
                return None
            
            # Instantiate agent
            agent = agent_class(self.config)
            
            # Cache the instance
            self.agent_cache[intent] = agent
            
            return agent
            
        except Exception as e:
            print(f"Error creating agent for {intent}: {e}")
            return None
    
    def register_agent(self, intent: str, agent_class: type):
        """
        Register a new agent for an intent.
        
        Args:
            intent: The intent name
            agent_class: The agent class to handle this intent
        """
        self.agent_registry[intent] = agent_class
        print(f"Registered agent {agent_class.__name__} for intent {intent}")
    
    def unregister_agent(self, intent: str):
        """
        Unregister an agent for an intent.
        
        Args:
            intent: The intent name to unregister
        """
        if intent in self.agent_registry:
            del self.agent_registry[intent]
            
        if intent in self.agent_cache:
            del self.agent_cache[intent]
            
        print(f"Unregistered agent for intent {intent}")
    
    def get_supported_intents(self) -> list:
        """
        Get a list of all supported intents.
        
        Returns:
            List of supported intent names
        """
        return list(self.agent_registry.keys()) 