"""
Knowledge Agent Module
Handles knowledge lookups and explanations using LLM integration.
"""

import json
import requests
import logging
from typing import Dict, Any, Optional
from .base_agent import BaseAgent

class KnowledgeAgent(BaseAgent):
    """
    Agent for handling knowledge-related queries.
    Uses LLM integration to define, explain, and provide information about topics.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # Ollama configuration for knowledge queries
        self.ollama_config = config.get('ollama', {})
        
    def execute(self, entities: Dict[str, Any]) -> Optional[str]:
        """
        Execute knowledge-related queries.
        
        Args:
            entities: Dictionary containing the topic to research
            
        Returns:
            Definition or explanation of the topic
        """
        try:
            # Validate required entities
            if not self.validate_entities(entities, ['topic']):
                return "Error: No topic specified for knowledge lookup"
                
            topic = entities['topic']
            
            if not topic or not topic.strip():
                return "Error: Empty topic specified"
                
            # Clean up the topic
            topic = topic.strip()
            
            self.logger.info(f"Knowledge request for topic: {topic}")
            
            # Get definition/explanation from LLM
            result = self._get_topic_explanation(topic)
            
            if result:
                return result
            else:
                return f"Unable to find information about '{topic}'. Please try rephrasing your query."
                
        except Exception as e:
            error_msg = f"Error in knowledge agent execution: {str(e)}"
            self.logger.error(error_msg)
            return error_msg
            
    def _get_topic_explanation(self, topic: str) -> Optional[str]:
        """
        Get explanation of a topic from the LLM.
        
        Args:
            topic: The topic to explain
            
        Returns:
            Explanation string or None if failed
        """
        try:
            # Construct the prompt for topic explanation
            prompt_text = f"""
Please provide a clear, concise explanation of the following topic: "{topic}"

Include:
- A brief definition
- Key characteristics or features
- Why it's significant or relevant
- Any important context

Keep the explanation informative but accessible, suitable for someone who wants to quickly understand the concept.

Topic: {topic}
"""

            # Prepare Ollama request payload
            ollama_payload = {
                "model": self.ollama_config.get('model', 'llama3'),
                "prompt": prompt_text,
                "stream": False
            }
            
            # Make request to Ollama API
            base_url = self.ollama_config.get('base_url', 'http://localhost:11434')
            timeout = self.ollama_config.get('timeout', 30)
            
            response = requests.post(
                f"{base_url}/api/generate",
                json=ollama_payload,
                timeout=timeout
            )
            
            if response.status_code == 200:
                response_data = response.json()
                explanation = response_data.get('response', '').strip()
                
                if explanation:
                    self.logger.info(f"Successfully retrieved explanation for '{topic}'")
                    return explanation
                else:
                    self.logger.warning(f"Empty response for topic '{topic}'")
                    return None
            else:
                self.logger.error(f"Ollama request failed: {response.status_code} - {response.text}")
                return None
                
        except requests.RequestException as e:
            self.logger.error(f"Network error during knowledge request: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error in knowledge lookup: {e}")
            return None
            
    def get_agent_info(self) -> Dict[str, str]:
        """
        Get information about this agent.
        
        Returns:
            Dictionary with agent name and description
        """
        return {
            "name": "KnowledgeAgent",
            "description": "Provides definitions and explanations of topics and concepts using AI"
        } 