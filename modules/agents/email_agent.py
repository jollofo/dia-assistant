"""
Email Agent Module
Handles email-related tasks through browser automation.
"""

import logging
from typing import Dict, Any, Optional
from .base_agent import BaseAgent

class EmailAgent(BaseAgent):
    """
    Agent for handling email operations through browser automation.
    Currently provides a basic implementation with room for expansion.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # Email configuration
        self.email_config = config.get('email', {})
        self.default_email = self.email_config.get('default_email', '')
        
    def execute(self, entities: Dict[str, Any]) -> Optional[str]:
        """
        Execute email-related actions.
        
        Args:
            entities: Dictionary containing email parameters
            
        Returns:
            Result string describing the action taken
        """
        try:
            action = entities.get('action', '')
            
            if not action:
                self.logger.error("No action specified for email agent")
                return "Error: No email action specified"
                
            # Parse the action to determine what to do
            action_lower = action.lower()
            
            if any(keyword in action_lower for keyword in ['send', 'compose', 'email']):
                return self._handle_send_email(entities)
            elif 'check' in action_lower or 'read' in action_lower:
                return self._handle_check_email(entities)
            else:
                return self._handle_generic_email_action(action)
                
        except Exception as e:
            error_msg = f"Error in email agent execution: {str(e)}"
            self.logger.error(error_msg)
            return error_msg
            
    def _handle_send_email(self, entities: Dict[str, Any]) -> str:
        """
        Handle sending an email.
        
        Args:
            entities: Email parameters
            
        Returns:
            Status message
        """
        # For now, this is a placeholder implementation
        # In a full implementation, this would use browser automation
        # to interact with a web-based email client
        
        action = entities.get('action', '')
        recipient = self._extract_recipient(action)
        subject = self._extract_subject(action)
        
        self.logger.info(f"Email send request - To: {recipient}, Subject: {subject}")
        
        # Placeholder response
        if recipient:
            return f"Email composition started for {recipient}. Please continue in your email client."
        else:
            return "Email composition interface opened. Please specify recipient and content."
            
    def _handle_check_email(self, entities: Dict[str, Any]) -> str:
        """
        Handle checking email.
        
        Args:
            entities: Email parameters
            
        Returns:
            Status message
        """
        self.logger.info("Email check requested")
        
        # Placeholder implementation
        return "Opening email client to check for new messages."
        
    def _handle_generic_email_action(self, action: str) -> str:
        """
        Handle generic email actions.
        
        Args:
            action: The action string
            
        Returns:
            Status message
        """
        self.logger.info(f"Generic email action: {action}")
        
        return f"Email-related action requested: {action}. Opening email client."
        
    def _extract_recipient(self, action: str) -> Optional[str]:
        """
        Extract email recipient from action string.
        
        Args:
            action: Action string to parse
            
        Returns:
            Extracted email address or None
        """
        # Simple regex-like extraction for email addresses
        import re
        
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        matches = re.findall(email_pattern, action)
        
        return matches[0] if matches else None
        
    def _extract_subject(self, action: str) -> Optional[str]:
        """
        Extract email subject from action string.
        
        Args:
            action: Action string to parse
            
        Returns:
            Extracted subject or None
        """
        # Look for common subject indicators
        subject_keywords = ['subject:', 'about', 'regarding', 're:']
        
        action_lower = action.lower()
        for keyword in subject_keywords:
            if keyword in action_lower:
                # Try to extract text after the keyword
                parts = action_lower.split(keyword, 1)
                if len(parts) > 1:
                    subject = parts[1].strip()
                    # Remove quotes if present
                    subject = subject.strip('"\'')
                    return subject if subject else None
                    
        return None
        
    def get_agent_info(self) -> Dict[str, str]:
        """
        Get information about this agent.
        
        Returns:
            Dictionary with agent name and description
        """
        return {
            "name": "EmailAgent",
            "description": "Handles email composition and management through browser automation"
        } 