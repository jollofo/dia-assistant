#!/usr/bin/env python3
"""
Test script for the resizable text box overlay
"""
import sys
from PyQt5.QtWidgets import QApplication
from ui.overlay import OverlayWindow

def main():
    """Test the resizable text box overlay."""
    print("🎯 Testing Resizable Text Box Overlay")
    print("=" * 40)
    print("Features to test:")
    print("• Text box resizes with window")
    print("• Font size adapts to window width")
    print("• Text height adapts to window height")
    print("• Drag window edges/corners to resize")
    print("• Text box maintains usability at all sizes")
    print("\nInstructions:")
    print("1. Type some text in the text box")
    print("2. Drag the window edges to resize")
    print("3. Notice how the text box adapts")
    print("4. Try different window sizes")
    print("5. Type more text to see height adaptation")
    print("\nPress Ctrl+C or close button to exit")
    print("=" * 40)
    
    app = QApplication(sys.argv)
    
    # Create overlay window
    overlay = OverlayWindow()
    
    # Connect signals for testing
    def on_text_submitted(text):
        print(f"Text submitted: {text}")
        overlay.update_status(f"You typed: {text}")
    
    def on_close():
        print("Overlay close requested")
        app.quit()
    
    overlay.text_input_submitted.connect(on_text_submitted)
    overlay.close_requested.connect(on_close)
    
    # Show overlay
    overlay.show()
    overlay.update_status("Ready! Try typing and resizing the window.")
    
    # Run application
    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        print("\n👋 Test interrupted by user")
        sys.exit(0)

if __name__ == "__main__":
    main() 