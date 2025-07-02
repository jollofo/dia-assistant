"""
Dia AI Assistant - Main Application
Entry point for the Dia AI Assistant application.
"""

import sys
import json
import logging
import os
import traceback
from typing import Dict, Any, Optional, List
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, QObject, pyqtSignal, QThread

# Import core modules
from core.orchestrator import Orchestrator
from core.agent_manager import AgentManager

# Import feature modules
from modules.audio_listener import AudioListener
from modules.screen_scanner import ScreenScanner

# Import UI
from ui.overlay import OverlayWindow

class Worker(QObject):
    """
    Generic worker to run a task in a separate thread.
    """
    finished = pyqtSignal(object)
    error = pyqtSignal(tuple)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        """Execute the worker's task."""
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            # Note: A logger instance won't exist here if not passed.
            # Printing to stderr is a safe fallback.
            print(f"Worker task failed: {e}")
            self.error.emit((e, traceback.format_exc()))

class DiaAssistant(QObject):
    """
    Main application class that coordinates all components of the Dia AI Assistant.
    """
    
    # Qt signals for thread-safe UI updates
    screen_change_detected = pyqtSignal(str)
    
    def __init__(self):
        """Initialize the Dia AI Assistant."""
        super().__init__()  # Initialize QObject
        
        # Setup logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self.config = self._load_config()
        
        # Initialize components
        self.app = None
        self.orchestrator = None
        self.agent_manager = None
        self.audio_listener = None
        self.screen_scanner = None
        self.overlay_window = None
        
        # Threading management - track active threads for proper cleanup
        self._active_threads: List[QThread] = []
        self._active_workers: List[Worker] = []
        self._is_shutting_down = False
        
        # State tracking
        self.audio_active = False
        
        self.logger.info("Dia AI Assistant initialized")
        
    def _setup_logging(self):
        """Configure logging for the application."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('dia_assistant.log')
            ]
        )
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from config.json."""
        try:
            config_path = 'config.json'
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                print(f"Configuration loaded from {config_path}")
                return config
            else:
                print(f"Config file {config_path} not found, using defaults")
                return self._get_default_config()
        except Exception as e:
            print(f"Error loading configuration: {e}")
            return self._get_default_config()
            
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "ollama": {
                "base_url": "http://localhost:11434",
                "model": "gemma3:latest",
                "timeout": 20
            },
            "audio": {
                "sample_rate": 16000,
                "chunk_size": 1024,
                "channels": 1
            },
            "ui": {
                "overlay_width": 400,
                "overlay_height": 300,
                "transparency": 0.95,
                "position": {"x": 50, "y": 50}
            },
            "analysis": {
                "interval_seconds": 15,
                "max_transcript_length": 5000
            }
        }
        
    def initialize_components(self):
        """Initialize all application components."""
        try:
            self.logger.info("Initializing application components...")
            
            # Initialize PyQt6 application
            self.app = QApplication(sys.argv)
            self.app.setQuitOnLastWindowClosed(False)
            
            # Connect application aboutToQuit signal for proper cleanup
            self.app.aboutToQuit.connect(self._cleanup_threads)
            
            # Initialize core components
            self.agent_manager = AgentManager(self.config)
            self.audio_listener = AudioListener(self.config)
            self.screen_scanner = ScreenScanner(self.config)
            
            # Initialize orchestrator with audio listener reference
            self.orchestrator = Orchestrator(self.config, self.audio_listener)
            
            # Initialize UI
            self.overlay_window = OverlayWindow(self.config)
            
            # Setup signal connections
            self._setup_signal_connections()
            
            self.logger.info("All components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            raise
            
    def _setup_signal_connections(self):
        """Setup signal/slot connections between components."""
        # Connect orchestrator analysis updates to UI
        self.orchestrator.analysis_updated.connect(self.overlay_window.update_display)
        
        # Connect orchestrator errors to error handler
        self.orchestrator.error_occurred.connect(self._handle_error)
        
        # Connect UI OCR requests to screen scanner
        self.overlay_window.ocr_requested.connect(self._handle_ocr_request)
        
        # Connect UI audio toggle requests
        self.overlay_window.audio_toggle_requested.connect(self._handle_audio_toggle)
        
        # Connect UI text prompt submissions
        self.overlay_window.text_prompt_submitted.connect(self._handle_text_prompt)
        
        # Connect window close to application shutdown
        self.overlay_window.window_closed.connect(self._handle_window_closed)
        
        # Connect screen change signal for thread-safe UI updates
        self.screen_change_detected.connect(self._handle_screen_change_safe)
        
        self.logger.info("Signal connections established")
        
    def _run_task_in_background(self, target_func, on_finish_slot, *args, **kwargs):
        """
        Runs a given function in a background thread and connects the result to a slot.
        Now properly tracks threads for cleanup.
        """
        if self._is_shutting_down:
            self.logger.warning("Ignoring background task request during shutdown")
            return
            
        thread = QThread()
        worker = Worker(target_func, *args, **kwargs)
        worker.moveToThread(thread)

        # Store references for cleanup
        self._active_threads.append(thread)
        self._active_workers.append(worker)

        # Connect signals
        thread.started.connect(worker.run)
        worker.finished.connect(on_finish_slot)
        worker.error.connect(self._handle_worker_error)
        
        # Clean up thread when worker finishes
        def cleanup_thread():
            try:
                if thread in self._active_threads:
                    self._active_threads.remove(thread)
                if worker in self._active_workers:
                    self._active_workers.remove(worker)
                    
                # Properly quit and wait for thread
                thread.quit()
                if thread.isRunning():
                    thread.wait(5000)  # Wait up to 5 seconds
                    
            except Exception as e:
                self.logger.error(f"Error cleaning up thread: {e}")
        
        worker.finished.connect(cleanup_thread)
        worker.error.connect(cleanup_thread)

        # Start the thread
        thread.start()

    def _handle_worker_error(self, error_info: tuple):
        """Handle errors from background workers."""
        error, traceback_str = error_info
        self.logger.error(f"Background worker error: {error}\n{traceback_str}")
        
        if self.overlay_window:
            self.overlay_window.add_response("❌ Task Error", 
                                            f"Background task failed: {str(error)[:100]}", 
                                            ["Try again", "Check logs"])

    def _cleanup_threads(self):
        """Clean up all active threads during shutdown."""
        if self._is_shutting_down:
            return  # Avoid recursive calls
            
        self._is_shutting_down = True
        self.logger.info(f"Cleaning up {len(self._active_threads)} active threads...")
        
        # Stop all active threads
        for thread in self._active_threads[:]:  # Create a copy to iterate
            try:
                if thread.isRunning():
                    thread.quit()
                    # Wait for thread to finish with timeout
                    if not thread.wait(3000):  # 3 second timeout
                        self.logger.warning("Thread did not finish gracefully, terminating")
                        thread.terminate()
                        thread.wait(1000)  # Give it 1 more second
                        
            except Exception as e:
                self.logger.error(f"Error stopping thread: {e}")
        
        # Clear the lists
        self._active_threads.clear()
        self._active_workers.clear()
        
        self.logger.info("Thread cleanup completed")

    def _handle_ocr_request(self):
        """
        Handle OCR requests from the UI with improved speed and error handling.
        Now also manages continuous screen monitoring.
        """
        try:
            self.logger.info("OCR request received - checking monitoring status")
            
            # Check if we're toggling monitoring or doing single capture
            if hasattr(self, '_screen_monitoring_active'):
                is_currently_monitoring = self._screen_monitoring_active
            else:
                is_currently_monitoring = False
                self._screen_monitoring_active = False
            
            # Fast response for missing tesseract
            if not hasattr(self, '_tesseract_checked'):
                # Quick check if tesseract is available
                try:
                    import subprocess
                    subprocess.run(['tesseract', '--version'], capture_output=True, timeout=2)
                    self._tesseract_checked = True
                except:
                    self._tesseract_checked = False
                    
            if not self._tesseract_checked:
                self.overlay_window.add_response(
                    "❌ OCR Unavailable", 
                    "Tesseract OCR not found in system PATH. Install from github.com/UB-Mannheim/tesseract/wiki",
                    ["Add to PATH after install", "Restart application"]
                )
                return
            
            # Toggle continuous monitoring
            if not is_currently_monitoring:
                # Start continuous monitoring
                self._start_screen_monitoring()
            else:
                # Stop continuous monitoring and do single capture
                self._stop_screen_monitoring()
                self._perform_single_screen_capture()
                
        except Exception as e:
            self.logger.error(f"OCR error: {e}")
            self.overlay_window.add_response("❌ Error", f"OCR failed: {str(e)[:30]}...", 
                                            ["Check system"])
            
    def _start_screen_monitoring(self):
        """Start continuous screen monitoring."""
        try:
            self.logger.info("Starting continuous screen monitoring")
            self._screen_monitoring_active = True
            
            # Update UI to show monitoring active
            self.overlay_window.set_monitoring_active(True)
            
            # Start monitoring with thread-safe callback
            self.screen_scanner.start_continuous_monitoring(
                change_callback=self._screen_change_callback
            )
            
            self.overlay_window.add_response(
                "👁 Screen Monitor Active", 
                "I'm now continuously watching your screen for changes. I'll notify you when I detect significant changes in content.",
                ["Stop monitoring", "View current content", "Ask about screen"]
            )
            
        except Exception as e:
            self.logger.error(f"Error starting screen monitoring: {e}")
            self._screen_monitoring_active = False
            self.overlay_window.add_response("❌ Monitor Error", 
                                            f"Failed to start monitoring: {str(e)}", 
                                            ["Try again", "Check system"])
                                            
    def _stop_screen_monitoring(self):
        """Stop continuous screen monitoring."""
        try:
            self.logger.info("Stopping continuous screen monitoring")
            self._screen_monitoring_active = False
            
            # Update UI to show monitoring stopped
            self.overlay_window.set_monitoring_active(False)
            
            self.screen_scanner.stop_continuous_monitoring()
            
            self.overlay_window.add_response(
                "👁 Screen Monitor Stopped", 
                "Screen monitoring has been stopped. Click the eye button again to capture a single screenshot or restart monitoring.",
                ["Single capture", "Restart monitoring", "Ask about last seen"]
            )
            
        except Exception as e:
            self.logger.error(f"Error stopping screen monitoring: {e}")
            self.overlay_window.add_response("❌ Monitor Error", 
                                            f"Error stopping monitoring: {str(e)}", 
                                            ["Force stop", "Restart"])
                                            
    def _screen_change_callback(self, screen_content: str):
        """
        Thread-safe callback for screen changes.
        This method runs in the background thread and emits a signal.
        
        Args:
            screen_content: The new screen content that was detected
        """
        # Emit signal to handle on main thread
        self.screen_change_detected.emit(screen_content)
        
    def _handle_screen_change_safe(self, screen_content: str):
        """
        Handle detected screen content changes (runs on main thread).
        This method now starts a background task for analysis.
        
        Args:
            screen_content: The new screen content that was detected
        """
        self.logger.info("Screen content change detected, starting background analysis.")
        self.overlay_window.show_message("🧠 Analyzing...", "Screen change detected...")
        
        # Enhanced analysis prompt for screen changes
        analysis_prompt = f"""I'm Dia, continuously monitoring your screen. I just detected a significant change in your screen content:

NEW SCREEN CONTENT:
---
{screen_content[:1500]}
---

Please analyze this updated content and provide:
- What type of change occurred (new window, content update, navigation, etc.)
- Key information now visible on screen
- Any important insights or patterns
- Suggestions for actions the user might want to take

Provide a helpful summary of what changed and what's now visible."""
        
        self._run_task_in_background(
            self.orchestrator.process_direct_prompt,
            self._handle_screen_analysis_complete,
            analysis_prompt
        )

    def _handle_screen_analysis_complete(self, response: Optional[str]):
        """Handle the result from the background screen analysis."""
        if response:
            self.overlay_window.add_response(
                "🔄 Screen Change Detected", 
                response,
                ["Continue monitoring", "Stop monitoring", "Ask follow-up"]
            )
        else:
            self.overlay_window.add_response(
                "🔄 Screen Updated", 
                "I detected a screen change but couldn't analyze it.",
                ["What's on screen?", "Continue monitoring", "Stop monitoring"]
            )
            
    def _perform_single_screen_capture(self):
        """
        Perform a single screen capture and analysis using background threads
        to keep the UI responsive.
        """
        self.logger.info("Starting non-blocking single screen capture.")
        self.overlay_window.show_message("👁 Capturing...", "Reading screen content...")
        
        self._run_task_in_background(
            self.screen_scanner.capture_and_extract_text,
            self._handle_ocr_complete
        )

    def _handle_ocr_complete(self, screen_text: Optional[str]):
        """
        Callback for when OCR extraction is complete. This method then
        triggers the AI analysis in another background thread.
        """
        # Handle OCR errors first
        if not screen_text or "Tesseract OCR not installed" in screen_text:
            self.overlay_window.add_response(
                "❌ OCR Error", 
                "Install Tesseract OCR and add to PATH",
                ["Download installer", "Restart after install"]
            )
            return
            
        if screen_text.startswith("OCR_ERROR:"):
            error_details = screen_text.replace("OCR_ERROR: ", "")[:50] + "..."
            self.overlay_window.add_response(
                "❌ OCR Error", 
                f"Configuration issue: {error_details}",
                ["Check installation", "Verify PATH"]
            )
            return
        
        if len(screen_text.strip()) > 10:
            self.overlay_window.show_message("🧠 Analyzing...", "Screen captured, processing...")
            
            analysis_prompt = f"""I am Dia, an AI assistant that can see your screen in real-time. I just captured the following text from your screen using OCR:

---
{screen_text[:1500]}
---

Please analyze this screen content and provide helpful insights about what's visible. Consider:
- What type of content or application is being displayed
- Key information or topics present
- Possible actions the user might want to take
- Any interesting patterns or insights

Provide a clear, helpful summary of what I can see on your screen."""
            
            self._run_task_in_background(
                self.orchestrator.process_direct_prompt,
                self._handle_single_capture_analysis_complete,
                analysis_prompt
            )
        else:
            self.overlay_window.add_response("👁 Screen Scanner", 
                                            "I'm looking at your screen but can't detect readable text. Try focusing on a window with text content.", 
                                            ["Try different area", "Check text visibility"])

    def _handle_single_capture_analysis_complete(self, response: Optional[str]):
        """Handle the result from the single screen capture analysis."""
        if response:
            self.overlay_window.add_response("👁 Screen Analysis", response, 
                                            ["Start monitoring", "Capture again", "Ask about screen"])
        else:
            # To get the word count, we need the original text. Since this is async,
            # we can't easily access it. We'll show a generic message.
            self.overlay_window.add_response("👁 Screen Captured", 
                                            "I read the screen, but analysis failed. You can ask me questions about what I saw.", 
                                            ["Ask about content", "Start monitoring"])
            
    def _handle_audio_toggle(self):
        """
        Handle audio toggle requests from the UI.
        Starts/stops audio listening.
        """
        try:
            self.audio_active = not self.audio_active
            self.logger.info(f"Audio toggle - Active: {self.audio_active}")
            
            if self.audio_active:
                # Start audio listening
                self.audio_listener.start_listening()
                self.orchestrator.start_analysis_loop()
                self.logger.info("Audio listening and analysis started")
            else:
                # Stop audio listening
                self.audio_listener.stop_listening()
                self.orchestrator.stop_analysis_loop()
                self.logger.info("Audio listening and analysis stopped")
                
        except Exception as e:
            error_msg = f"Error toggling audio: {e}"
            self.logger.error(error_msg)
            self.overlay_window.show_message("Audio Error", error_msg)
            
    def _handle_text_prompt(self, prompt: str):
        """
        Handle text prompts with proper direct prompt processing in a background thread.
        """
        self.logger.info(f"Processing text prompt: {prompt}")
        self.overlay_window.show_message("🤔 Processing...", "Sending to AI...")
        
        self._run_task_in_background(
            self.orchestrator.process_direct_prompt,
            self._handle_text_prompt_analysis_complete,
            prompt
        )

    def _handle_text_prompt_analysis_complete(self, response: Optional[str]):
        """Handle the result from the background text prompt analysis."""
        if response:
            self.overlay_window.add_response("🤖 Dia AI", response, ["Ask follow-up", "Use screen reader", "Listen to audio"])
            self.logger.info("Text prompt processed successfully")
        else:
            self.overlay_window.add_response("❌ AI Error", 
                                            "No response generated", 
                                            ["Check Ollama", "Try again"])
            self.logger.warning("No response generated for text prompt")
            
    def _handle_error(self, error_message: str):
        """
        Handle error messages from components.
        
        Args:
            error_message: The error message to handle
        """
        self.logger.error(f"Component error: {error_message}")
        if self.overlay_window:
            self.overlay_window.show_message("System Error", error_message)
            
    def _handle_window_closed(self):
        """Handle overlay window close event."""
        self.logger.info("Overlay window closed, shutting down application")
        self.shutdown()
        
    def start(self):
        """Start the Dia AI Assistant."""
        try:
            self.logger.info("Starting Dia AI Assistant...")
            
            # Initialize all components
            self.initialize_components()
            
            # Show the overlay window
            self.overlay_window.show()
            
            self.logger.info("Dia AI Assistant started successfully")
            self.logger.info("Use eye for screen analysis, mic for audio, or type prompts")
            
            # Start the Qt event loop
            sys.exit(self.app.exec())
            
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
            self.shutdown()
        except Exception as e:
            self.logger.error(f"Failed to start application: {e}")
            self.shutdown()
            raise
            
    def shutdown(self):
        """Shutdown the application gracefully."""
        try:
            self.logger.info("Shutting down Dia AI Assistant...")
            self._is_shutting_down = True
            
            # Stop orchestrator first to prevent new analysis tasks
            if self.orchestrator:
                self.orchestrator.stop_analysis_loop()
                
            # Stop audio listening
            if self.audio_listener:
                self.audio_listener.stop_listening()
                
            # Clean up all background threads
            self._cleanup_threads()
            
            # Disconnect all signal connections to prevent issues during shutdown
            if self.orchestrator:
                try:
                    self.orchestrator.analysis_updated.disconnect()
                    self.orchestrator.error_occurred.disconnect()
                except:
                    pass  # Ignore if already disconnected
                    
            if self.overlay_window:
                try:
                    self.overlay_window.ocr_requested.disconnect()
                    self.overlay_window.audio_toggle_requested.disconnect()
                    self.overlay_window.text_prompt_submitted.disconnect()
                    self.overlay_window.window_closed.disconnect()
                except:
                    pass  # Ignore if already disconnected
                    
            # Close overlay window
            if self.overlay_window:
                self.overlay_window.close()
                
            # Process any remaining events before quitting
            if self.app:
                self.app.processEvents()
                
            # Quit application
            if self.app:
                self.app.quit()
                
            self.logger.info("Dia AI Assistant shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")


def main():
    """Main entry point for the application."""
    try:
        # Create and start the Dia AI Assistant
        assistant = DiaAssistant()
        assistant.start()
        
    except Exception as e:
        print(f"Critical error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 