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
    
    # New streaming signals
    stream_started = pyqtSignal(str)  # Signal when streaming begins
    stream_chunk = pyqtSignal(str)    # Signal for each chunk of streamed content
    stream_completed = pyqtSignal(str) # Signal when streaming is complete
    stream_error = pyqtSignal(str)    # Signal for streaming errors
    
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
        
        # Track last analysis to avoid empty transcripts
        self._last_transcript_length = 0
        
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
                
            # Check if transcript has meaningful content
            conversation_history = "\n".join(transcript)
            current_length = len(conversation_history.strip())
            min_length = self.config.get('analysis', {}).get('min_analysis_length', 50)
            
            if current_length < min_length:
                self.logger.debug(f"Transcript too short for analysis: {current_length} chars")
                return
                
            # Check if there's been new content since last analysis
            if hasattr(self, '_last_transcript_length'):
                if current_length <= self._last_transcript_length:
                    self.logger.debug("No new conversation content since last analysis")
                    return
                    
                # Require significant new content for analysis
                new_content = current_length - self._last_transcript_length
                if new_content < 30:  # Require at least 30 new characters
                    self.logger.debug(f"Insufficient new content for analysis: {new_content} chars")
                    return
                
            # Limit transcript length to avoid overwhelming the LLM
            max_length = self.config.get('analysis', {}).get('max_transcript_length', 5000)
            if len(conversation_history) > max_length:
                conversation_history = conversation_history[-max_length:]
                
            self.logger.debug(f"Analyzing transcript: {current_length} chars, {len(transcript)} segments")
                
            # Get analysis from LLM
            analysis = self._get_analysis_from_llm(conversation_history)
            
            if analysis:
                with self._lock:
                    self._last_analysis = analysis
                
                # Update last transcript length
                self._last_transcript_length = current_length
                
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
            # Skip analysis if transcript is too short or meaningless
            if len(transcript.strip()) < 20:
                self.logger.debug("Transcript too short for meaningful analysis")
                return None
            
            # Construct the enhanced prompt
            prompt_text = f"""
System: You are Dia, an advanced AI assistant with multimodal capabilities including screen reading (OCR) and audio transcription. You're analyzing a conversation transcript from real-time audio monitoring.

Your capabilities:
- SEE: Read and analyze screen content in real-time
- HEAR: Listen to and transcribe conversations 
- ANALYZE: Process both visual and audio information

Analyze the following conversation transcript and respond ONLY with a single, valid JSON object with three keys: "insights", "topics", and "actions".
- "insights": An array of strings, summarizing the key points and interesting aspects of the conversation
- "topics": An array of key terms, concepts, or subjects mentioned that could be explored further
- "actions": An array of suggested actions the user might want to take, including using your screen reading or conversation analysis capabilities

If the transcript has minimal content, return: {{"insights": ["Conversation in progress"], "topics": [], "actions": ["Continue conversation", "Use screen reader", "Ask me anything"]}}

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
            
            self.logger.debug(f"Sending analysis request to {base_url} for {len(transcript)} chars")
            
            response = requests.post(
                f"{base_url}/api/generate",
                json=ollama_payload,
                timeout=timeout
            )
            
            if response.status_code == 200:
                response_data = response.json()
                response_text = response_data.get('response', '').strip()
                
                self.logger.debug(f"LLM response received: {len(response_text)} chars")
                
                if not response_text:
                    self.logger.warning("Empty response from LLM")
                    return None
                
                # Parse JSON response
                try:
                    analysis = json.loads(response_text)
                    
                    # Handle empty dictionary response
                    if not analysis or analysis == {}:
                        self.logger.warning("LLM returned empty JSON object")
                        return {
                            "insights": ["Minimal conversation detected"],
                            "topics": [],
                            "actions": ["Continue conversation", "Use screen reader", "Ask me anything"]
                        }
                    
                    # Validate structure
                    required_keys = ['insights', 'topics', 'actions']
                    if all(key in analysis for key in required_keys):
                        # Additional validation - ensure arrays are not empty
                        if not analysis['insights'] and not analysis['topics'] and not analysis['actions']:
                            self.logger.warning("LLM returned empty analysis arrays")
                            return {
                                "insights": ["No significant conversation content analyzed"],
                                "topics": [],
                                "actions": ["Continue conversation", "Ask about screen", "Use voice commands"]
                            }
                        return analysis
                    else:
                        missing_keys = [key for key in required_keys if key not in analysis]
                        self.logger.error(f"Invalid analysis structure - missing keys: {missing_keys}")
                        self.logger.debug(f"Received structure: {analysis}")
                        
                        # Return fallback structure instead of None
                        return {
                            "insights": ["Analysis parsing error - I'm still listening and watching"],
                            "topics": [],
                            "actions": ["Try screen reader", "Ask me a question", "Continue conversation"]
                        }
                        
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse JSON response: {e}")
                    self.logger.debug(f"Raw response: {response_text[:200]}...")
                    
                    # Return fallback structure instead of None
                    return {
                        "insights": ["Response parsing error - I can still see and hear"],
                        "topics": [],
                        "actions": ["Use screen reader", "Ask direct question", "Check AI service"]
                    }
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
            
    def process_direct_prompt(self, user_prompt: str) -> Optional[str]:
        """
        Process a direct user prompt and return a simple response.
        This is different from transcript analysis - it's for direct Q&A.
        """
        # Get retry configuration
        ollama_config = self.config.get('ollama', {})
        max_retries = ollama_config.get('max_retries', 2)
        retry_delay = ollama_config.get('retry_delay', 1)
        timeout = ollama_config.get('direct_prompt_timeout', 15)
        
        for attempt in range(max_retries + 1):  # max_retries + initial attempt
            try:
                # Enhanced prompt with capability awareness
                prompt_text = f"""You are Dia, a helpful AI assistant with advanced multimodal capabilities. You can:

