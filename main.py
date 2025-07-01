"""
Dia AI Assistant - Main Application
Entry point for the Dia AI Assistant application.
"""

import sys
import json
import logging
import os
from typing import Dict, Any
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, QObject, pyqtSignal

# Import core modules
from core.orchestrator import Orchestrator
from core.agent_manager import AgentManager

# Import feature modules
from modules.audio_listener import AudioListener
from modules.screen_scanner import ScreenScanner

# Import UI
from ui.overlay import OverlayWindow

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
                "timeout": 30
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
        
        Args:
            screen_content: The new screen content that was detected
        """
        try:
            self.logger.info("Screen content change detected - analyzing")
            
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
            
            # Process with AI
            response = self.orchestrator.process_direct_prompt(analysis_prompt)
            
            if response:
                self.overlay_window.add_response(
                    "🔄 Screen Change Detected", 
                    response,
                    ["Continue monitoring", "Stop monitoring", "Ask follow-up"]
                )
            else:
                word_count = len(screen_content.split())
                self.overlay_window.add_response(
                    "🔄 Screen Updated", 
                    f"I detected a screen change ({word_count} words now visible). Ask me what I can see.",
                    ["What's on screen?", "Continue monitoring", "Stop monitoring"]
                )
                
        except Exception as e:
            self.logger.error(f"Error handling screen change: {e}")
            self.overlay_window.add_response(
                "🔄 Screen Changed", 
                "I detected a screen change but couldn't analyze it. You can ask me what I see.",
                ["What do you see?", "Continue monitoring"]
            )
            
    def _perform_single_screen_capture(self):
        """Perform a single screen capture and analysis."""
        try:
            self.logger.info("Performing single screen capture")
            
            # Capture screen content
            screen_text = self.screen_scanner.capture_and_extract_text()
            
            # Quick error handling
            if not screen_text or screen_text.startswith("Tesseract OCR not installed"):
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
            
            if screen_text and len(screen_text.strip()) > 10:
                # Enhanced AI analysis with better context
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
                
                # Fast AI call with enhanced context
                try:
                    response = self.orchestrator.process_direct_prompt(analysis_prompt)
                    
                    if response:
                        # Show full response since window is resizable
                        self.overlay_window.add_response("👁 Screen Analysis", response, 
                                                        ["Start monitoring", "Capture again", "Ask about screen"])
                    else:
                        word_count = len(screen_text.split())
                        self.overlay_window.add_response("👁 Screen Captured", 
                                                        f"I can see your screen content ({word_count} words detected) but analysis failed. Try asking me specific questions about what's visible.", 
                                                        ["Try analysis again", "Ask specific question"])
                except Exception as e:
                    word_count = len(screen_text.split())
                    self.overlay_window.add_response("👁 Screen Captured", 
                                                    f"I successfully read {word_count} words from your screen. You can ask me questions about what I saw.", 
                                                    ["Ask about content", "Start monitoring"])
            else:
                self.overlay_window.add_response("👁 Screen Scanner", 
                                                "I'm looking at your screen but can't detect readable text. Try focusing on a window with text content.", 
                                                ["Try different area", "Check text visibility"])
                                                
        except Exception as e:
            self.logger.error(f"Single capture error: {e}")
            self.overlay_window.add_response("❌ Capture Error", 
                                            f"Screen capture failed: {str(e)}", 
                                            ["Try again", "Check system"])
            
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
        Handle text prompts with proper direct prompt processing.
        """
        try:
            self.logger.info(f"Processing text prompt: {prompt}")
            
            # Use the dedicated direct prompt method
            response = self.orchestrator.process_direct_prompt(prompt)
            
            if response:
                # Show full response since window is resizable
                self.overlay_window.add_response("🤖 Dia AI", response, ["Ask follow-up", "Use screen reader", "Listen to audio"])
                self.logger.info("Text prompt processed successfully")
            else:
                self.overlay_window.add_response("❌ AI Error", 
                                                "No response generated", 
                                                ["Check Ollama", "Try again"])
                self.logger.warning("No response generated for text prompt")
                
        except Exception as e:
            self.logger.error(f"Text prompt error: {e}")
            self.overlay_window.add_response("❌ Error", 
                                            f"Request failed: {str(e)}", 
                                            ["Check connection", "Try again"])
            
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
            
            # Stop orchestrator
            if self.orchestrator:
                self.orchestrator.stop_analysis_loop()
                
            # Stop audio listening
            if self.audio_listener:
                self.audio_listener.stop_listening()
                
            # Close overlay window
            if self.overlay_window:
                self.overlay_window.close()
                
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