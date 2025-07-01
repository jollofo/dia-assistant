"""
Agent Manager Module
Manages different agents and routes tasks based on intents.
"""

import logging
from typing import Dict, Any, Optional
from modules.agents.base_agent import BaseAgent
from modules.agents.email_agent import EmailAgent
from modules.agents.knowledge_agent import KnowledgeAgent

class AgentManager:
    """
    Manages all available agents and routes tasks based on detected intents.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize available agents
        self.agents = {
            "SEND_EMAIL": EmailAgent(config),
            "DEFINE_TOPIC": KnowledgeAgent(config),
            "EXPLAIN_CONCEPT": KnowledgeAgent(config),
            "LOOKUP_INFORMATION": KnowledgeAgent(config)
        }
        
        self.logger.info(f"Initialized AgentManager with {len(self.agents)} agents")
        
    def execute_action(self, action_text: str) -> Optional[str]:
        """
        Execute an action based on the action text from the UI.
        
        Args:
            action_text: The action string suggested by the LLM
            
        Returns:
            Result string from the agent execution, or None if failed
        """
        try:
            # Parse the action to determine intent and entities
            intent, entities = self._parse_action(action_text)
            
            if not intent:
                self.logger.warning(f"Could not determine intent for action: {action_text}")
                return None
                
            # Get the appropriate agent
            agent = self.agents.get(intent)
            if not agent:
                self.logger.warning(f"No agent available for intent: {intent}")
                return None
                
            # Execute the task
            self.logger.info(f"Executing {intent} with entities: {entities}")
            result = agent.execute(entities)
            
            return result
            
        except Exception as e:
            error_msg = f"Error executing action '{action_text}': {str(e)}"
            self.logger.error(error_msg)
            return error_msg
            
    def _parse_action(self, action_text: str) -> tuple[Optional[str], Dict[str, Any]]:
        """
        Parse an action string to determine the intent and extract entities.
        
        Args:
            action_text: The action string to parse
            
        Returns:
            Tuple of (intent, entities_dict)
        """
        action_lower = action_text.lower().strip()
        
        # Define patterns for different intents
        if any(keyword in action_lower for keyword in ['define', 'what is', 'explain']):
            # Extract the topic/concept to define
            topic = self._extract_topic(action_text)
            return "DEFINE_TOPIC", {"topic": topic}
            
        elif any(keyword in action_lower for keyword in ['send email', 'email', 'compose']):
            # Extract email details (simplified for now)
            return "SEND_EMAIL", {"action": action_text}
            
        elif any(keyword in action_lower for keyword in ['lookup', 'search', 'find information']):
            topic = self._extract_topic(action_text)
            return "LOOKUP_INFORMATION", {"topic": topic}
            
        else:
            # Default to knowledge lookup for unknown actions
            topic = self._extract_topic(action_text)
            return "DEFINE_TOPIC", {"topic": topic}
            
    def _extract_topic(self, action_text: str) -> str:
        """
        Extract the main topic/concept from an action string.
        
        Args:
            action_text: The action string
            
        Returns:
            Extracted topic string
        """
        # Simple extraction - remove common action words
        action_words = ['define', 'explain', 'what is', 'lookup', 'search for', 'find information about']
        
        topic = action_text.lower().strip()
        for word in action_words:
            topic = topic.replace(word, '').strip()
            
        # Remove extra whitespace and quotes
        topic = ' '.join(topic.split())
        topic = topic.strip('"\'')
        
        return topic or action_text
        
    def get_available_agents(self) -> Dict[str, str]:
        """
        Get a list of available agents and their descriptions.
        
        Returns:
            Dictionary mapping agent names to descriptions
        """
        return {
            "SEND_EMAIL": "Send emails through browser automation",
            "DEFINE_TOPIC": "Define or explain concepts and topics",
            "EXPLAIN_CONCEPT": "Provide detailed explanations of concepts",
            "LOOKUP_INFORMATION": "Look up and provide information about topics"
        }
        
    def add_agent(self, intent: str, agent: BaseAgent):
        """
        Add a new agent to the manager.
        
        Args:
            intent: The intent string to map to this agent
            agent: The agent instance
        """
        self.agents[intent] = agent
        self.logger.info(f"Added new agent for intent: {intent}")
        
    def remove_agent(self, intent: str):
        """
        Remove an agent from the manager.
        
        Args:
            intent: The intent string to remove
        """
        if intent in self.agents:
            del self.agents[intent]
            self.logger.info(f"Removed agent for intent: {intent}")
        else:
            self.logger.warning(f"Attempted to remove non-existent agent: {intent}") 