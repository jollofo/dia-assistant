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
    QPushButton, QLineEdit, QTextEdit, QFrame
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
        
        # Minimalistic UI configuration
        self.width = 300  # Smaller width
        self.height = 200  # Smaller height
        self.transparency = 0.92
        
        # State tracking
        self.is_audio_active = False
        self.response_count = 0
        
        # UI components
        self.eye_button = None
        self.mic_button = None
        self.text_input = None
        self.close_button = None
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
        
        # Minimalistic window flags
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        
        self.setWindowOpacity(self.transparency)
        
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
        
        # Compact output area (only shows when needed)
        self.output_area = QTextEdit()
        self.output_area.setObjectName("output_area")
        self.output_area.setReadOnly(True)
        self.output_area.setMaximumHeight(80)
        self.output_area.hide()  # Hidden by default
        main_layout.addWidget(self.output_area)
        
        self.setLayout(main_layout)
        
    def _create_control_bar(self) -> QHBoxLayout:
        """Create minimalistic control bar."""
        control_layout = QHBoxLayout()
        control_layout.setSpacing(4)
        
        # Eye button
        self.eye_button = QPushButton("👁")
        self.eye_button.setObjectName("control_button")
        self.eye_button.setFixedSize(24, 24)
        self.eye_button.setToolTip("Screen")
        self.eye_button.clicked.connect(self._handle_ocr_request)
        
        # Mic button
        self.mic_button = QPushButton("🎤")
        self.mic_button.setObjectName("control_button")
        self.mic_button.setFixedSize(24, 24)
        self.mic_button.setToolTip("Audio")
        self.mic_button.clicked.connect(self._handle_audio_toggle)
        
        # Text input - more compact
        self.text_input = QLineEdit()
        self.text_input.setObjectName("text_input")
        self.text_input.setPlaceholderText("Ask AI...")
        self.text_input.returnPressed.connect(self._handle_text_submit)
        
        # Close button
        self.close_button = QPushButton("✕")
        self.close_button.setObjectName("close_button")
        self.close_button.setFixedSize(20, 20)
        self.close_button.clicked.connect(self.close)
        
        control_layout.addWidget(self.eye_button)
        control_layout.addWidget(self.mic_button)
        control_layout.addWidget(self.text_input)
        control_layout.addWidget(self.close_button)
        
        return control_layout
        
    def _apply_styling(self):
        """Apply clean, minimalistic styling."""
        style_sheet = """
        QWidget {
            background-color: rgba(25, 25, 25, 235);
            color: #E0E0E0;
            border-radius: 8px;
            font-family: 'Segoe UI', sans-serif;
            font-size: 11px;
        }
        
        QPushButton#control_button {
            background-color: rgba(60, 60, 60, 150);
            border: 1px solid rgba(100, 100, 100, 100);
            border-radius: 4px;
            font-size: 12px;
        }
        
        QPushButton#control_button:hover {
            background-color: rgba(80, 80, 80, 180);
            border: 1px solid rgba(120, 120, 120, 150);
        }
        
        QPushButton#close_button {
            background-color: rgba(220, 53, 69, 150);
            border: none;
            border-radius: 3px;
            color: white;
            font-size: 10px;
            font-weight: bold;
        }
        
        QPushButton#close_button:hover {
            background-color: rgba(220, 53, 69, 200);
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
        """
        
        # Apply audio active state styling
        if self.is_audio_active:
            style_sheet += """
            QPushButton#control_button:first-child + QPushButton {
                background-color: rgba(244, 67, 54, 180);
                border: 1px solid rgba(244, 67, 54, 200);
            }
            """
        
        self.setStyleSheet(style_sheet)
        
    def _handle_ocr_request(self):
        """Handle OCR button click with immediate feedback."""
        self.status_label.setText("📷 Capturing screen...")
        self.status_label.setStyleSheet("color: #FFA726;")
        QApplication.processEvents()  # Force immediate update
        self.ocr_requested.emit()
        
    def _handle_audio_toggle(self):
        """Handle audio toggle with immediate visual feedback."""
        self.is_audio_active = not self.is_audio_active
        
        if self.is_audio_active:
            self.status_label.setText("🎤 Listening...")
            self.status_label.setStyleSheet("color: #EF5350;")
            self.mic_button.setStyleSheet("""
                QPushButton#control_button {
                    background-color: rgba(244, 67, 54, 200);
                    border: 1px solid rgba(244, 67, 54, 255);
                }
            """)
        else:
            self.status_label.setText("Ready")
            self.status_label.setStyleSheet("color: #B0BEC5;")
            self.mic_button.setStyleSheet("")
            
        QApplication.processEvents()  # Force immediate update
        self.audio_toggle_requested.emit()
        
    def _handle_text_submit(self):
        """Handle text submission with immediate feedback."""
        prompt = self.text_input.text().strip()
        if prompt:
            self.status_label.setText("🤔 Thinking...")
            self.status_label.setStyleSheet("color: #42A5F5;")
            self.text_input.clear()
            QApplication.processEvents()  # Force immediate update
            self.text_prompt_submitted.emit(prompt)
            
    def add_response(self, title: str, summary: str, actions: List[str]):
        """Add AI response with minimalistic display."""
        self.response_count += 1
        
        # Update status
        self.status_label.setText(f"✅ Response {self.response_count}")
        self.status_label.setStyleSheet("color: #66BB6A;")
        
        # Show compact output
        if summary:
            # Truncate long responses
            display_text = summary
            if len(display_text) > 100:
                display_text = display_text[:100] + "..."
                
            self.output_area.clear()
            self.output_area.append(f"<b>{title}</b>")
            self.output_area.append(display_text)
            
            if actions:
                action_text = " • ".join(actions[:2])  # Only show first 2 actions
                if len(actions) > 2:
                    action_text += f" (+{len(actions)-2} more)"
                self.output_area.append(f"<i>{action_text}</i>")
                
            self.output_area.show()
            
            # Auto-hide after 5 seconds
            QTimer.singleShot(5000, self._hide_output)
            
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
        self.response_count = 0
        
    def closeEvent(self, event):
        """Handle window close event."""
        self.window_closed.emit()
        event.accept()
        
    def mousePressEvent(self, event):
        """Enable window dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            
    def mouseMoveEvent(self, event):
        """Handle window dragging."""
        if hasattr(self, 'drag_position') and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position) 