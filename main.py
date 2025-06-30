import sys
import json
import os
import queue
import threading
import time
import signal
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

from modules.screen_scanner import ScreenScanner
from modules.audio_stream import AudioDataStream, AudioTranscriber
from modules.ai_core import AIWorker
from ui.overlay import OverlayWindow
from core.orchestrator import Orchestrator

class DiaApplication:
    def __init__(self):
        self.config = self._load_config()
        self._validate_system()

        # --- Core Components ---
        # The Orchestrator now creates and manages all worker threads and queues.
        self.orchestrator = Orchestrator(
            config=self.config,
            visual_stream_class=VisualDataStream,
            audio_stream_class=AudioDataStream,
            audio_transcriber_class=AudioTranscriber
        )
        
        # --- App and UI ---
        self.app = QApplication(sys.argv)
        self.overlay = OverlayWindow()
        self._connect_signals()
        
        signal.signal(signal.SIGINT, self.shutdown)

    def _load_config(self):
        try:
            with open('config.json', 'r') as f: return json.load(f)
        except Exception as e:
            print(f"FATAL: Could not load config.json: {e}", file=sys.stderr); sys.exit(1)

    def _validate_system(self):
        # Basic validation, can be expanded
        if not os.path.exists(self.config.get("TESSERACT_CMD_PATH", "")):
            print("FATAL: Tesseract path in config.json is invalid.", file=sys.stderr); sys.exit(1)
        print("System validation passed.")

    def _connect_signals(self):
        # UI -> Orchestrator
        self.overlay.sight_mode_toggled.connect(self.orchestrator.toggle_sight)
        self.overlay.audio_mode_toggled.connect(self.orchestrator.toggle_audio)
        self.overlay.text_input_submitted.connect(self.orchestrator.submit_manual_input)
        self.overlay.close_requested.connect(self.shutdown)

        # Orchestrator -> UI
        self.orchestrator.status_changed.connect(self.overlay.update_status)
        self.orchestrator.stream_started.connect(self.overlay._on_stream_start)
        self.orchestrator.stream_content_received.connect(self.overlay._on_stream_content)
        self.orchestrator.stream_ended.connect(self.overlay._on_stream_end)
        
        # App Lifecycle
        self.app.aboutToQuit.connect(self.shutdown)

    def run(self):
        print("Dia AI Assistant is running.")
        self.orchestrator.start()
        self.overlay.show()
        sys.exit(self.app.exec_())

    def shutdown(self, *args):
        print("Shutting down all threads...")
        try:
            self.orchestrator.stop()
            print("Shutdown complete.")
        except Exception as e:
            print(f"Error during shutdown: {e}")
        finally:
            self.app.quit()

    def toggle_sight_mode(self, enabled):
        if enabled:
            if not self.visual_thread:
                self.visual_thread = VisualDataStream(self.q_visual, self.config)
                self.visual_thread.start()
                self.overlay.update_status("Sight mode enabled.")
        else:
            if self.visual_thread:
                self.visual_thread.stop()
                self.visual_thread.join()
                self.visual_thread = None
                self.overlay.update_status("Sight mode disabled.")

    def toggle_audio_mode(self, enabled):
        if enabled:
            if not self.audio_capture_thread:
                self.audio_capture_thread = AudioDataStream(self.q_raw_audio, self.config)
                self.audio_transcriber_thread = AudioTranscriber(self.q_raw_audio, self.q_audio_text, self.config)
                self.audio_capture_thread.start()
                self.audio_transcriber_thread.start()
                self.overlay.update_status("Audio mode enabled.")
        else:
            if self.audio_capture_thread:
                self.audio_capture_thread.stop(); self.audio_capture_thread.join()
                self.audio_transcriber_thread.stop(); self.audio_transcriber_thread.join()
                self.audio_capture_thread = None
                self.audio_transcriber_thread = None
                self.overlay.update_status("Audio mode disabled.")

    def submit_text_to_ai(self, text):
        print(f"DEBUG: Submitting text to AI: '{text}'")
        self.orchestrator.submit_manual_input(text)
        self.overlay.show_spinner()

if __name__ == '__main__':
    # This placeholder class is here to represent the screen scanning functionality.
    class VisualDataStream(threading.Thread):
        def __init__(self, q, c):
            super().__init__(daemon=True)
            self.output_queue = q
            self.config = c
            self.running = True
            self.scanner = ScreenScanner(self.config)
            self.last_text = ""
            self.last_update_time = 0
            self.force_update_interval = 10  # Force update every 10 seconds
            print("VisualDataStream initialized.")

        def _text_similarity(self, text1, text2):
            """Calculate simple similarity between two texts."""
            if not text1 or not text2:
                return 0
            
            # Simple word-based similarity
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())
            
            if not words1 and not words2:
                return 1
            if not words1 or not words2:
                return 0
                
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            return len(intersection) / len(union) if union else 0

        def run(self):
            while self.running:
                try:
                    text = self.scanner.capture_and_ocr()
                    current_time = time.time()
                    
                    if text and len(text.strip()) > 10:
                        # Check if text is significantly different OR enough time has passed
                        similarity = self._text_similarity(text, self.last_text)
                        time_since_last = current_time - self.last_update_time
                        
                        # Send update if:
                        # 1. Text is significantly different (similarity < 0.7)
                        # 2. OR enough time has passed since last update (force refresh)
                        if similarity < 0.7 or time_since_last > self.force_update_interval:
                            print(f"[VisualDataStream] Screen change detected (similarity: {similarity:.2f})")
                            self.output_queue.put(text)
                            self.last_text = text
                            self.last_update_time = current_time
                    
                    time.sleep(2)
                except Exception as e:
                    print(f"Error in VisualDataStream: {e}", file=sys.stderr)
                    time.sleep(5)
        
        def stop(self):
            self.running = False
            print("VisualDataStream stopped.")

    assistant = DiaApplication()
    assistant.run() 