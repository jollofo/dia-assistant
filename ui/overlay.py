"""
UI Overlay Module
Minimalistic overlay window with essential AI assistant features.
"""

import sys
import logging
import time
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
            border: 1px solid rgba(70, 70, 70, 100);
            border-radius: 4px;
            padding: 4px;
            font-size: 10px;
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
        """Handle text submission with immediate feedback."""
        prompt = self.text_input.text().strip()
        if prompt:
            self.status_label.setText("🤔 Processing...")
            self.status_label.setStyleSheet("color: #42A5F5;")
            self.text_input.clear()
            QApplication.processEvents()  # Force immediate update
            self.text_prompt_submitted.emit(prompt)
            
    def add_response(self, title: str, summary: str, actions: List[str]):
        """Add AI response with persistent display (no auto-hide)."""
        # Update status
        self.status_label.setText("✅ Response received")
        self.status_label.setStyleSheet("color: #66BB6A;")
        
        # Show full output (no truncation since window is resizable)
        if summary:
            self.output_area.clear()
            self.output_area.append(f"<b>{title}</b>")
            self.output_area.append(summary)  # Show full text
            
            if actions:
                action_text = " • ".join(actions)  # Show all actions
                self.output_area.append(f"<i>{action_text}</i>")
                
            self.output_area.show()  # Show the output area
            
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
        """Show simple message."""
        self.status_label.setText(f"{title}: {message[:30]}...")
        self.status_label.setStyleSheet("color: #FFA726;")
        
        # Reset after 3 seconds
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