- SEE: Read and analyze content on the user's screen in real-time using OCR
- HEAR: Listen to and transcribe audio conversations 
- ANALYZE: Process both visual and audio information

The user is interacting with you through a resizable overlay window that stays on top. You have access to screen content and can hear conversations when audio is enabled.

Respond to the following request clearly and helpfully, keeping in mind your screen reading and audio capabilities:

{user_prompt}"""

                # Prepare Ollama request payload
                ollama_payload = {
                    "model": ollama_config.get('model', 'llama3'),
                    "prompt": prompt_text,
                    "stream": False
                }
                
                # Make request to Ollama API
                base_url = ollama_config.get('base_url', 'http://localhost:11434')
                
                if attempt > 0:
                    self.logger.info(f"Retry attempt {attempt}/{max_retries} for direct prompt")
                    
                self.logger.debug(f"Sending direct prompt request (attempt {attempt + 1})")
                
                response = requests.post(
                    f"{base_url}/api/generate",
                    json=ollama_payload,
                    timeout=timeout
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    response_text = response_data.get('response', '').strip()
                    
                    if response_text:
                        self.logger.info(f"Direct prompt processed successfully (attempt {attempt + 1})")
                        return response_text
                    else:
                        self.logger.warning(f"Empty response from LLM (attempt {attempt + 1})")
                        if attempt == max_retries:
                            return "I received your request but couldn't generate a response."
                else:
                    self.logger.error(f"Ollama request failed: {response.status_code} - {response.text}")
                    if attempt == max_retries:
                        return f"Service error (status {response.status_code}). Check if Ollama is running."
                    
            except requests.Timeout:
                self.logger.error(f"LLM request timed out (attempt {attempt + 1}/{max_retries + 1})")
                if attempt == max_retries:
                    return "Request timed out. The AI service may be slow or unavailable."
                else:
                    self.logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    
            except requests.ConnectionError:
                self.logger.error(f"Cannot connect to Ollama service (attempt {attempt + 1})")
                if attempt == max_retries:
                    return "Cannot connect to AI service. Please check if Ollama is running on localhost:11434."
                else:
                    self.logger.info(f"Retrying connection in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    
            except requests.RequestException as e:
                self.logger.error(f"Network error during LLM request: {e} (attempt {attempt + 1})")
                if attempt == max_retries:
                    return f"Network error: {str(e)}"
                else:
                    time.sleep(retry_delay)
                    
            except Exception as e:
                self.logger.error(f"Unexpected error processing prompt: {e}")
                return f"Unexpected error: {str(e)}"
        
        return "Maximum retry attempts reached. Please try again later."
            
    def process_direct_prompt_streaming_with_screen(self, user_prompt: str, screen_content: str, stream_id: str = "default") -> bool:
        """
        Process a direct user prompt with current screen content and streaming response.
        Returns True if stream started successfully, False otherwise.
        
        Args:
            user_prompt: The user's prompt to process
            screen_content: Current screen content for AI context
            stream_id: Identifier for this stream (for UI tracking)
        """
        try:
            # Enhanced prompt with capability awareness and actual screen content
            prompt_text = f"""You are Dia, a helpful AI assistant with advanced multimodal capabilities. You can:

