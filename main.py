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
from PyQt6.QtCore import QTimer

# Import core modules
from core.orchestrator import Orchestrator
from core.agent_manager import AgentManager

# Import feature modules
from modules.audio_listener import AudioListener
from modules.screen_scanner import ScreenScanner

# Import UI
from ui.overlay import OverlayWindow

class DiaAssistant:
    """
    Main application class that coordinates all components of the Dia AI Assistant.
    """
    
    def __init__(self):
        """Initialize the Dia AI Assistant."""
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
        
        self.logger.info("Signal connections established")
        
    def _handle_ocr_request(self):
        """
        Handle OCR requests from the UI with improved speed and error handling.
        """
        try:
            self.logger.info("OCR request received - capturing screen")
            
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
                # Quick AI analysis with shorter prompt
                analysis_prompt = f"Analyze this screen content briefly: {screen_text[:800]}"
                
                # Fast AI call
                try:
                    analysis = self.orchestrator._get_analysis_from_llm(analysis_prompt)
                    
                    if analysis and analysis.get('insights'):
                        insights = analysis.get('insights', [])
                        actions = analysis.get('actions', [])
                        
                        summary = insights[0] if insights else "Screen analyzed"
                        if len(summary) > 80:
                            summary = summary[:80] + "..."
                            
                        self.overlay_window.add_response("👁 Screen", summary, actions[:3])
                    else:
                        word_count = len(screen_text.split())
                        self.overlay_window.add_response("👁 Screen", 
                                                        f"Captured {word_count} words from screen", 
                                                        ["Content captured"])
                except Exception as e:
                    self.overlay_window.add_response("👁 Screen", 
                                                    "Captured but AI analysis failed", 
                                                    ["Try again"])
            else:
                self.overlay_window.add_response("👁 Screen", 
                                                "No readable text found on screen", 
                                                ["Try different content"])
                
        except Exception as e:
            self.logger.error(f"OCR error: {e}")
            self.overlay_window.add_response("❌ Error", f"OCR failed: {str(e)[:30]}...", 
                                            ["Check system"])
            
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
        Handle text prompts with faster processing.
        """
        try:
            self.logger.info(f"Processing text prompt: {prompt[:50]}...")
            
            # Quick AI analysis
            try:
                analysis = self.orchestrator._get_analysis_from_llm(prompt)
                
                if analysis:
                    insights = analysis.get('insights', [])
                    actions = analysis.get('actions', [])
                    
                    # Use first insight as response
                    response = insights[0] if insights else "Request processed"
                    if len(response) > 100:
                        response = response[:100] + "..."
                        
                    self.overlay_window.add_response("🤖 AI", response, actions[:3])
                else:
                    self.overlay_window.add_response("🤖 AI", 
                                                    "Response generated but not parsed correctly", 
                                                    ["Try rephrasing"])
                    
            except Exception as e:
                self.logger.error(f"AI processing error: {e}")
                self.overlay_window.add_response("❌ AI Error", 
                                                "Failed to process request", 
                                                ["Check Ollama", "Try again"])
                
        except Exception as e:
            self.logger.error(f"Text prompt error: {e}")
            self.overlay_window.add_response("❌ Error", "Request failed", ["Try again"])
            
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