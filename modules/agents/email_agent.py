"""
Email Agent Module - Handles email sending using Browserbase API
"""
import os
import time
import requests
from typing import Dict, Any, Optional
from modules.agents.base_agent import BaseAgent


class BrowserbaseEmailAgent(BaseAgent):
    """
    BrowserbaseEmailAgent uses the Browserbase API to automate email sending through Gmail.
    """
    
    def __init__(self, config: dict):
        """
        Initialize the email agent with Browserbase configuration.
        
        Args:
            config: Dictionary containing configuration settings
        """
        super().__init__(config)
        
        # Get Browserbase API key from environment
        self.api_key = os.getenv('BROWSERBASE_API_KEY')
        if not self.api_key:
            raise ValueError("BROWSERBASE_API_KEY environment variable is required")
        
        # Browserbase API configuration
        self.base_url = "https://www.browserbase.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Email configuration
        self.email_config = config.get('agents', {}).get('email', {})
        self.gmail_url = self.email_config.get('default_gmail_url', 'https://mail.google.com')
        
        print("Browserbase email agent initialized")
    
    def execute(self, entities: Dict[str, Any]) -> bool:
        """
        Execute email sending action using Browserbase.
        
        Args:
            entities: Dictionary containing email entities:
                - recipient_email: Email address of recipient
                - recipient_name: Name of recipient (optional)
                - subject: Email subject
                - body: Email content/message
                
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            # Validate required entities
            required_entities = ['recipient_email', 'subject', 'body']
            if not self.validate_entities(entities, required_entities):
                return False
            
            # Extract entities
            recipient_email = entities['recipient_email']
            recipient_name = entities.get('recipient_name', recipient_email)
            subject = entities['subject']
            body = entities['body']
            
            self.log_action("Starting email send", True, f"To: {recipient_email}")
            
            # Create browser session
            session_id = self._create_browser_session()
            if not session_id:
                self.log_action("Create browser session", False)
                return False
            
            try:
                # Navigate to Gmail
                if not self._navigate_to_gmail(session_id):
                    self.log_action("Navigate to Gmail", False)
                    return False
                
                # Wait for Gmail to load
                time.sleep(3)
                
                # Click compose button
                if not self._click_compose_button(session_id):
                    self.log_action("Click compose button", False)
                    return False
                
                # Fill in email details
                if not self._fill_email_form(session_id, recipient_email, subject, body):
                    self.log_action("Fill email form", False)
                    return False
                
                # Send the email
                if not self._send_email(session_id):
                    self.log_action("Send email", False)
                    return False
                
                self.log_action("Email sent successfully", True, f"To: {recipient_email}")
                return True
                
            finally:
                # Clean up browser session
                self._cleanup_browser_session(session_id)
                
        except Exception as e:
            self.log_action("Execute email action", False, str(e))
            return False
    
    def _create_browser_session(self) -> Optional[str]:
        """
        Create a new browser session using Browserbase API.
        
        Returns:
            str: Session ID if successful, None otherwise
        """
        try:
            payload = {
                "projectId": os.getenv('BROWSERBASE_PROJECT_ID'),  # Optional project ID
                "keepAlive": True,
                "timeout": 300  # 5 minutes timeout
            }
            
            response = requests.post(
                f"{self.base_url}/sessions",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 201:
                session_data = response.json()
                session_id = session_data.get('id')
                self.log_action("Created browser session", True, f"ID: {session_id}")
                return session_id
            else:
                self.log_action("Create browser session", False, f"Status: {response.status_code}")
                return None
                
        except Exception as e:
            self.log_action("Create browser session", False, str(e))
            return None
    
    def _navigate_to_gmail(self, session_id: str) -> bool:
        """
        Navigate to Gmail in the browser session.
        
        Args:
            session_id: Browser session ID
            
        Returns:
            bool: True if navigation was successful, False otherwise
        """
        try:
            payload = {
                "url": self.gmail_url
            }
            
            response = requests.post(
                f"{self.base_url}/sessions/{session_id}/navigate",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            success = response.status_code == 200
            self.log_action("Navigate to Gmail", success, f"URL: {self.gmail_url}")
            return success
            
        except Exception as e:
            self.log_action("Navigate to Gmail", False, str(e))
            return False
    
    def _click_compose_button(self, session_id: str) -> bool:
        """
        Click the compose button in Gmail.
        
        Args:
            session_id: Browser session ID
            
        Returns:
            bool: True if click was successful, False otherwise
        """
        try:
            # Try multiple selectors for the compose button
            selectors = [
                'div[gh="cm"]',  # Gmail compose button
                '[data-tooltip="Compose"]',
                'div[role="button"][aria-label*="Compose"]',
                '.T-I.T-I-KE.L3'  # Classic Gmail compose button
            ]
            
            for selector in selectors:
                payload = {
                    "selector": selector,
                    "action": "click"
                }
                
                response = requests.post(
                    f"{self.base_url}/sessions/{session_id}/element/action",
                    headers=self.headers,
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    self.log_action("Click compose button", True, f"Selector: {selector}")
                    time.sleep(2)  # Wait for compose window to open
                    return True
            
            self.log_action("Click compose button", False, "No selector worked")
            return False
            
        except Exception as e:
            self.log_action("Click compose button", False, str(e))
            return False
    
    def _fill_email_form(self, session_id: str, recipient: str, subject: str, body: str) -> bool:
        """
        Fill in the email form fields.
        
        Args:
            session_id: Browser session ID
            recipient: Recipient email address
            subject: Email subject
            body: Email body content
            
        Returns:
            bool: True if form was filled successfully, False otherwise
        """
        try:
            # Fill recipient field
            if not self._fill_field(session_id, 'input[name="to"]', recipient, "To field"):
                if not self._fill_field(session_id, 'textarea[name="to"]', recipient, "To field (textarea)"):
                    return False
            
            # Fill subject field
            if not self._fill_field(session_id, 'input[name="subjectbox"]', subject, "Subject field"):
                if not self._fill_field(session_id, 'input[placeholder*="Subject"]', subject, "Subject field (placeholder)"):
                    return False
            
            # Fill body field
            body_selectors = [
                'div[aria-label="Message Body"]',
                'div[role="textbox"]',
                'div[contenteditable="true"]'
            ]
            
            for selector in body_selectors:
                if self._fill_field(session_id, selector, body, "Body field"):
                    break
            else:
                self.log_action("Fill body field", False, "No selector worked")
                return False
            
            self.log_action("Fill email form", True, "All fields filled")
            return True
            
        except Exception as e:
            self.log_action("Fill email form", False, str(e))
            return False
    
    def _fill_field(self, session_id: str, selector: str, value: str, field_name: str) -> bool:
        """
        Fill a specific form field.
        
        Args:
            session_id: Browser session ID
            selector: CSS selector for the field
            value: Value to fill
            field_name: Name of the field (for logging)
            
        Returns:
            bool: True if field was filled successfully, False otherwise
        """
        try:
            payload = {
                "selector": selector,
                "action": "type",
                "text": value
            }
            
            response = requests.post(
                f"{self.base_url}/sessions/{session_id}/element/action",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            success = response.status_code == 200
            if success:
                self.log_action(f"Fill {field_name}", True, f"Value: {value[:50]}...")
            
            return success
            
        except Exception as e:
            self.log_action(f"Fill {field_name}", False, str(e))
            return False
    
    def _send_email(self, session_id: str) -> bool:
        """
        Click the send button to send the email.
        
        Args:
            session_id: Browser session ID
            
        Returns:
            bool: True if send was successful, False otherwise
        """
        try:
            # Try multiple selectors for the send button
            selectors = [
                'div[data-tooltip="Send"]',
                'div[aria-label="Send"]',
                'div[role="button"][aria-label*="Send"]',
                '.T-I.J-J5-Ji.aoO.v7.T-I-atl.L3'  # Classic Gmail send button
            ]
            
            for selector in selectors:
                payload = {
                    "selector": selector,
                    "action": "click"
                }
                
                response = requests.post(
                    f"{self.base_url}/sessions/{session_id}/element/action",
                    headers=self.headers,
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    self.log_action("Send email", True, f"Selector: {selector}")
                    time.sleep(2)  # Wait for send confirmation
                    return True
            
            self.log_action("Send email", False, "No selector worked")
            return False
            
        except Exception as e:
            self.log_action("Send email", False, str(e))
            return False
    
    def _cleanup_browser_session(self, session_id: str):
        """
        Clean up the browser session.
        
        Args:
            session_id: Browser session ID
        """
        try:
            response = requests.delete(
                f"{self.base_url}/sessions/{session_id}",
                headers=self.headers,
                timeout=30
            )
            
            success = response.status_code == 200
            self.log_action("Cleanup browser session", success, f"ID: {session_id}")
            
        except Exception as e:
            self.log_action("Cleanup browser session", False, str(e)) 