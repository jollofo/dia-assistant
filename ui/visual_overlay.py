"""
Enhanced Visual Overlay Module - Clean Material Design-inspired visual feedback system
"""
import sys
from PyQt5.QtWidgets import (QMainWindow, QLabel, QVBoxLayout, QHBoxLayout, 
                            QWidget, QProgressBar, QPushButton, QFrame, QGraphicsOpacityEffect)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal, QRect
from PyQt5.QtGui import (QFont, QPalette, QColor, QPainter, QPen, QBrush, 
                        QLinearGradient, QPixmap, QIcon)
import math
import time
import json
import os


class PulsingIndicator(QWidget):
    """Clean animated pulsing indicator with Material Design colors."""
    
    def __init__(self, color=None, size=16):
        super().__init__()
        # Updated with cleaner Material Design colors
        self.color = color or QColor(25, 118, 210)  # Material Blue 600
        self.size = size
        self._pulse_value = 0.0
        self.setFixedSize(size + 8, size + 8)
        
        # Smoother animation with better easing
        self.animation = QPropertyAnimation(self, b"pulse_value")
        self.animation.setDuration(2000)  # Slower, more elegant
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setLoopCount(-1)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.animation.valueChanged.connect(self.update)
    
    def start_animation(self):
        """Start the pulsing animation."""
        self.animation.start()
    
    def stop_animation(self):
        """Stop the pulsing animation."""
        self.animation.stop()
        self._pulse_value = 0.0
        self.update()
    
    def set_color(self, color):
        """Change the indicator color."""
        self.color = color
        self.update()
    
    @property
    def pulse_value(self):
        return self._pulse_value
    
    @pulse_value.setter
    def pulse_value(self, value):
        self._pulse_value = value
        self.update()
    
    def paintEvent(self, event):
        """Custom paint event with cleaner Material Design styling."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Cleaner pulsing calculation
        pulse_factor = 0.5 + 0.4 * math.sin(self._pulse_value * 2 * math.pi)
        alpha = int(80 + 120 * pulse_factor)
        radius = self.size // 2
        
        # Material Design elevation shadow
        shadow_color = QColor(0, 0, 0, 20)
        painter.setBrush(QBrush(shadow_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(self.rect().center().x() - radius - 1, 
                          self.rect().center().y() - radius + 1,
                          (radius + 1) * 2, (radius + 1) * 2)
        
        # Main indicator circle
        color = QColor(self.color)
        color.setAlpha(alpha)
        painter.setBrush(QBrush(color))
        painter.drawEllipse(self.rect().center().x() - radius, 
                          self.rect().center().y() - radius,
                          radius * 2, radius * 2)


class StatusCard(QFrame):
    """Clean Material Design status card widget."""
    
    def __init__(self, title, value="", color=None):
        super().__init__()
        self.color = color or QColor(25, 118, 210)  # Material Blue 600
        self.setup_ui(title, value)
    
    def setup_ui(self, title, value):
        """Setup the clean status card UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 12, 16, 12)  # Material spacing
        layout.setSpacing(4)
        
        # Title label with Material typography
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("Segoe UI", 8, QFont.Weight.Medium))
        self.title_label.setStyleSheet("color: rgba(0, 0, 0, 0.6); margin: 0;")
        
        # Value label with better typography
        self.value_label = QLabel(value)
        self.value_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Normal))
        self.value_label.setStyleSheet("color: rgba(0, 0, 0, 0.87); margin: 0;")
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        self.setLayout(layout)
        
        # Clean Material Design card styling
        self.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(255, 255, 255, 0.95);
                border: none;
                border-radius: 8px;
                margin: 1px;
            }}
            QFrame:hover {{
                background-color: rgba(255, 255, 255, 1.0);
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            }}
        """)
    
    def update_value(self, value):
        """Update the status card value."""
        self.value_label.setText(str(value))


class VisualOverlay(QMainWindow):
    """Clean Material Design visual overlay with minimal dashboard."""
    
    # Signals for user interactions
    dashboard_clicked = pyqtSignal()
    settings_clicked = pyqtSignal()
    close_requested = pyqtSignal()  # Add signal for close button
    
    # Material Design color palette
    COLORS = {
        'idle': QColor(158, 158, 158),      # Material Grey 500
        'listening': QColor(25, 118, 210),  # Material Blue 600
        'processing': QColor(255, 152, 0),  # Material Orange 500
        'success': QColor(76, 175, 80),     # Material Green 500
        'error': QColor(244, 67, 54),       # Material Red 500
    }
    
    def __init__(self, config: dict):
        """Initialize the clean visual overlay."""
        super().__init__()
        
        self.config = config.get('ui', {})
        self.opacity = self.config.get('overlay_opacity', 0.95)
        self.position = self.config.get('overlay_position', 'top-right')
        
        # State tracking
        self.current_state = "idle"
        self.is_dashboard_visible = True
        self.activity_log = []
        self.is_minimized = False
        
        # Size preferences (can be saved/loaded from config)
        self.preferred_size = self.config.get('overlay_size', {'width': 300, 'height': 260})
        self.min_size = {'width': 200, 'height': 120}
        self.max_size = {'width': 600, 'height': 500}
        
        # UI Components
        self.status_indicator = None
        self.status_cards = {}
        self.progress_bar = None
        
        self._init_ui()
        self._position_window()
        self._setup_animations()
        
        # Auto-hide timer
        self.hide_timer = QTimer()
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self._auto_hide)
        
        print("Clean visual overlay initialized with dynamic sizing")
    
    def _init_ui(self):
        """Initialize the clean Material Design user interface."""
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
        main_layout.setContentsMargins(12, 12, 12, 12)  # Consistent Material spacing
        main_layout.setSpacing(8)
        main_widget.setLayout(main_layout)
        
        # Create clean header with status indicator
        self._create_header(main_layout)
        
        # Create dashboard section
        self._create_dashboard(main_layout)
        
        # Create progress section
        self._create_progress_section(main_layout)
        
        # Create control buttons
        self._create_controls(main_layout)
        
        # Set dynamic sizing constraints instead of fixed size
        self.setMinimumSize(self.min_size['width'], self.min_size['height'])
        self.setMaximumSize(self.max_size['width'], self.max_size['height'])
        self.resize(self.preferred_size['width'], self.preferred_size['height'])
        
        # Enable custom resize handling
        self._setup_resize_behavior()
        
        # Initially hide the window
        self.hide()
    
    def _create_header(self, parent_layout):
        """Create clean header with Material Design principles."""
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(4, 4, 4, 4)
        header_layout.setSpacing(12)
        
        # Status indicator
        self.status_indicator = PulsingIndicator(self.COLORS['idle'], 14)
        
        # Status text with clean typography
        self.status_text = QLabel("Ready")
        self.status_text.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        self.status_text.setStyleSheet("color: rgba(0, 0, 0, 0.87); background: transparent;")
        
        header_layout.addWidget(self.status_indicator)
        header_layout.addWidget(self.status_text)
        header_layout.addStretch()
        
        parent_layout.addLayout(header_layout)
    
    def _create_dashboard(self, parent_layout):
        """Create clean minimal dashboard with Material cards."""
        self.dashboard_widget = QWidget()
        dashboard_layout = QVBoxLayout()
        dashboard_layout.setContentsMargins(0, 4, 0, 4)
        dashboard_layout.setSpacing(6)
        
        # Create cards grid with cleaner layout
        cards_layout = QVBoxLayout()
        cards_layout.setSpacing(4)
        
        # Row 1: Status and Model
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(6)
        
        self.status_cards['status'] = StatusCard("STATUS", "Idle")
        self.status_cards['model'] = StatusCard("MODEL", "...")
        
        row1_layout.addWidget(self.status_cards['status'])
        row1_layout.addWidget(self.status_cards['model'])
        
        # Row 2: Actions and Confidence
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(6)
        
        self.status_cards['actions'] = StatusCard("ACTIONS", "0")
        self.status_cards['confidence'] = StatusCard("CONFIDENCE", "0%")
        
        row2_layout.addWidget(self.status_cards['actions'])
        row2_layout.addWidget(self.status_cards['confidence'])
        
        cards_layout.addLayout(row1_layout)
        cards_layout.addLayout(row2_layout)
        
        dashboard_layout.addLayout(cards_layout)
        self.dashboard_widget.setLayout(dashboard_layout)
        parent_layout.addWidget(self.dashboard_widget)
    
    def _create_progress_section(self, parent_layout):
        """Create clean progress section with Material styling."""
        self.progress_widget = QWidget()
        progress_layout = QVBoxLayout()
        progress_layout.setContentsMargins(0, 4, 0, 0)
        progress_layout.setSpacing(6)
        
        # Progress bar with Material Design styling
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(4)  # Thin Material progress bar
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 2px;
                background-color: rgba(0, 0, 0, 0.1);
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(25, 118, 210, 0.8),
                    stop:1 rgba(25, 118, 210, 1.0));
                border-radius: 2px;
            }
        """)
        
        progress_layout.addWidget(self.progress_bar)
        self.progress_widget.setLayout(progress_layout)
        parent_layout.addWidget(self.progress_widget)
    
    def _create_controls(self, parent_layout):
        """Create clean control buttons with Material Design."""
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 4, 0, 0)
        controls_layout.setSpacing(8)
        
        # Minimize button
        self.minimize_button = QPushButton("−")
        self.minimize_button.setFixedSize(24, 24)
        self.minimize_button.clicked.connect(self.toggle_minimize)
        
        # Close button
        self.close_button = QPushButton("×")
        self.close_button.setFixedSize(24, 24)
        self.close_button.clicked.connect(self.close_requested.emit)
        
        # Settings button
        self.settings_button = QPushButton("⚙")
        self.settings_button.setFixedSize(24, 24)
        self.settings_button.clicked.connect(self.settings_clicked.emit)
        
        # Clean button styling
        button_style = """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.8);
                border: none;
                border-radius: 12px;
                color: rgba(0, 0, 0, 0.6);
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 1.0);
                color: rgba(0, 0, 0, 0.87);
            }
            QPushButton:pressed {
                background-color: rgba(0, 0, 0, 0.1);
            }
        """
        
        # Special styling for close button (red hover)
        close_button_style = """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.8);
                border: none;
                border-radius: 12px;
                color: rgba(0, 0, 0, 0.6);
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: rgba(244, 67, 54, 0.9);
                color: rgba(255, 255, 255, 0.87);
            }
            QPushButton:pressed {
                background-color: rgba(244, 67, 54, 1.0);
            }
        """
        
        self.minimize_button.setStyleSheet(button_style)
        self.close_button.setStyleSheet(close_button_style)
        self.settings_button.setStyleSheet(button_style)
        
        controls_layout.addStretch()
        controls_layout.addWidget(self.minimize_button)
        controls_layout.addWidget(self.close_button)
        controls_layout.addWidget(self.settings_button)
        
        parent_layout.addLayout(controls_layout)
        
        # Enable drag-to-move
        self.drag_position = None
    
    def _setup_animations(self):
        """Setup clean animations for various UI elements."""
        # Smooth opacity animation
        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_animation.setDuration(300)
        self.opacity_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    
    def _setup_resize_behavior(self):
        """Setup custom resize behavior and constraints."""
        # Make the window resizable by adding resize grips
        # Since we're frameless, we need custom resize handling
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.resize_margin = 8  # Margin for resize detection
        self.resize_direction = None
        self.resize_start_pos = None
        self.resize_start_geometry = None
    
    def _position_window(self):
        """Position the window according to configuration."""
        screen = self.screen()
        if screen:
            screen_geometry = screen.geometry()
            
            # Get current size or use preferred size
            current_width = self.width() if self.width() > 0 else self.preferred_size['width']
            current_height = self.height() if self.height() > 0 else self.preferred_size['height']
            
            if self.position == 'top-right':
                x = screen_geometry.width() - current_width - 24
                y = 24
            elif self.position == 'top-left':
                x = 24
                y = 24
            elif self.position == 'bottom-right':
                x = screen_geometry.width() - current_width - 24
                y = screen_geometry.height() - current_height - 80
            elif self.position == 'bottom-left':
                x = 24
                y = screen_geometry.height() - current_height - 80
            elif self.position == 'center':
                x = (screen_geometry.width() - current_width) // 2
                y = (screen_geometry.height() - current_height) // 2
            else:
                x = screen_geometry.width() - current_width - 24
                y = 24
            
            self.move(x, y)
            
        # Start hidden for cleaner experience
        self.hide()
    
    def update_status(self, status: str, state: str = "processing"):
        """Update the overlay status with clean Material Design visual feedback."""
        self.current_state = state
        self.status_text.setText(status)
        
        # Update status card
        if 'status' in self.status_cards:
            self.status_cards['status'].update_value(state.title())
        
        # Use Material Design colors
        color = self.COLORS.get(state, self.COLORS['processing'])
        self.status_indicator.set_color(color)
        
        if state in ['listening', 'processing']:
            self.status_indicator.start_animation()
            self.progress_bar.show()
            if state == 'processing':
                self._animate_progress()
        else:
            self.status_indicator.stop_animation()
            self.progress_bar.hide()
        
        # Show overlay and start auto-hide timer
        self.show_overlay()
        self._start_auto_hide_timer()
        
        # Add to activity log
        self.activity_log.append({
            'timestamp': time.time(),
            'status': status,
            'state': state
        })
        
        # Keep only last 10 entries
        if len(self.activity_log) > 10:
            self.activity_log.pop(0)
    
    def update_persistent_status(self, status: str, state: str = "idle"):
        """
        Update the status text and show the overlay without auto-hide.
        For compatibility with standard overlay interface.
        
        Args:
            status: Status text to display
            state: State indicator (default: "idle")
        """
        # Update status normally
        self.current_state = state
        self.status_text.setText(status)
        
        # Update status card
        if 'status' in self.status_cards:
            self.status_cards['status'].update_value(state.title())
        
        # Use Material Design colors
        color = self.COLORS.get(state, self.COLORS['idle'])
        self.status_indicator.set_color(color)
        
        if state in ['listening', 'processing']:
            self.status_indicator.start_animation()
        else:
            self.status_indicator.stop_animation()
        
        # Show overlay but DON'T start auto-hide timer (persistent)
        self.show_overlay()
        self.hide_timer.stop()  # Stop any existing auto-hide timer
        
        print(f"Persistent visual status updated: {status} [{state}]")
    
    def update_confidence(self, confidence: float):
        """Update confidence display."""
        if 'confidence' in self.status_cards:
            if confidence > 0:
                self.status_cards['confidence'].update_value(f"{confidence:.1%}")
            else:
                self.status_cards['confidence'].update_value("N/A")
    
    def update_model_info(self, model_name: str):
        """Update model information display."""
        if 'model' in self.status_cards:
            # Truncate long model names
            display_name = model_name.split(':')[0] if ':' in model_name else model_name
            if len(display_name) > 10:
                display_name = display_name[:8] + "..."
            self.status_cards['model'].update_value(display_name)
    
    def increment_action_count(self):
        """Increment the action counter."""
        if 'actions' in self.status_cards:
            current = self.status_cards['actions'].value_label.text()
            try:
                count = int(current) + 1
                self.status_cards['actions'].update_value(str(count))
            except ValueError:
                self.status_cards['actions'].update_value("1")
    
    def show_overlay(self):
        """Show the overlay with animation."""
        if not self.isVisible():
            self.show()
            self.opacity_animation.setStartValue(0.0)
            self.opacity_animation.setEndValue(self.opacity)
            self.opacity_animation.start()
    
    def hide_overlay(self):
        """Hide the overlay with animation."""
        if self.isVisible():
            self.opacity_animation.setStartValue(self.opacity)
            self.opacity_animation.setEndValue(0.0)
            self.opacity_animation.finished.connect(self.hide)
            self.opacity_animation.start()
    
    def toggle_minimize(self):
        """Toggle between minimized and full view with dynamic sizing."""
        if not self.is_minimized:
            # Minimize: hide dashboard and progress, save current size
            self.dashboard_widget.hide()
            self.progress_widget.hide()
            self.saved_size = self.size()  # Save current size
            
            # Set minimized size
            minimized_height = 80
            self.resize(self.width(), minimized_height)
            self.is_minimized = True
        else:
            # Restore: show all components, restore size
            self.dashboard_widget.show()
            self.progress_widget.show()
            
            # Restore previous size or use preferred size
            if hasattr(self, 'saved_size'):
                self.resize(self.saved_size)
            else:
                self.resize(self.preferred_size['width'], self.preferred_size['height'])
            self.is_minimized = False
        
        # Reposition window after size change
        self._position_window()
    
    def _animate_progress(self):
        """Animate progress bar for processing states."""
        # Simple indeterminate progress animation
        timer = QTimer(self)
        timer.timeout.connect(lambda: self._update_progress(timer))
        timer.start(100)
        setattr(self, '_progress_timer', timer)
    
    def _update_progress(self, timer):
        """Update progress bar animation."""
        if self.current_state != 'processing':
            timer.stop()
            self.progress_bar.setValue(0)
            return
        
        current = self.progress_bar.value()
        if current >= 90:
            self.progress_bar.setValue(10)
        else:
            self.progress_bar.setValue(current + 10)
    
    def _start_auto_hide_timer(self):
        """Start timer for auto-hiding overlay."""
        timeout = self.config.get('status_timeout', 5000)
        self.hide_timer.stop()
        self.hide_timer.start(timeout)
    
    def _auto_hide(self):
        """Auto-hide the overlay if in idle state."""
        if self.current_state in ['idle', 'success']:
            self.hide_overlay()
    
    def mousePressEvent(self, event):
        """Handle mouse press for dragging and resizing."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if we're in a resize area
            self.resize_direction = self._get_resize_direction(event.position().toPoint())
            
            if self.resize_direction:
                # Start resize operation
                self.resize_start_pos = event.globalPosition().toPoint()
                self.resize_start_geometry = self.geometry()
            else:
                # Start drag operation
                self.drag_start_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging and resizing."""
        if event.buttons() == Qt.MouseButton.LeftButton:
            if self.resize_direction and hasattr(self, 'resize_start_pos'):
                # Handle resize
                self._handle_resize(event.globalPosition().toPoint())
            elif hasattr(self, 'drag_start_position'):
                # Handle drag
                self.move(event.globalPosition().toPoint() - self.drag_start_position)
        else:
            # Update cursor for resize hints
            direction = self._get_resize_direction(event.position().toPoint())
            self._update_cursor_for_resize(direction)

    def mouseReleaseEvent(self, event):
        """Handle mouse release to end resize/drag operations."""
        if event.button() == Qt.MouseButton.LeftButton:
            if self.resize_direction:
                # End resize operation
                self.resize_direction = None
                self.resize_start_pos = None
                self.resize_start_geometry = None
                
                # Save new size to preferences
                self.preferred_size['width'] = self.width()
                self.preferred_size['height'] = self.height()
                self._save_size_preferences()
            
            # Clear drag position
            if hasattr(self, 'drag_start_position'):
                delattr(self, 'drag_start_position')

    def _handle_resize(self, global_pos):
        """Handle window resizing based on drag direction."""
        if not self.resize_start_pos or not self.resize_start_geometry:
            return
            
        delta = global_pos - self.resize_start_pos
        new_rect = QRect(self.resize_start_geometry)
        
        # Apply resize based on direction
        if 'right' in self.resize_direction:
            new_rect.setWidth(max(self.min_size['width'], 
                                min(self.max_size['width'], 
                                   self.resize_start_geometry.width() + delta.x())))
        elif 'left' in self.resize_direction:
            new_width = max(self.min_size['width'], 
                           min(self.max_size['width'], 
                              self.resize_start_geometry.width() - delta.x()))
            new_rect.setWidth(new_width)
            new_rect.setX(self.resize_start_geometry.x() + 
                         (self.resize_start_geometry.width() - new_width))
        
        if 'bottom' in self.resize_direction:
            new_rect.setHeight(max(self.min_size['height'], 
                                  min(self.max_size['height'], 
                                     self.resize_start_geometry.height() + delta.y())))
        elif 'top' in self.resize_direction:
            new_height = max(self.min_size['height'], 
                            min(self.max_size['height'], 
                               self.resize_start_geometry.height() - delta.y()))
            new_rect.setHeight(new_height)
            new_rect.setY(self.resize_start_geometry.y() + 
                         (self.resize_start_geometry.height() - new_height))
        
        self.setGeometry(new_rect)

    def _save_size_preferences(self):
        """Save current size preferences to config."""
        try:
            # Update the config in memory
            if 'ui' not in self.config:
                self.config['ui'] = {}
            self.config['ui']['overlay_size'] = {
                'width': self.preferred_size['width'],
                'height': self.preferred_size['height']
            }
            
            # Save to config.json file if it exists
            config_path = 'config.json'
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    full_config = json.load(f)
                
                if 'ui' not in full_config:
                    full_config['ui'] = {}
                full_config['ui']['overlay_size'] = {
                    'width': self.preferred_size['width'],
                    'height': self.preferred_size['height']
                }
                
                with open(config_path, 'w') as f:
                    json.dump(full_config, f, indent=2)
                    
                print(f"Size preferences saved to config: {self.preferred_size['width']}x{self.preferred_size['height']}")
            else:
                print(f"Size preferences updated: {self.preferred_size['width']}x{self.preferred_size['height']}")
                
        except Exception as e:
            print(f"Error saving size preferences: {e}")
            print(f"Size preferences updated: {self.preferred_size['width']}x{self.preferred_size['height']}")

    def resizeEvent(self, event):
        """Handle resize events to maintain layout."""
        super().resizeEvent(event)
        # Ensure minimum content is visible when resized
        if self.width() < self.min_size['width'] or self.height() < self.min_size['height']:
            self.resize(max(self.width(), self.min_size['width']), 
                       max(self.height(), self.min_size['height']))

    def closeEvent(self, event):
        """Handle close event."""
        self.hide_overlay()
        event.ignore()

    def _get_resize_direction(self, pos):
        """Determine resize direction based on mouse position."""
        rect = self.rect()
        margin = 8  # Margin for resize detection
        
        # Check corners first (for diagonal resize)
        if pos.x() <= margin and pos.y() <= margin:
            return 'top-left'
        elif pos.x() >= rect.width() - margin and pos.y() <= margin:
            return 'top-right'
        elif pos.x() <= margin and pos.y() >= rect.height() - margin:
            return 'bottom-left'
        elif pos.x() >= rect.width() - margin and pos.y() >= rect.height() - margin:
            return 'bottom-right'
        
        # Check edges
        elif pos.x() <= margin:
            return 'left'
        elif pos.x() >= rect.width() - margin:
            return 'right'
        elif pos.y() <= margin:
            return 'top'
        elif pos.y() >= rect.height() - margin:
            return 'bottom'
        
        return None
    
    def _update_cursor_for_resize(self, direction):
        """Update cursor based on resize direction."""
        cursor_map = {
            'top': Qt.CursorShape.SizeVerCursor,
            'bottom': Qt.CursorShape.SizeVerCursor,
            'left': Qt.CursorShape.SizeHorCursor,
            'right': Qt.CursorShape.SizeHorCursor,
            'top-left': Qt.CursorShape.SizeFDiagCursor,
            'bottom-right': Qt.CursorShape.SizeFDiagCursor,
            'top-right': Qt.CursorShape.SizeBDiagCursor,
            'bottom-left': Qt.CursorShape.SizeBDiagCursor,
        }
        
        if direction in cursor_map:
            self.setCursor(cursor_map[direction])
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