- SEE: Read and analyze content on the user's screen in real-time using OCR
- HEAR: Listen to and transcribe audio conversations 
- ANALYZE: Process both visual and audio information

The user is interacting with you through a resizable overlay window that stays on top. You have access to screen content and can hear conversations when audio is enabled.

CURRENT SCREEN CONTENT:
---
{screen_content}
---

Based on what you can see on the screen above and the user's request below, respond clearly and helpfully:

USER REQUEST: {user_prompt}

Important: You can actually see the screen content above. Reference specific elements, text, or applications you see when relevant to the user's question."""

            # Prepare Ollama request payload for streaming
            ollama_config = self.config.get('ollama', {})
            ollama_payload = {
                "model": ollama_config.get('model', 'llama3'),
                "prompt": prompt_text,
                "stream": True  # Enable streaming
            }
            
            # Make streaming request to Ollama API
            base_url = ollama_config.get('base_url', 'http://localhost:11434')
            timeout = ollama_config.get('direct_prompt_timeout', 15)
            
            self.logger.debug(f"Starting streaming request with screen content for prompt: {user_prompt[:50]}...")
            
            # Emit stream started signal
            self.stream_started.emit(stream_id)
            
            response = requests.post(
                f"{base_url}/api/generate",
                json=ollama_payload,
                timeout=timeout,
                stream=True  # Enable response streaming
            )
            
            if response.status_code == 200:
                complete_response = ""
                
                # Process streaming response line by line
                for line in response.iter_lines():
                    if line:
                        try:
                            # Parse JSON from each line
                            chunk_data = json.loads(line.decode('utf-8'))
                            
                            # Extract the response chunk
                            response_chunk = chunk_data.get('response', '')
                            
                            if response_chunk:
                                complete_response += response_chunk
                                # Emit chunk signal for real-time UI updates
                                self.stream_chunk.emit(response_chunk)
                            
                            # Check if streaming is done
                            if chunk_data.get('done', False):
                                self.logger.info(f"Streaming with screen content completed: {len(complete_response)} chars")
                                self.stream_completed.emit(complete_response)
                                return True
                                
                        except json.JSONDecodeError as e:
                            self.logger.error(f"Error parsing streaming chunk: {e}")
                            continue
                
                # If we get here, stream ended without 'done' signal
                self.stream_completed.emit(complete_response)
                return True
                
            else:
                error_msg = f"Streaming request failed: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                self.stream_error.emit(error_msg)
                return False
                
        except requests.Timeout:
            error_msg = "Streaming request timed out. The AI service may be slow or unavailable."
            self.logger.error(error_msg)
            self.stream_error.emit(error_msg)
            return False
            
        except requests.ConnectionError:
            error_msg = "Cannot connect to AI service. Please check if Ollama is running."
            self.logger.error(error_msg)
            self.stream_error.emit(error_msg)
            return False
            
        except requests.RequestException as e:
            error_msg = f"Network error during streaming: {str(e)}"
            self.logger.error(error_msg)
            self.stream_error.emit(error_msg)
            return False
            
        except Exception as e:
            error_msg = f"Unexpected error during streaming: {str(e)}"
            self.logger.error(error_msg)
            self.stream_error.emit(error_msg)
            return False
            
    def process_direct_prompt_streaming(self, user_prompt: str, stream_id: str = "default") -> bool:
        """
        Process a direct user prompt with streaming response.
        Returns True if stream started successfully, False otherwise.
        
        Args:
            user_prompt: The user's prompt to process
            stream_id: Identifier for this stream (for UI tracking)
        """
        try:
            # Enhanced prompt with capability awareness
            prompt_text = f"""You are Dia, a helpful AI assistant with advanced multimodal capabilities. You can:

- SEE: Read and analyze content on the user's screen in real-time using OCR
- HEAR: Listen to and transcribe audio conversations 
- ANALYZE: Process both visual and audio information

The user is interacting with you through a resizable overlay window that stays on top. You have access to screen content and can hear conversations when audio is enabled.

Respond to the following request clearly and helpfully, keeping in mind your screen reading and audio capabilities:

{user_prompt}"""

            # Prepare Ollama request payload for streaming
            ollama_config = self.config.get('ollama', {})
            ollama_payload = {
                "model": ollama_config.get('model', 'llama3'),
                "prompt": prompt_text,
                "stream": True  # Enable streaming
            }
            
            # Make streaming request to Ollama API
            base_url = ollama_config.get('base_url', 'http://localhost:11434')
            timeout = ollama_config.get('direct_prompt_timeout', 15)
            
            self.logger.debug(f"Starting streaming request for prompt: {user_prompt[:50]}...")
            
            # Emit stream started signal
            self.stream_started.emit(stream_id)
            
            response = requests.post(
                f"{base_url}/api/generate",
                json=ollama_payload,
                timeout=timeout,
                stream=True  # Enable response streaming
            )
            
            if response.status_code == 200:
                complete_response = ""
                
                # Process streaming response line by line
                for line in response.iter_lines():
                    if line:
                        try:
                            # Parse JSON from each line
                            chunk_data = json.loads(line.decode('utf-8'))
                            
                            # Extract the response chunk
                            response_chunk = chunk_data.get('response', '')
                            
                            if response_chunk:
                                complete_response += response_chunk
                                # Emit chunk signal for real-time UI updates
                                self.stream_chunk.emit(response_chunk)
                            
                            # Check if streaming is done
                            if chunk_data.get('done', False):
                                self.logger.info(f"Streaming completed: {len(complete_response)} chars")
                                self.stream_completed.emit(complete_response)
                                return True
                                
                        except json.JSONDecodeError as e:
                            self.logger.error(f"Error parsing streaming chunk: {e}")
                            continue
                
                # If we get here, stream ended without 'done' signal
                self.stream_completed.emit(complete_response)
                return True
                
            else:
                error_msg = f"Streaming request failed: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                self.stream_error.emit(error_msg)
                return False
                
        except requests.Timeout:
            error_msg = "Streaming request timed out. The AI service may be slow or unavailable."
            self.logger.error(error_msg)
            self.stream_error.emit(error_msg)
            return False
            
        except requests.ConnectionError:
            error_msg = "Cannot connect to AI service. Please check if Ollama is running."
            self.logger.error(error_msg)
            self.stream_error.emit(error_msg)
            return False
            
        except requests.RequestException as e:
            error_msg = f"Network error during streaming: {str(e)}"
            self.logger.error(error_msg)
            self.stream_error.emit(error_msg)
            return False
            
        except Exception as e:
            error_msg = f"Unexpected error during streaming: {str(e)}"
            self.logger.error(error_msg)
            self.stream_error.emit(error_msg)
            return False
            
    def trigger_manual_analysis(self):
        """Manually trigger an analysis cycle."""
        self.logger.info("Manual analysis triggered")
        self._perform_analysis()
    
    def debug_transcript_status(self):
        """Debug method to check transcript status."""
        if not self.audio_listener:
            self.logger.info("Debug: No audio listener available")
            return
            
        transcript = self.audio_listener.get_transcript()
        conversation_history = "\n".join(transcript) if transcript else ""
        
        self.logger.info(f"Debug: Transcript segments: {len(transcript) if transcript else 0}")
        self.logger.info(f"Debug: Total characters: {len(conversation_history)}")
        self.logger.info(f"Debug: Recent content: {conversation_history[-100:] if conversation_history else 'None'}")
        
        return {
            'segment_count': len(transcript) if transcript else 0,
            'total_chars': len(conversation_history),
            'is_listening': self.audio_listener.is_listening() if hasattr(self.audio_listener, 'is_listening') else False
        } 