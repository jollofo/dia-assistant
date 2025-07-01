"""
Orchestrator Core Module
Handles continuous analysis of conversation transcripts and generates insights.
"""

import json
import threading
import time
import requests
from typing import Dict, List, Any, Optional
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
import logging

class Orchestrator(QObject):
    """
    Core orchestrator that continuously analyzes conversation transcripts
    and generates insights, topics, and suggested actions.
    """
    
    # Signals for PyQt6 integration
    analysis_updated = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, config: Dict[str, Any], audio_listener=None):
        super().__init__()
        self.config = config
        self.audio_listener = audio_listener
        self.is_running = False
        self.analysis_timer = None
        
        # Thread-safe data structures
        self._lock = threading.Lock()
        self._last_analysis = {}
        
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def start_analysis_loop(self):
        """Start the periodic analysis loop."""
        if self.is_running:
            self.logger.warning("Analysis loop is already running")
            return
            
        self.is_running = True
        self.analysis_timer = QTimer()
        self.analysis_timer.timeout.connect(self._perform_analysis)
        
        # Start timer with interval from config
        interval_ms = self.config.get('analysis', {}).get('interval_seconds', 15) * 1000
        self.analysis_timer.start(interval_ms)
        
        self.logger.info(f"Started analysis loop with {interval_ms/1000}s interval")
        
    def stop_analysis_loop(self):
        """Stop the periodic analysis loop."""
        self.is_running = False
        if self.analysis_timer:
            self.analysis_timer.stop()
            self.analysis_timer = None
        self.logger.info("Stopped analysis loop")
        
    def _perform_analysis(self):
        """Perform analysis of current conversation transcript."""
        try:
            if not self.audio_listener:
                return
                
            # Get current transcript from audio listener
            transcript = self.audio_listener.get_transcript()
            
            if not transcript or len(transcript) == 0:
                self.logger.debug("No transcript available for analysis")
                return
                
            # Limit transcript length to avoid overwhelming the LLM
            max_length = self.config.get('analysis', {}).get('max_transcript_length', 5000)
            conversation_history = "\n".join(transcript)
            if len(conversation_history) > max_length:
                conversation_history = conversation_history[-max_length:]
                
            # Get analysis from LLM
            analysis = self._get_analysis_from_llm(conversation_history)
            
            if analysis:
                with self._lock:
                    self._last_analysis = analysis
                
                # Emit signal with analysis data
                self.analysis_updated.emit(analysis)
                self.logger.info("Analysis completed and emitted")
            else:
                self.logger.warning("Failed to get analysis from LLM")
                
        except Exception as e:
            error_msg = f"Error during analysis: {str(e)}"
            self.logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            
    def _get_analysis_from_llm(self, transcript: str) -> Optional[Dict[str, Any]]:
        """
        Enhanced LLM integration to get structured analysis.
        Returns a JSON object with insights, topics, and actions.
        """
        try:
            # Construct the enhanced prompt
            prompt_text = f"""
System: You are a helpful AI meeting assistant. Analyze the following conversation transcript. Respond ONLY with a single, valid JSON object with three keys: "insights", "topics", and "actions".
- "insights": An array of strings, summarizing the key points of the conversation.
- "topics": An array of key terms or concepts mentioned that could be defined or explored.
- "actions": An array of suggested action strings the user might want to take. These should be concise and clickable.

Transcript:
---
{transcript}
---
"""

            # Prepare Ollama request payload
            ollama_config = self.config.get('ollama', {})
            ollama_payload = {
                "model": ollama_config.get('model', 'llama3'),
                "prompt": prompt_text,
                "format": "json",
                "stream": False
            }
            
            # Make request to Ollama API
            base_url = ollama_config.get('base_url', 'http://localhost:11434')
            timeout = ollama_config.get('timeout', 30)
            
            response = requests.post(
                f"{base_url}/api/generate",
                json=ollama_payload,
                timeout=timeout
            )
            
            if response.status_code == 200:
                response_data = response.json()
                response_text = response_data.get('response', '')
                
                # Parse JSON response
                try:
                    analysis = json.loads(response_text)
                    
                    # Validate structure
                    required_keys = ['insights', 'topics', 'actions']
                    if all(key in analysis for key in required_keys):
                        return analysis
                    else:
                        self.logger.error(f"Invalid analysis structure: {analysis}")
                        return None
                        
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse JSON response: {e}")
                    self.logger.debug(f"Raw response: {response_text}")
                    return None
            else:
                self.logger.error(f"Ollama request failed: {response.status_code} - {response.text}")
                return None
                
        except requests.RequestException as e:
            self.logger.error(f"Network error during LLM request: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error in LLM integration: {e}")
            return None
            
    def get_last_analysis(self) -> Dict[str, Any]:
        """Get the most recent analysis results."""
        with self._lock:
            return self._last_analysis.copy()
            
    def trigger_manual_analysis(self):
        """Manually trigger an analysis cycle."""
        self.logger.info("Manual analysis triggered")
        self._perform_analysis() 