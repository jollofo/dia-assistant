#!/usr/bin/env python3
"""
Demo script for the enhanced visual overlay system
This showcases the Cluely-inspired visual feedback and minimal dashboard
"""
import sys
import time
import json
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from ui.visual_overlay import VisualOverlay

class OverlayDemo:
    """Demo class to showcase the visual overlay features."""
    
    def __init__(self):
        """Initialize the demo."""
        self.app = QApplication(sys.argv)
        
        # Load demo configuration
        config = {
            "ui": {
                "overlay_position": "top-right",
                "overlay_opacity": 0.9,
                "status_timeout": 3000
            }
        }
        
        # Create visual overlay
        self.overlay = VisualOverlay(config)
        
        # Demo sequence
        self.demo_steps = [
            ("Starting Dia Assistant...", "idle", 2000),
            ("Listening for voice input...", "listening", 3000),
            ("Voice detected: 'Send email to john@example.com'", "listening", 2000),
            ("Processing speech with Ollama...", "processing", 3000),
            ("Intent recognized: SEND_EMAIL", "processing", 2000),
            ("Executing email action...", "processing", 3000),
            ("Email sent successfully!", "success", 2000),
            ("Ready for next command", "idle", 2000),
            ("Testing error scenario...", "processing", 2000),
            ("Connection failed!", "error", 2000),
            ("System ready", "idle", 1000),
        ]
        
        self.current_step = 0
        self.action_count = 0
        
        # Timer for demo sequence
        self.demo_timer = QTimer()
        self.demo_timer.timeout.connect(self._next_demo_step)
        
        print("Visual Overlay Demo initialized")
        print("This demo showcases the Cluely-inspired visual feedback system")
        print("Watch the overlay in the top-right corner of your screen")
    
    def start_demo(self):
        """Start the demo sequence."""
        print("\n🎬 Starting Visual Overlay Demo...")
        print("The overlay will cycle through different states to show all features")
        
        # Initialize overlay with model info
        self.overlay.update_model_info("llama3.2")
        self.overlay.update_confidence(0.0)
        
        # Start first step
        self._next_demo_step()
        self.demo_timer.start(2000)  # Start timer
        
        return self.app.exec()
    
    def _next_demo_step(self):
        """Execute the next demo step."""
        if self.current_step >= len(self.demo_steps):
            # Demo complete - exit instead of restarting
            print("\n✅ Demo completed! Press Ctrl+C to exit or close the window.")
            self.demo_timer.stop()
            return
        
        status, state, duration = self.demo_steps[self.current_step]
        
        print(f"Step {self.current_step + 1}: {status} [{state}]")
        
        # Update overlay
        self.overlay.update_status(status, state)
        
        # Update confidence based on state
        if state == "processing":
            confidence = 0.85 + (self.current_step * 0.02)  # Varying confidence
            self.overlay.update_confidence(min(confidence, 0.95))
        elif state == "success":
            self.overlay.update_confidence(0.92)
            self.overlay.increment_action_count()
            self.action_count += 1
        elif state == "error":
            self.overlay.update_confidence(0.0)
        
        # Special actions for certain steps
        if "email" in status.lower() and state == "success":
            # Simulate successful action
            self.overlay.increment_action_count()
        
        self.current_step += 1
        self.demo_timer.start(duration)
    
    def add_interactive_features(self):
        """Add interactive features to the demo."""
        # Connect overlay signals
        self.overlay.settings_clicked.connect(self._on_settings_clicked)
        
        print("\n🖱️  Interactive features:")
        print("- Click the ⚙️ button to test settings")
        print("- Click the − button to minimize/restore")
        print("- Drag the overlay to move it around")
    
    def _on_settings_clicked(self):
        """Handle settings button click."""
        print("⚙️ Settings clicked!")
        self.overlay.update_status("Settings opened", "idle")


def main():
    """Main demo function."""
    print("🎯 Dia AI Assistant - Visual Overlay Demo")
    print("=" * 50)
    print("This demo showcases the enhanced visual overlay system")
    print("inspired by Cluely's visual feedback approach.")
    print("\nFeatures demonstrated:")
    print("• Animated pulsing indicators")
    print("• Real-time status dashboard")
    print("• Progress animations")
    print("• State-based color coding")
    print("• Minimalist card-based UI")
    print("• Auto-hide functionality")
    print("• Interactive controls")
    print("\nPress Ctrl+C to exit the demo")
    print("=" * 50)
    
    try:
        demo = OverlayDemo()
        demo.add_interactive_features()
        exit_code = demo.start_demo()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 