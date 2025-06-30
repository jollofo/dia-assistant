"""
Audio Listener Module - Captures microphone input and transcribes speech
"""
import threading
import queue
import speech_recognition as sr
import json
import time
from typing import Optional


class AudioListener:
    """
    AudioListener captures microphone input in a background thread and transcribes 
    speech to text, placing results in a thread-safe queue.
    """
    
    def __init__(self, config: dict):
        """
        Initialize the AudioListener with configuration parameters.
        
        Args:
            config: Dictionary containing audio configuration settings
        """
        self.config = config.get('audio', {})
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.transcription_queue = queue.Queue()
        self.is_listening = False
        self.listen_thread = None
        
        # Configure recognizer settings
        self.recognizer.energy_threshold = self.config.get('energy_threshold', 300)
        self.recognizer.pause_threshold = self.config.get('pause_threshold', 1.0)
        
        # Adjust for ambient noise
        print("Adjusting for ambient noise...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
        print("Audio listener initialized.")
    
    def start_listening(self):
        """Start the background listening thread."""
        if not self.is_listening:
            self.is_listening = True
            self.listen_thread = threading.Thread(target=self._listen_continuously)
            self.listen_thread.daemon = True
            self.listen_thread.start()
            print("Audio listening started.")
    
    def stop_listening(self):
        """Stop the background listening thread."""
        self.is_listening = False
        if self.listen_thread:
            self.listen_thread.join(timeout=2.0)
        print("Audio listening stopped.")
    
    def get_transcription(self) -> Optional[str]:
        """
        Get the next transcribed text from the queue.
        
        Returns:
            str: The transcribed text, or None if queue is empty
        """
        try:
            return self.transcription_queue.get_nowait()
        except queue.Empty:
            return None
    
    def _listen_continuously(self):
        """
        Main listening loop that runs in the background thread.
        Continuously listens for speech and transcribes it.
        """
        timeout = self.config.get('timeout', 5.0)
        
        while self.is_listening:
            try:
                # Listen for audio with timeout
                with self.microphone as source:
                    print("Listening for speech...")
                    audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=10)
                
                # Attempt to transcribe
                try:
                    text = self.recognizer.recognize_google(audio)
                    if text.strip():  # Only add non-empty transcriptions
                        print(f"Transcribed: {text}")
                        self.transcription_queue.put(text)
                
                except sr.UnknownValueError:
                    # Speech was unintelligible
                    print("Could not understand audio")
                except sr.RequestError as e:
                    # Error with the speech recognition service
                    print(f"Speech recognition error: {e}")
                    time.sleep(1)  # Brief pause before retrying
                    
            except sr.WaitTimeoutError:
                # No speech detected within timeout - this is normal
                pass
            except Exception as e:
                print(f"Unexpected error in audio listener: {e}")
                time.sleep(1)  # Brief pause before retrying 