"""
Live Captions Overlay - Real-time transcription display

A specialized overlay window for displaying live captions from audio transcription.
Features transparent background, customizable positioning, and smooth text updates.
"""
import time
from PyQt5.QtWidgets import (QMainWindow, QLabel, QVBoxLayout, QWidget, 
                            QPushButton, QHBoxLayout, QScrollArea, QTextEdit)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QColor, QPalette, QTextOption


class CaptionsOverlay(QMainWindow):
    """
    Live captions overlay window with Material Design styling.
    """
    
    # Signals for user interactions
    close_requested = pyqtSignal()
    save_transcript_requested = pyqtSignal()
    clear_transcript_requested = pyqtSignal()
    
    def __init__(self, config: dict):
        """
        Initialize the captions overlay.
        
        Args:
            config: Dictionary containing UI configuration settings
        """
        super().__init__()
        
        self.config = config.get('ui', {})
        self.captions_config = config.get('transcription', {}).get('ui', {})
        
        # UI settings
        self.opacity = self.captions_config.get('opacity', 0.9)
        self.position = self.captions_config.get('position', 'bottom-center')
        self.max_lines = self.captions_config.get('max_lines', 3)
        self.font_size = self.captions_config.get('font_size', 14)
        
        # Size preferences
        self.preferred_size = self.captions_config.get('size', {'width': 600, 'height': 150})
        self.min_size = {'width': 400, 'height': 100}
        self.max_size = {'width': 1200, 'height': 400}
        
        # Caption state
        self.current_text = ""
        self.is_final_text = False
        self.auto_hide_enabled = self.captions_config.get('auto_hide', True)
        self.hide_delay = self.captions_config.get('hide_delay', 5000)  # ms
        
        self._init_ui()
        self._position_window()
        
        # Auto-hide timer
        self.hide_timer = QTimer()
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self._auto_hide)
        
        print("Live captions overlay initialized")
    
    def _init_ui(self):
        """Initialize the captions overlay UI."""
        # Set window properties for overlay
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        
        # Set window properties for transparency
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(self.opacity)
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(8)
        main_widget.setLayout(main_layout)
        
        # Create captions display area
        self._create_captions_display(main_layout)
        
        # Create control buttons
        self._create_controls(main_layout)
        
        # Set dynamic sizing
        self.setMinimumSize(self.min_size['width'], self.min_size['height'])
        self.setMaximumSize(self.max_size['width'], self.max_size['height'])
        self.resize(self.preferred_size['width'], self.preferred_size['height'])
        
        # Setup animations
        self._setup_animations()
        
        # Initially hide the window
        self.hide()
    
    def _create_captions_display(self, parent_layout):
        """Create the main captions display area."""
        # Create scrollable text area for captions
        self.captions_area = QTextEdit()
        self.captions_area.setReadOnly(True)
        self.captions_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.captions_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.captions_area.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        
        # Style the captions area
        self._style_captions_area()
        
        parent_layout.addWidget(self.captions_area)
    
    def _style_captions_area(self):
        """Apply styling to the captions display area."""
        font = QFont("Segoe UI", self.font_size, QFont.Weight.Medium)
        self.captions_area.setFont(font)
        
        # Material Design styling for captions
        style = f"""
            QTextEdit {{
                background-color: rgba(33, 33, 33, 0.95);
                color: rgba(255, 255, 255, 0.95);
                border: none;
                border-radius: 12px;
                padding: 16px;
                line-height: 1.4;
            }}
            QScrollBar:vertical {{
                background-color: rgba(255, 255, 255, 0.1);
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background-color: rgba(255, 255, 255, 0.3);
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: rgba(255, 255, 255, 0.5);
            }}
        """
        self.captions_area.setStyleSheet(style)
    
    def _create_controls(self, parent_layout):
        """Create control buttons for the captions overlay."""
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 4, 0, 0)
        controls_layout.setSpacing(8)
        
        # Save transcript button
        self.save_button = QPushButton("💾 Save")
        self.save_button.setFixedSize(60, 24)
        self.save_button.clicked.connect(self.save_transcript_requested.emit)
        
        # Clear captions button
        self.clear_button = QPushButton("🗑 Clear")
        self.clear_button.setFixedSize(60, 24)
        self.clear_button.clicked.connect(self.clear_transcript_requested.emit)
        
        # Close button
        self.close_button = QPushButton("×")
        self.close_button.setFixedSize(24, 24)
        self.close_button.clicked.connect(self.close_requested.emit)
        
        # Button styling
        button_style = """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.15);
                border: none;
                border-radius: 6px;
                color: rgba(255, 255, 255, 0.9);
                font-size: 10px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.25);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.35);
            }
        """
        
        close_button_style = """
            QPushButton {
                background-color: rgba(244, 67, 54, 0.8);
                border: none;
                border-radius: 12px;
                color: rgba(255, 255, 255, 0.9);
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: rgba(244, 67, 54, 0.9);
            }
            QPushButton:pressed {
                background-color: rgba(244, 67, 54, 1.0);
            }
        """
        
        self.save_button.setStyleSheet(button_style)
        self.clear_button.setStyleSheet(button_style)
        self.close_button.setStyleSheet(close_button_style)
        
        controls_layout.addWidget(self.save_button)
        controls_layout.addWidget(self.clear_button)
        controls_layout.addStretch()
        controls_layout.addWidget(self.close_button)
        
        parent_layout.addLayout(controls_layout)
    
    def _setup_animations(self):
        """Setup animations for the captions overlay."""
        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_animation.setDuration(250)
        self.opacity_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    
    def _position_window(self):
        """Position the captions window according to configuration."""
        screen = self.screen()
        if screen:
            screen_geometry = screen.geometry()
            
            current_width = self.width() if self.width() > 0 else self.preferred_size['width']
            current_height = self.height() if self.height() > 0 else self.preferred_size['height']
            
            if self.position == 'bottom-center':
                x = (screen_geometry.width() - current_width) // 2
                y = screen_geometry.height() - current_height - 80
            elif self.position == 'bottom-left':
                x = 24
                y = screen_geometry.height() - current_height - 80
            elif self.position == 'bottom-right':
                x = screen_geometry.width() - current_width - 24
                y = screen_geometry.height() - current_height - 80
            elif self.position == 'top-center':
                x = (screen_geometry.width() - current_width) // 2
                y = 24
            elif self.position == 'center':
                x = (screen_geometry.width() - current_width) // 2
                y = (screen_geometry.height() - current_height) // 2
            else:
                # Default to bottom-center
                x = (screen_geometry.width() - current_width) // 2
                y = screen_geometry.height() - current_height - 80
            
            self.move(x, y)
    
    def update_captions(self, text: str, is_final: bool):
        """
        Update the captions display with new text.
        
        Args:
            text: The transcribed text to display
            is_final: Whether this is a final transcript or partial
        """
        if not text.strip():
            return
        
        self.current_text = text
        self.is_final_text = is_final
        
        # Format the text with styling
        if is_final:
            # Final text - add to permanent display
            timestamp = time.strftime("%H:%M:%S")
            formatted_text = f"<p style='margin: 4px 0; color: #ffffff;'><span style='color: #90a4ae; font-size: 11px;'>[{timestamp}]</span> {text}</p>"
            self.captions_area.append(formatted_text)
        else:
            # Partial text - show as temporary overlay
            self._show_partial_text(text)
        
        # Show the overlay if hidden
        self.show_overlay()
        
        # Reset auto-hide timer
        if self.auto_hide_enabled:
            self._start_auto_hide_timer()
        
        # Auto-scroll to bottom
        self.captions_area.verticalScrollBar().setValue(
            self.captions_area.verticalScrollBar().maximum()
        )
    
    def _show_partial_text(self, text: str):
        """Show partial text as an overlay."""
        # For now, we'll append partial text too but in a different color
        formatted_text = f"<p style='margin: 2px 0; color: #b0bec5; font-style: italic;'>{text}</p>"
        
        # Remove previous partial text if exists
        cursor = self.captions_area.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.captions_area.setTextCursor(cursor)
        self.captions_area.insertHtml(formatted_text)
    
    def show_overlay(self):
        """Show the captions overlay with animation."""
        if not self.isVisible():
            self.show()
            self.opacity_animation.setStartValue(0.0)
            self.opacity_animation.setEndValue(self.opacity)
            self.opacity_animation.start()
    
    def hide_overlay(self):
        """Hide the captions overlay with animation."""
        if self.isVisible():
            self.opacity_animation.setStartValue(self.opacity)
            self.opacity_animation.setEndValue(0.0)
            self.opacity_animation.finished.connect(self.hide)
            self.opacity_animation.start()
    
    def _start_auto_hide_timer(self):
        """Start the auto-hide timer."""
        if self.auto_hide_enabled:
            self.hide_timer.stop()
            self.hide_timer.start(self.hide_delay)
    
    def _auto_hide(self):
        """Auto-hide the overlay after inactivity."""
        # Only hide if we have final text (not actively transcribing)
        if self.is_final_text:
            self.hide_overlay()
    
    def clear_captions(self):
        """Clear all captions from the display."""
        self.captions_area.clear()
        print("Captions display cleared")
    
    def set_font_size(self, size: int):
        """Update the font size for captions."""
        self.font_size = size
        self._style_captions_area()
    
    def set_auto_hide(self, enabled: bool):
        """Enable or disable auto-hide functionality."""
        self.auto_hide_enabled = enabled
        if not enabled:
            self.hide_timer.stop()
    
    def mousePressEvent(self, event):
        """Handle mouse press for dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging."""
        if (event.buttons() == Qt.MouseButton.LeftButton and 
            hasattr(self, 'drag_start_position')):
            self.move(event.globalPosition().toPoint() - self.drag_start_position)
    
    def closeEvent(self, event):
        """Handle close event."""
        self.hide_overlay()
        event.ignore() 