import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLineEdit, QTextEdit, QSizeGrip
from PyQt5.QtCore import Qt, pyqtSignal, QPoint
from PyQt5.QtGui import QCursor

if sys.platform == "win32":
    import win32gui, win32con

class OverlayWindow(QMainWindow):
    # Signals to communicate with main application
    sight_mode_toggled = pyqtSignal(bool)
    audio_mode_toggled = pyqtSignal(bool)
    text_input_submitted = pyqtSignal(str)
    close_requested = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Set minimum and maximum sizes for resizing
        self.setMinimumSize(200, 80)
        self.setMaximumSize(800, 600)
        
        # Track conversation state
        self.current_user_question = ""
        self.is_streaming = False
        self.pending_question = ""
        self.continue_button = None
        
        self.container = QWidget()
        self.main_layout = QVBoxLayout(self.container)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(10)

        self.top_bar = self._create_top_bar()
        self.bottom_bar = self._create_bottom_bar()

        self.main_layout.addWidget(self.top_bar)
        self.main_layout.addWidget(self.bottom_bar)
        self.setCentralWidget(self.container)
        
        # Add resize grip for easy resizing
        self.size_grip = QSizeGrip(self)
        self.size_grip.setStyleSheet("QSizeGrip { background-color: rgba(0,0,0,0.3); }")
        
        self.adjustSize()
        self._position_window()
        
        # Initial text input sizing
        self._update_text_input_size()
        
        # Variables for window dragging and resizing
        self._drag_pos = None
        self._resize_mode = None
        self._resize_start_pos = None
        self._resize_start_geometry = None

    def _create_top_bar(self):
        bar = QWidget()
        bar.setMinimumHeight(40) # Even smaller minimum height for compact design
        bar.setStyleSheet(self._get_bar_style())
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 3, 8, 3) # Smaller margins for compact design
        layout.setSpacing(6) # Reduced spacing for more compact layout

        self.sight_button = self._create_button("👁️")
        self.audio_button = self._create_button("🎤")
        self.sight_button.setToolTip("Toggle sight mode (screen scanning)")
        self.audio_button.setToolTip("Toggle audio mode (voice listening)")
        self.sight_button.toggled.connect(self.sight_mode_toggled.emit)
        self.audio_button.toggled.connect(self.audio_mode_toggled.emit)

        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Ask AI... (Press Enter to send, Shift+Enter for new line)")
        self.text_input.setMinimumHeight(22) # Minimum height for readability
        self.text_input.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff) # Hide vertical scrollbar
        self.text_input.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff) # Hide horizontal scrollbar
        self.text_input.setStyleSheet("background-color: rgba(255, 255, 255, 0.7); border: 1px solid rgba(204, 204, 204, 0.8); border-radius: 6px; padding: 4px 8px; color: #333; font-size: 12px;")
        self.text_input.textChanged.connect(self._adjust_text_height)
        
        send_button = QPushButton("→")
        send_button.setStyleSheet("background-color: #007AFF; color: white; border: none; border-radius: 6px; padding: 4px 8px; font-size: 14px; font-weight: bold;")
        send_button.setFixedSize(30, 24)
        send_button.clicked.connect(self._on_text_submit)
        send_button.setToolTip("Send message (or press Enter)")
        
        close_button = QPushButton("×")
        close_button.setStyleSheet("background-color: transparent; color: #666; border: none; font-size: 18px; font-weight: normal;")
        close_button.setFixedSize(25, 25)
        close_button.setToolTip("Close Dia Assistant")
        close_button.clicked.connect(self.close_requested.emit)

        layout.addWidget(self.sight_button)
        layout.addWidget(self.audio_button)
        layout.addWidget(self.text_input, 1) # Set stretch factor to fill space
        layout.addWidget(send_button)
        layout.addWidget(close_button)
        return bar

    def _create_bottom_bar(self):
        bar = QWidget()
        bar.setMaximumHeight(300) # Allow more space for scrollable conversation
        bar.setStyleSheet(self._get_bar_style())
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(15, 12, 15, 12)

        # Replace QLabel with scrollable QTextEdit for conversation history
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setPlainText("Sight and Audio are off. Type a question or enable a mode.")
        self.status_text.setStyleSheet("""
            QTextEdit {
                color: #555; 
                background-color: transparent; 
                font-size: 13px;
                border: none;
                padding: 5px;
            }
            QScrollBar:vertical {
                background-color: rgba(200, 200, 200, 0.3);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(100, 100, 100, 0.5);
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: rgba(100, 100, 100, 0.7);
            }
        """)
        self.status_text.setMinimumHeight(40)  # Ensure minimum height for text
        self.status_text.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.status_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        layout.addWidget(self.status_text, 1)  # Give full width to status text
        return bar

    # Spinner methods removed - no longer using spinner UI

    def update_status(self, text: str):
        """Update the status text with a static message."""
        self.status_text.setPlainText(text)
        self.adjustSize()
        self.show()

    def add_user_question(self, question: str):
        """Add a user question to the conversation."""
        current_text = self.status_text.toPlainText()
        is_first_question = (not current_text.strip() or 
                           current_text.endswith("Type a question or enable a mode."))
        
        if current_text.strip() and not current_text.endswith("Type a question or enable a mode."):
            # Add spacing between conversations
            new_text = current_text + "\n\n" + f"You: {question}\n"
        else:
            # First question or replacing initial message
            new_text = f"You: {question}\n"
        
        self.status_text.setPlainText(new_text)
        self.current_user_question = question
        self._scroll_to_bottom()
        
        if is_first_question:
            # For first question, auto-continue since there's nothing to read
            print("[OverlayWindow] First question - auto-continuing")
            if self.pending_question:
                self.text_input_submitted.emit(self.pending_question)
                self.pending_question = ""
        else:
            # Show continue button to let user read previous content before new response
            self._show_continue_button()

    def _on_stream_start(self):
        print("[OverlayWindow] Stream started")
        self.is_streaming = True
        
        # Hide continue button when streaming starts
        self._hide_continue_button()
        
        # Add "AI:" prefix for the response
        current_text = self.status_text.toPlainText()
        if not current_text.endswith("\n"):
            current_text += "\n"
        new_text = current_text + "AI: "
        self.status_text.setPlainText(new_text)
        
        # Make AI response text more visible
        self.status_text.setStyleSheet("""
            QTextEdit {
                color: #333; 
                background-color: transparent; 
                font-size: 13px;
                border: none;
                padding: 5px;
                font-weight: 500;
            }
            QScrollBar:vertical {
                background-color: rgba(200, 200, 200, 0.3);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(100, 100, 100, 0.5);
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: rgba(100, 100, 100, 0.7);
            }
        """)
        self._scroll_to_bottom()

    def _on_stream_content(self, content: str):
        print(f"[OverlayWindow] Stream content: {content!r}")
        
        # Append content to the existing text
        current_text = self.status_text.toPlainText()
        new_text = current_text + content
        self.status_text.setPlainText(new_text)
        
        # Auto-scroll to bottom to show new content
        self._scroll_to_bottom()
        QApplication.processEvents() # Ensure UI updates are shown immediately
        
        # Force the window to show and update
        self.show()
        self.raise_()

    def _on_stream_end(self):
        print("[OverlayWindow] Stream ended")
        self.is_streaming = False
        
        # Reset to normal text color
        self.status_text.setStyleSheet("""
            QTextEdit {
                color: #555; 
                background-color: transparent; 
                font-size: 13px;
                border: none;
                padding: 5px;
            }
            QScrollBar:vertical {
                background-color: rgba(200, 200, 200, 0.3);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(100, 100, 100, 0.5);
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: rgba(100, 100, 100, 0.7);
            }
        """)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        """Scroll the text area to the bottom to show latest content."""
        scrollbar = self.status_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _show_continue_button(self):
        """Show a continue button to let user read previous content before new response."""
        if self.continue_button is None:
            self.continue_button = QPushButton("Continue →")
            self.continue_button.setStyleSheet("""
                QPushButton {
                    background-color: #007AFF;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-size: 13px;
                    font-weight: 500;
                    margin: 5px;
                }
                QPushButton:hover {
                    background-color: #0056CC;
                }
                QPushButton:pressed {
                    background-color: #004AAD;
                }
            """)
            self.continue_button.clicked.connect(self._on_continue_clicked)
            self.continue_button.setToolTip("Click to get AI response (or press Enter with empty input)")
            
            # Add button to the bottom bar layout
            layout = self.bottom_bar.layout()
            layout.addWidget(self.continue_button)
        
        self.continue_button.show()
        self.adjustSize()

    def _hide_continue_button(self):
        """Hide the continue button."""
        if self.continue_button:
            self.continue_button.hide()
            self.adjustSize()

    def _on_continue_clicked(self):
        """Handle continue button click - start AI processing."""
        print(f"[OverlayWindow] Continue clicked for question: {self.pending_question}")
        self._hide_continue_button()
        
        if self.pending_question:
            # Now emit the signal to start AI processing
            self.text_input_submitted.emit(self.pending_question)
            self.pending_question = ""

    def _on_text_submit(self):
        text = self.text_input.toPlainText().strip()
        if text:
            # Store the pending question and add to display
            self.pending_question = text
            self.add_user_question(text)
            self.text_input.clear()
            # Don't emit signal yet - wait for continue button click
    
    def _adjust_text_height(self):
        """Dynamically adjust text input height based on content and window size."""
        doc = self.text_input.document()
        doc.setTextWidth(self.text_input.width() - 20) # Account for padding and potential scrollbar
        
        # Calculate ideal height based on content
        content_height = int(doc.size().height() + 8) # Add padding
        
        # Calculate maximum height based on window size (25% of window height or 80px, whichever is larger)
        window_height = self.height()
        max_text_height = max(80, int(window_height * 0.25))
        
        # Determine appropriate height
        if content_height <= 30:
            # For small content, use exact height but ensure minimum
            height = max(22, content_height)
        elif content_height <= max_text_height:
            # For medium content, grow the box up to the window-based limit
            height = content_height
        else:
            # For large content, cap at window-based maximum and enable scrolling
            height = max_text_height
            
        self.text_input.setFixedHeight(height)
        self._update_text_input_size() # Update width as well
    
    def _update_text_input_size(self):
        """Update text input size based on window dimensions."""
        # Calculate font size based on window width (responsive typography)
        window_width = self.width()
        base_font_size = 12
        if window_width < 300:
            font_size = 10
        elif window_width < 400:
            font_size = 11  
        elif window_width > 600:
            font_size = 14
        else:
            font_size = base_font_size
            
        # Update text input styling with responsive font size
        self.text_input.setStyleSheet(f"background-color: rgba(255, 255, 255, 0.7); border: 1px solid rgba(204, 204, 204, 0.8); border-radius: 6px; padding: 4px 8px; color: #333; font-size: {font_size}px;")
    
    def keyPressEvent(self, event):
        """Handle key press events for text input."""
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if event.modifiers() & Qt.ShiftModifier:
                # Shift+Enter for new line - let default behavior handle it
                super().keyPressEvent(event)
            else:
                # Enter to submit or continue
                if self.text_input.toPlainText().strip():
                    # Text input has content - submit question
                    self._on_text_submit()
                elif self.continue_button and self.continue_button.isVisible():
                    # No text but continue button is visible - trigger continue
                    self._on_continue_clicked()
                event.accept()
        else:
            super().keyPressEvent(event)

    # --- Styles, positioning and event handlers ---
    def _get_bar_style(self): return "background-color: rgba(240, 240, 240, 0.6); border-radius: 12px;"
    def _get_button_style(self, checked):
        if checked:
            # Enabled: Bright blue background, white icon
            return "background-color: #007AFF; color: white; border: none; border-radius: 50%; padding: 8px; font-size: 16px;"
        else:
            # Disabled: Faded background, grayed-out icon
            return "background-color: rgba(200, 200, 200, 0.3); color: #999; border: none; border-radius: 50%; padding: 8px; font-size: 16px;"
    def _create_button(self, text):
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setFixedSize(32, 32)  # Make buttons perfectly circular
        btn.setStyleSheet(self._get_button_style(False))
        btn.toggled.connect(lambda checked, b=btn: b.setStyleSheet(self._get_button_style(checked)))
        return btn
    def _position_window(self):
        try:
            screen = QApplication.primaryScreen().geometry()
            self.move((screen.width() - self.width()) // 2, int(screen.height() * 0.10))
        except Exception as e: print(f"Could not position overlay: {e}", file=sys.stderr)
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._resize_mode = self._get_resize_mode(e.pos())
            if self._resize_mode:
                self._resize_start_pos = e.globalPos()
                self._resize_start_geometry = self.geometry()
            else:
                self._drag_pos = e.globalPos()
    
    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton:
            if self._resize_mode:
                self._do_resize(e.globalPos())
            elif self._drag_pos:
                self.move(self.pos() + e.globalPos() - self._drag_pos)
                self._drag_pos = e.globalPos()
        else:
            # Update cursor based on position
            resize_mode = self._get_resize_mode(e.pos())
            if resize_mode:
                self._set_cursor_for_resize(resize_mode)
            else:
                self.setCursor(QCursor(Qt.ArrowCursor))
    
    def mouseReleaseEvent(self, e):
        self._drag_pos = None
        self._resize_mode = None
        self._resize_start_pos = None
        self._resize_start_geometry = None
    
    def _get_resize_mode(self, pos):
        """Determine resize mode based on mouse position."""
        margin = 10  # Resize area width
        rect = self.rect()
        
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
    
    def _set_cursor_for_resize(self, resize_mode):
        """Set appropriate cursor for resize mode."""
        cursors = {
            'top-left': Qt.SizeFDiagCursor,
            'top-right': Qt.SizeBDiagCursor,
            'bottom-left': Qt.SizeBDiagCursor,
            'bottom-right': Qt.SizeFDiagCursor,
            'left': Qt.SizeHorCursor,
            'right': Qt.SizeHorCursor,
            'top': Qt.SizeVerCursor,
            'bottom': Qt.SizeVerCursor,
        }
        self.setCursor(QCursor(cursors.get(resize_mode, Qt.ArrowCursor)))
    
    def _do_resize(self, global_pos):
        """Perform the resize based on current mode."""
        if not self._resize_mode or not self._resize_start_pos or not self._resize_start_geometry:
            return
        
        delta = global_pos - self._resize_start_pos
        geo = self._resize_start_geometry
        
        new_x, new_y = geo.x(), geo.y()
        new_width, new_height = geo.width(), geo.height()
        
        # Apply resize based on mode
        if 'left' in self._resize_mode:
            new_x = geo.x() + delta.x()
            new_width = geo.width() - delta.x()
        if 'right' in self._resize_mode:
            new_width = geo.width() + delta.x()
        if 'top' in self._resize_mode:
            new_y = geo.y() + delta.y()
            new_height = geo.height() - delta.y()
        if 'bottom' in self._resize_mode:
            new_height = geo.height() + delta.y()
        
        # Enforce minimum and maximum sizes
        min_size = self.minimumSize()
        max_size = self.maximumSize()
        
        if new_width < min_size.width():
            if 'left' in self._resize_mode:
                new_x = geo.x() + geo.width() - min_size.width()
            new_width = min_size.width()
        elif new_width > max_size.width():
            if 'left' in self._resize_mode:
                new_x = geo.x() + geo.width() - max_size.width()
            new_width = max_size.width()
        
        if new_height < min_size.height():
            if 'top' in self._resize_mode:
                new_y = geo.y() + geo.height() - min_size.height()
            new_height = min_size.height()
        elif new_height > max_size.height():
            if 'top' in self._resize_mode:
                new_y = geo.y() + geo.height() - max_size.height()
            new_height = max_size.height()
        
        self.setGeometry(new_x, new_y, new_width, new_height)
    
    def resizeEvent(self, event):
        """Position the size grip and update text input size when window is resized."""
        super().resizeEvent(event)
        # Position size grip at bottom-right corner
        grip_size = self.size_grip.sizeHint()
        self.size_grip.move(
            self.width() - grip_size.width(),
            self.height() - grip_size.height()
        )
        # Update text input size based on new window dimensions
        if hasattr(self, 'text_input'):
            self._adjust_text_height()
    
    def showEvent(self, e):
        super().showEvent(e)
        if sys.platform == "win32":
            try: # Remove click-through style
                hwnd = int(self.winId()); style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                style &= ~win32con.WS_EX_TRANSPARENT; win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)
            except Exception as e: print(f"Could not set window style: {e}", file=sys.stderr)
