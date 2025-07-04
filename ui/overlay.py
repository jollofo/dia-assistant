"""
UI Overlay Module
Minimalistic overlay window with essential AI assistant features.
"""

import sys
import logging
import time
from datetime import datetime
from typing import Dict, Any, List
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QTextEdit, QFrame, QSizeGrip
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QTextCursor

class OverlayWindow(QWidget):
    """
    Minimalistic overlay window for AI assistant.
    """
    
    # Signals for interaction with other components
    ocr_requested = pyqtSignal()
    audio_toggle_requested = pyqtSignal()
    text_prompt_submitted = pyqtSignal(str)
    window_closed = pyqtSignal()
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Resizable UI configuration
        self.width = 320  # Slightly wider for better resizable experience
        self.height = 240  # Taller to accommodate resize functionality
        self.transparency = 0.92
        
        # Toggle state tracking
        self.is_audio_active = False
        self.is_eye_active = False
        
        # Streaming control attributes
        self.streaming_chunk_queue = []
        self.streaming_timer = QTimer()
        self.streaming_timer.timeout.connect(self._process_next_chunk)
        self.is_streaming = False
        
        # Get streaming configuration
        ui_config = config.get('ui', {}).get('overlay', {})
        self.streaming_delay = ui_config.get('streaming_delay_ms', 80)  # Default 80ms between chunks
        self.streaming_mode = ui_config.get('streaming_mode', 'smooth')  # smooth, fast, typing
        
        # UI components
        self.eye_button = None
        self.mic_button = None
        self.text_input = None
        self.output_area = None
        self.status_label = None
        
        # Setup the window
        self._setup_window()
        self._setup_layout()
        self._apply_styling()
        
        self.logger.info("Minimalistic OverlayWindow initialized")
        
    def _setup_window(self):
        """Configure the main window properties."""
        ui_config = self.config.get('ui', {})
        self.setWindowTitle("Dia AI")
        self.setGeometry(
            ui_config.get('position', {}).get('x', 50),
            ui_config.get('position', {}).get('y', 50),
            self.width,
            self.height
        )
        
        # Resizable window flags - removed FramelessWindowHint to allow resizing
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        
        self.setWindowOpacity(self.transparency)
        
        # Set minimum size for usability
        self.setMinimumSize(250, 150)
        
        # Add resize grip for better UX
        self.size_grip = QSizeGrip(self)
        self.size_grip.setFixedSize(16, 16)
        
    def _setup_layout(self):
        """Create minimalistic layout."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)
        
        # Control bar
        control_bar = self._create_control_bar()
        main_layout.addLayout(control_bar)
        
        # Status label (replaces large output area)
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("status_label")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        main_layout.addWidget(self.status_label)
        
        # Output area (only shows when needed)
        self.output_area = QTextEdit()
        self.output_area.setObjectName("output_area")
        self.output_area.setReadOnly(True)
        self.output_area.setMinimumHeight(60)
        self.output_area.hide()  # Hidden by default
        main_layout.addWidget(self.output_area)
        
        # Add resize grip in bottom-right corner
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.size_grip)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addLayout(bottom_layout)
        
        self.setLayout(main_layout)
        
    def _create_control_bar(self) -> QHBoxLayout:
        """Create minimalistic control bar."""
        control_layout = QHBoxLayout()
        control_layout.setSpacing(4)
        
        # Eye button
        self.eye_button = QPushButton("👁")
        self.eye_button.setObjectName("eye_button")
        self.eye_button.setFixedSize(24, 24)
        self.eye_button.setToolTip("Screen Scanner")
        self.eye_button.clicked.connect(self._handle_eye_toggle)
        
        # Mic button
        self.mic_button = QPushButton("🎤")
        self.mic_button.setObjectName("mic_button")
        self.mic_button.setFixedSize(24, 24)
        self.mic_button.setToolTip("Audio Listener")
        self.mic_button.clicked.connect(self._handle_audio_toggle)
        
        # Text input - more compact
        self.text_input = QLineEdit()
        self.text_input.setObjectName("text_input")
        self.text_input.setPlaceholderText("Ask AI...")
        self.text_input.returnPressed.connect(self._handle_text_submit)
        
        control_layout.addWidget(self.eye_button)
        control_layout.addWidget(self.mic_button)
        control_layout.addWidget(self.text_input)
        
        return control_layout
        
    def _apply_styling(self):
        """Apply clean, minimalistic styling with toggle states."""
        style_sheet = """
        QWidget {
            background-color: rgba(25, 25, 25, 235);
            color: #E0E0E0;
            border-radius: 8px;
            font-family: 'Segoe UI', sans-serif;
            font-size: 11px;
        }
        
        QPushButton#eye_button, QPushButton#mic_button {
            background-color: rgba(60, 60, 60, 150);
            border: 1px solid rgba(100, 100, 100, 100);
            border-radius: 4px;
            font-size: 12px;
        }
        
        QPushButton#eye_button:hover, QPushButton#mic_button:hover {
            background-color: rgba(80, 80, 80, 180);
            border: 1px solid rgba(120, 120, 120, 150);
        }
        
        QLineEdit#text_input {
            background-color: rgba(40, 40, 40, 200);
            border: 1px solid rgba(80, 80, 80, 150);
            border-radius: 4px;
            padding: 4px 6px;
            color: white;
        }
        
        QLineEdit#text_input:focus {
            border: 1px solid rgba(33, 150, 243, 200);
        }
        
        QLabel#status_label {
            color: #B0BEC5;
            font-size: 10px;
            padding: 4px;
        }
        
        QTextEdit#output_area {
            background-color: rgba(35, 35, 35, 200);
            border: 1px solid rgba(80, 80, 80, 150);
            border-radius: 4px;
            padding: 6px;
            color: white;
            font-size: 10px;
            line-height: 1.4;
        }
        
        QTextEdit#output_area:focus {
            border: 1px solid rgba(33, 150, 243, 100);
        }
        
        /* Simple, minimal scroll bar styling */
        QScrollBar:vertical {
            background: rgba(60, 60, 60, 100);
            width: 8px;
            border-radius: 4px;
            margin: 0px;
        }
        
        QScrollBar::handle:vertical {
            background: rgba(120, 120, 120, 150);
            border-radius: 4px;
            min-height: 20px;
        }
        
        QScrollBar::handle:vertical:hover {
            background: rgba(140, 140, 140, 180);
        }
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: none;
                }
        """
        
        self.setStyleSheet(style_sheet)
        self._update_button_states()
        
    def _update_button_states(self):
        """Update visual state of toggle buttons."""
        # Update eye button state
        if self.is_eye_active:
            self.eye_button.setStyleSheet("""
                QPushButton#eye_button {
                    background-color: rgba(76, 175, 80, 200);
                    border: 1px solid rgba(76, 175, 80, 255);
                    color: white;
                }
            """)
        else:
            self.eye_button.setStyleSheet("")
            
        # Update mic button state
        if self.is_audio_active:
            self.mic_button.setStyleSheet("""
                QPushButton#mic_button {
                    background-color: rgba(244, 67, 54, 200);
                    border: 1px solid rgba(244, 67, 54, 255);
                    color: white;
                }
            """)
        else:
            self.mic_button.setStyleSheet("")
    
    def _handle_eye_toggle(self):
        """Handle eye button toggle with visual feedback for monitoring states."""
        # Don't auto-toggle state here - let main.py handle it based on monitoring
        self.status_label.setText("👁 Processing...")
        self.status_label.setStyleSheet("color: #42A5F5;")
        
        self._update_button_states()
        QApplication.processEvents()  # Force immediate update
        
        # Emit signal to main.py to handle monitoring logic
        self.ocr_requested.emit()
        
        # Reset status will be handled by main.py responses
        
    def _handle_audio_toggle(self):
        """Handle audio toggle with visual feedback."""
        self.is_audio_active = not self.is_audio_active
        
        if self.is_audio_active:
            self.status_label.setText("🎤 Audio listener active")
            self.status_label.setStyleSheet("color: #EF5350;")
        else:
            self.status_label.setText("🎤 Audio listener inactive")
            self.status_label.setStyleSheet("color: #B0BEC5;")
            
        self._update_button_states()
        QApplication.processEvents()  # Force immediate update
        self.audio_toggle_requested.emit()
        
        # Reset status after 2 seconds
        QTimer.singleShot(2000, lambda: (
            self.status_label.setText("Ready"),
            self.status_label.setStyleSheet("color: #B0BEC5;")
        ))
        
    def _handle_text_submit(self):
        """Handle text input submission with special commands."""
        text = self.text_input.text().strip()
        if text:
            # Check for special commands
            if text.lower() in ['/clear', '/c']:
                self.clear_chat_history()
                self.text_input.clear()
                return
            elif text.lower() in ['/help', '/h']:
                self._show_help_message()
                self.text_input.clear()
                return
            elif text.lower() in ['/screen', '/s']:
                self._show_last_screen_analysis()
                self.text_input.clear()
                return
            
            # Normal text prompt
            self.text_prompt_submitted.emit(text)
            self.text_input.clear()
            
    def _show_last_screen_analysis(self):
        """Show the last screen analysis that was processed silently."""
        # This will be handled by the main application
        self.text_prompt_submitted.emit("__SHOW_LAST_SCREEN_ANALYSIS__")
            
    def _show_help_message(self):
        """Show help message with available commands."""
        current_time = datetime.now().strftime("%H:%M:%S")
        
        # Add separator if there's existing content
        if self.output_area.toPlainText().strip():
            self.output_area.append("")
            self.output_area.append("─" * 40)
            self.output_area.append("")
        
        help_text = """Available commands:
• /clear or /c - Clear chat history
• /screen or /s - Show last screen analysis
• /help or /h - Show this help
• Ctrl+L - Clear chat history (keyboard shortcut)

You can also:
• 👁 Click eye button to scan screen
• 🎤 Click mic button to toggle audio
• Ask any question directly"""
        
        self.output_area.append(f"<b>📚 Help</b> <span style='color: #888; font-size: 9px;'>[{current_time}]</span>")
        self.output_area.append(help_text)
        self.output_area.show()
        
        # Scroll to bottom
        scrollbar = self.output_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def add_response(self, title: str, summary: str, actions: List[str]):
        """Add a non-streaming response with timestamp in chat-like format."""
        self.status_label.setText("✅ Analysis complete")
        self.status_label.setStyleSheet("color: #66BB6A;")
        
        # Show output area
        self.output_area.show()
        
        # Add timestamp and separator if this isn't the first message
        current_time = datetime.now().strftime("%H:%M:%S")
        
        # If there's existing content, add a separator
        if self.output_area.toPlainText().strip():
            self.output_area.append("")  # Empty line for spacing
            self.output_area.append("─" * 40)  # Visual separator
            self.output_area.append("")  # Another empty line
        
        # Add timestamped response
        self.output_area.append(f"<b>{title}</b> <span style='color: #888; font-size: 9px;'>[{current_time}]</span>")
        self.output_area.append(summary)  # Show full text
        
        if actions:
            action_text = " • ".join(actions)  # Show all actions
            self.output_area.append(f"<i>{action_text}</i>")
            
        # Scroll to bottom to show the latest content
        scrollbar = self.output_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
            
        # Reset status after 3 seconds but keep output visible
        QTimer.singleShot(3000, lambda: (
            self.status_label.setText("Ready"),
            self.status_label.setStyleSheet("color: #B0BEC5;")
        ))
        
    def _hide_output(self):
        """Hide the output area and reset status."""
        self.output_area.hide()
        self.status_label.setText("Ready")
        self.status_label.setStyleSheet("color: #B0BEC5;")
        
    def show_message(self, title: str, message: str):
        """Show message in chat-like format with timestamp."""
        current_time = datetime.now().strftime("%H:%M:%S")
        
        # Show output area
        self.output_area.show()
        
        # Add separator if there's existing content
        if self.output_area.toPlainText().strip():
            self.output_area.append("")
            self.output_area.append("─" * 40)
            self.output_area.append("")
        
        # Add timestamped message
        self.output_area.append(f"<b>{title}</b> <span style='color: #888; font-size: 9px;'>[{current_time}]</span>")
        self.output_area.append(message)
        
        # Update status briefly
        self.status_label.setText(f"{title}: {message[:30]}...")
        self.status_label.setStyleSheet("color: #FFA726;")
        
        # Scroll to bottom
        scrollbar = self.output_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
        # Reset status after 3 seconds but keep message in chat
        QTimer.singleShot(3000, lambda: (
            self.status_label.setText("Ready"),
            self.status_label.setStyleSheet("color: #B0BEC5;")
        ))
        
    def start_streaming_response(self, title: str):
        """Initialize UI for streaming response with chat-like append behavior."""
        self.status_label.setText("🌊 Streaming...")
        self.status_label.setStyleSheet("color: #42A5F5;")
        
        # Show output area if hidden
        self.output_area.show()
        
        # Add timestamp and separator if this isn't the first message
        current_time = datetime.now().strftime("%H:%M:%S")
        
        # If there's existing content, add a separator
        if self.output_area.toPlainText().strip():
            self.output_area.append("")  # Empty line for spacing
            self.output_area.append("─" * 40)  # Visual separator
            self.output_area.append("")  # Another empty line
        
        # Add timestamped header for the new message
        self.output_area.append(f"<b>{title}</b> <span style='color: #888; font-size: 9px;'>[{current_time}]</span>")
        self.output_area.append("")  # Empty line for content
        
        # Initialize streaming state
        self.streaming_chunk_queue.clear()
        self.is_streaming = True
        
        # Move cursor to the end for appending
        cursor = self.output_area.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.output_area.setTextCursor(cursor)
        
        # Scroll to bottom to show the latest message
        scrollbar = self.output_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def append_streaming_chunk(self, chunk: str):
        """Queue a chunk of streamed content for controlled display."""
        if chunk:
            if self.streaming_mode == 'instant':
                # Immediate display like before
                self._append_chunk_immediately(chunk)
            else:
                # Add to queue for controlled display
                self.streaming_chunk_queue.append(chunk)
                
                # Start processing if not already running
                if not self.streaming_timer.isActive():
                    self._process_next_chunk()  # Process first chunk immediately
                    self.streaming_timer.start(self.streaming_delay)
                    
    def _append_chunk_immediately(self, chunk: str):
        """Append chunk immediately without delay (original behavior)."""
        cursor = self.output_area.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(chunk)
        
        # Scroll to bottom
        scrollbar = self.output_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        QApplication.processEvents()
        
    def _process_next_chunk(self):
        """Process the next chunk from the queue with controlled timing."""
        if self.streaming_chunk_queue:
            chunk = self.streaming_chunk_queue.pop(0)
            
            if self.streaming_mode == 'typing':
                # Typing effect - add character by character
                self._add_typing_effect(chunk)
            else:
                # Smooth mode - add chunk by chunk
                self._append_chunk_immediately(chunk)
                
        else:
            # Queue is empty, stop timer
            self.streaming_timer.stop()
            
    def _add_typing_effect(self, chunk: str):
        """Add chunk with typing effect (character by character)."""
        cursor = self.output_area.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        # For typing effect, we'll add the whole chunk but it feels like typing
        # due to the controlled timing between chunks
        cursor.insertText(chunk)
        
        # Scroll to bottom
        scrollbar = self.output_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        QApplication.processEvents()
        
    def complete_streaming_response(self, complete_response: str, actions: List[str] = None):
        """Complete the streaming response and add actions if provided."""
        # Process any remaining chunks in queue
        while self.streaming_chunk_queue:
            chunk = self.streaming_chunk_queue.pop(0)
            self._append_chunk_immediately(chunk)
            
        # Stop streaming timer and reset state
        self.streaming_timer.stop()
        self.is_streaming = False
        
        self.status_label.setText("✅ Stream complete")
        self.status_label.setStyleSheet("color: #66BB6A;")
        
        # Add actions if provided
        if actions:
            self.output_area.append("")  # Empty line
            action_text = " • ".join(actions[:3])  # Limit to 3 actions
            self.output_area.append(f"<i>{action_text}</i>")
            
        # Scroll to bottom to show the latest content
        scrollbar = self.output_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
        # Reset status after 3 seconds but keep output visible
        QTimer.singleShot(3000, lambda: (
            self.status_label.setText("Ready"),
            self.status_label.setStyleSheet("color: #B0BEC5;")
        ))
        
    def handle_streaming_error(self, error_message: str):
        """Handle streaming errors."""
        # Clean up streaming state
        self.streaming_chunk_queue.clear()
        self.streaming_timer.stop()
        self.is_streaming = False
        
        self.status_label.setText("❌ Stream error")
        self.status_label.setStyleSheet("color: #EF5350;")
        
        # Show error in output if visible
        if self.output_area.isVisible():
            self.output_area.append(f"\n<i>Error: {error_message}</i>")
        
        # Reset status after 3 seconds
        QTimer.singleShot(3000, lambda: (
            self.status_label.setText("Ready"),
            self.status_label.setStyleSheet("color: #B0BEC5;")
        ))
        
    def update_display(self, analysis_data: Dict[str, Any]):
        """Update with analysis data."""
        insights = analysis_data.get('insights', [])
        actions = analysis_data.get('actions', [])
        
        if insights:
            summary = insights[0] if insights else "Analysis complete"
            self.add_response("🧠 Analysis", summary, actions)
            
    def clear_display(self):
        """Clear all content."""
        self.output_area.hide()
        self.status_label.setText("Ready")
        self.status_label.setStyleSheet("color: #B0BEC5;")
        
    def clear_chat_history(self):
        """Clear the chat history and show confirmation."""
        self.output_area.clear()
        current_time = datetime.now().strftime("%H:%M:%S")
        self.output_area.append(f"<i style='color: #888;'>Chat history cleared [{current_time}]</i>")
        self.output_area.append("")
        self.output_area.show()
        
        # Brief status update
        self.status_label.setText("🗑 Chat cleared")
        self.status_label.setStyleSheet("color: #FFA726;")
        
        # Reset status after 2 seconds
        QTimer.singleShot(2000, lambda: (
            self.status_label.setText("Ready"),
            self.status_label.setStyleSheet("color: #B0BEC5;")
        ))
        
    def set_monitoring_active(self, active: bool):
        """Update UI to reflect continuous monitoring state."""
        self.is_eye_active = active
        self._update_button_states()
        
        if active:
            # Keep status updated to show monitoring is active
            self.status_label.setText("👁 Monitoring screen...")
            self.status_label.setStyleSheet("color: #4CAF50;")
        else:
            self.status_label.setText("👁 Monitoring stopped")
            self.status_label.setStyleSheet("color: #B0BEC5;")
            
        QApplication.processEvents()
        
        # Reset status after brief display if not monitoring  
        if not active:
            QTimer.singleShot(2000, lambda: (
                self.status_label.setText("Ready"),
                self.status_label.setStyleSheet("color: #B0BEC5;")
            ))
        
    def closeEvent(self, event):
        """Handle window close event."""
        self.window_closed.emit()
        event.accept()
        
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts."""
        # Ctrl+L to clear chat history
        if event.key() == Qt.Key.Key_L and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.clear_chat_history()
            event.accept()
            return
        
        # Pass other events to parent
        super().keyPressEvent(event) 