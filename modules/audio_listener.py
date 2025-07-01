"""
Audio Listener Module
Continuously captures and transcribes speech for real-time conversation analysis.
"""

import speech_recognition as sr
import threading
import logging
import time
from typing import List, Dict, Any
import queue

class AudioListener:
    """
    Continuously listens to microphone input and maintains a running transcript.
    Thread-safe implementation for concurrent access by the Orchestrator.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Audio configuration
        self.sample_rate = config.get('audio', {}).get('sample_rate', 16000)
        self.chunk_size = config.get('audio', {}).get('chunk_size', 1024)
        self.channels = config.get('audio', {}).get('channels', 1)
        
        # Initialize speech recognition
        self.recognizer = sr.Recognizer()
        self.microphone = None
        
        # Thread-safe transcript storage
        self._transcript_lock = threading.Lock()
        self._transcript_segments = []
        self._max_segments = 100  # Limit memory usage
        
        # Threading control
        self._listening_thread = None
        self._is_listening = False
        self._stop_event = threading.Event()
        
        # Audio processing queue
        self._audio_queue = queue.Queue()
        self._processing_thread = None
        
        self.logger.info("AudioListener initialized")
        
    def start_listening(self):
        """Start continuous audio listening and transcription."""
        if self._is_listening:
            self.logger.warning("Audio listener is already running")
            return
            
        try:
            # Initialize microphone
            self.microphone = sr.Microphone(
                sample_rate=self.sample_rate,
                chunk_size=self.chunk_size
            )
            
            # Adjust for ambient noise
            with self.microphone as source:
                self.logger.info("Adjusting for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                
            self._is_listening = True
            self._stop_event.clear()
            
            # Start listening and processing threads
            self._listening_thread = threading.Thread(
                target=self._listen_continuously,
                daemon=True
            )
            self._processing_thread = threading.Thread(
                target=self._process_audio_continuously,
                daemon=True
            )
            
            self._listening_thread.start()
            self._processing_thread.start()
            
            self.logger.info("Audio listening started")
            
        except Exception as e:
            self.logger.error(f"Failed to start audio listening: {e}")
            self._is_listening = False
            
    def stop_listening(self):
        """Stop audio listening and transcription."""
        if not self._is_listening:
            return
            
        self._is_listening = False
        self._stop_event.set()
        
        # Wait for threads to finish
        if self._listening_thread and self._listening_thread.is_alive():
            self._listening_thread.join(timeout=2)
            
        if self._processing_thread and self._processing_thread.is_alive():
            self._processing_thread.join(timeout=2)
            
        self.logger.info("Audio listening stopped")
        
    def _listen_continuously(self):
        """Continuously listen for audio and queue it for processing."""
        try:
            with self.microphone as source:
                while self._is_listening and not self._stop_event.is_set():
                    try:
                        # Listen for audio with timeout
                        audio = self.recognizer.listen(
                            source,
                            timeout=1,
                            phrase_time_limit=5
                        )
                        
                        # Queue audio for processing
                        self._audio_queue.put(audio)
                        
                    except sr.WaitTimeoutError:
                        # Timeout is expected, continue listening
                        continue
                    except Exception as e:
                        self.logger.error(f"Error during audio capture: {e}")
                        time.sleep(0.1)
                        
        except Exception as e:
            self.logger.error(f"Critical error in listening thread: {e}")
            
    def _process_audio_continuously(self):
        """Process queued audio for speech recognition."""
        while self._is_listening and not self._stop_event.is_set():
            try:
                # Get audio from queue with timeout
                audio = self._audio_queue.get(timeout=1)
                
                # Perform speech recognition
                try:
                    text = self.recognizer.recognize_google(audio)
                    if text.strip():
                        self._add_to_transcript(text.strip())
                        self.logger.debug(f"Transcribed: {text[:50]}...")
                        
                except sr.UnknownValueError:
                    # Speech was unintelligible, ignore
                    pass
                except sr.RequestError as e:
                    self.logger.error(f"Speech recognition request failed: {e}")
                    
                # Mark task as done
                self._audio_queue.task_done()
                
            except queue.Empty:
                # No audio to process, continue
                continue
            except Exception as e:
                self.logger.error(f"Error processing audio: {e}")
                
    def _add_to_transcript(self, text: str):
        """
        Add transcribed text to the running transcript.
        
        Args:
            text: Transcribed text to add
        """
        with self._transcript_lock:
            # Add timestamp and text
            timestamp = time.time()
            segment = {
                'timestamp': timestamp,
                'text': text
            }
            
            self._transcript_segments.append(segment)
            
            # Limit the number of stored segments
            if len(self._transcript_segments) > self._max_segments:
                self._transcript_segments = self._transcript_segments[-self._max_segments:]
                
            self.logger.debug(f"Added to transcript: {text}")
            
    def get_transcript(self) -> List[str]:
        """
        Get the current conversation transcript.
        
        Returns:
            List of transcribed text segments
        """
        with self._transcript_lock:
            return [segment['text'] for segment in self._transcript_segments]
            
    def get_recent_transcript(self, seconds: int = 60) -> List[str]:
        """
        Get transcript from the last N seconds.
        
        Args:
            seconds: Number of seconds to look back
            
        Returns:
            List of recent transcribed text segments
        """
        cutoff_time = time.time() - seconds
        
        with self._transcript_lock:
            recent_segments = [
                segment['text'] 
                for segment in self._transcript_segments 
                if segment['timestamp'] >= cutoff_time
            ]
            return recent_segments
            
    def clear_transcript(self):
        """Clear the current transcript."""
        with self._transcript_lock:
            self._transcript_segments.clear()
            self.logger.info("Transcript cleared")
            
    def get_transcript_count(self) -> int:
        """Get the number of transcript segments."""
        with self._transcript_lock:
            return len(self._transcript_segments)
            
    def is_listening(self) -> bool:
        """Check if the audio listener is currently active."""
        return self._is_listening 