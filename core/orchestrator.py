"""
Orchestrator Module - Main brain that processes inputs and coordinates actions
"""
import json
import os
import time
from typing import Dict, Optional, Any
from PyQt5.QtCore import QObject, pyqtSignal
import openai
from dotenv import load_dotenv
import threading
import queue
import sys

# Handle Windows-specific ollama import issues
try:
    import ollama
    OLLAMA_AVAILABLE = True
except (OSError, ImportError) as e:
    print(f"Warning: Ollama import failed ({e}). Falling back to OpenAI mode.")
    OLLAMA_AVAILABLE = False
    ollama = None

from modules.ai_core import AIWorker
from modules.audio_listener import AudioListener
from modules.screen_scanner import ScreenScanner
from core.agent_manager import AgentManager


class Orchestrator(QObject):
    """
    Orchestrator acts as the main brain, processing audio transcriptions and screen context
    to determine user intent and coordinate appropriate actions.
    """
    
    # PyQt signals for UI communication
    status_changed = pyqtSignal(str)
    intent_detected = pyqtSignal(str, dict)
    action_completed = pyqtSignal(str, bool)
    model_info_changed = pyqtSignal(str)
    confidence_updated = pyqtSignal(float)
    stream_started = pyqtSignal()
    stream_content_received = pyqtSignal(str)
    stream_ended = pyqtSignal()
    
    def __init__(self, config: dict, visual_stream_class, audio_stream_class, audio_transcriber_class):
        """
        Initialize the Orchestrator with configuration and dependencies.
        """
        super().__init__()
        self.config = config
        self.running = False
        
        # --- Queues for Inter-thread Communication ---
        self.visual_queue = queue.Queue()
        self.audio_queue = queue.Queue()
        self.text_queue = queue.Queue()
        self.raw_audio_queue = queue.Queue()
        self.response_queue = queue.Queue()
        
        # --- AI Worker ---
        self.ai_worker = AIWorker(
            config=self.config,
            visual_queue=self.visual_queue,
            audio_queue=self.audio_queue,
            text_queue=self.text_queue,
            response_queue=self.response_queue
        )
        
        # Thread classes
        self.VisualDataStream = visual_stream_class
        self.AudioDataStream = audio_stream_class
        self.AudioTranscriber = audio_transcriber_class
        
        # Thread instances
        self.visual_thread = None
        self.audio_capture_thread = None
        self.audio_transcriber_thread = None
        
        print("Orchestrator initialized.")
    
    def start(self):
        """Start the orchestrator and begin processing."""
        if not self.running:
            self.running = True
            self.ai_worker.start()
            # Start the response processing loop in a separate thread
            threading.Thread(target=self.process_ai_responses, daemon=True).start()
            self.status_changed.emit("Listening for your cues...")
    
    def stop(self):
        """Stop the orchestrator and all components."""
        print("Orchestrator stopping...")
        self.running = False

        if self.visual_thread and self.visual_thread.is_alive():
            self.visual_thread.stop()
            self.visual_thread.join(timeout=1.0)
        
        if self.audio_capture_thread and self.audio_capture_thread.is_alive():
            self.audio_capture_thread.stop()
            self.audio_capture_thread.join(timeout=1.0)
            
        if self.audio_transcriber_thread and self.audio_transcriber_thread.is_alive():
            self.audio_transcriber_thread.stop()
            self.audio_transcriber_thread.join(timeout=1.0)
        
        if self.ai_worker and self.ai_worker.is_alive():
            self.ai_worker.stop()
            self.ai_worker.join(timeout=1.0)

        self.status_changed.emit("Stopped")
        print("Orchestrator stopped.")
    
    def process_ai_responses(self):
        """
        Main processing loop that checks for new AI responses and updates the UI.
        """
        while self.running:
            try:
                # Blocking get from the queue
                message_type, content = self.response_queue.get(timeout=1)

                if message_type == "STATUS":
                    self.status_changed.emit(content)
                elif message_type == "STREAM_START":
                    self.stream_started.emit()
                elif message_type == "STREAM_CONTENT":
                    self.stream_content_received.emit(content)
                elif message_type == "STREAM_END":
                    self.stream_ended.emit()
                
                self.response_queue.task_done()

            except queue.Empty:
                # This is normal, just continue the loop
                continue
            except Exception as e:
                print(f"Error processing AI response queue: {e}", file=sys.stderr)
                time.sleep(1)

    def submit_manual_input(self, text: str):
        """Submits manual text input to the AI worker."""
        self.text_queue.put(text)
        print(f"Orchestrator submitted manual text: '{text}'")

    def toggle_sight(self, enabled: bool):
        """Toggles the screen scanner thread."""
        self.ai_worker.visual_mode_enabled = enabled
        if enabled:
            if not self.visual_thread or not self.visual_thread.is_alive():
                self.visual_thread = self.VisualDataStream(self.visual_queue, self.config)
                self.visual_thread.start()
                self.status_changed.emit("Sight mode enabled.")
        else:
            if self.visual_thread:
                self.visual_thread.stop()
                self.visual_thread.join()
                self.visual_thread = None
                self.status_changed.emit("Sight mode disabled.")

    def toggle_audio(self, enabled: bool):
        """Toggles the audio capture and transcription threads."""
        if enabled:
            if not self.audio_capture_thread or not self.audio_capture_thread.is_alive():
                self.audio_capture_thread = self.AudioDataStream(self.raw_audio_queue, self.config)
                self.audio_transcriber_thread = self.AudioTranscriber(self.raw_audio_queue, self.audio_queue, self.config)
                self.audio_capture_thread.start()
                self.audio_transcriber_thread.start()
                self.status_changed.emit("Audio mode enabled.")
        else:
            if self.audio_capture_thread:
                self.audio_capture_thread.stop()
                self.audio_capture_thread.join()
                self.audio_capture_thread = None
            if self.audio_transcriber_thread:
                self.audio_transcriber_thread.stop()
                self.audio_transcriber_thread.join()
                self.audio_transcriber_thread = None
            self.status_changed.emit("Audio mode disabled.")

    def force_process_input(self, text: str):
        """
        Force process a text input (useful for testing).
        
        Args:
            text: Text to process as if it were spoken
        """
        self._process_user_input(text) 