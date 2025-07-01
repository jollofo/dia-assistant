"""
Screen Scanner Module
Provides on-demand screen capture and OCR functionality with continuous monitoring.
"""

import mss
from PIL import Image
import logging
from typing import Dict, Any, Optional, Tuple, Callable
import io
import subprocess
import sys
import os
import threading
import time
import hashlib

class ScreenScanner:
    """
    Handles screen capture and optical character recognition (OCR) functionality.
    Supports both on-demand scanning and continuous monitoring for changes.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Thread-local storage for mss instances
        self._thread_local = threading.local()
        
        # Configure Tesseract path explicitly
        self._configure_tesseract_path()
        
        # Check if tesseract is available
        self.tesseract_available = self._check_tesseract_installation()
        
        # Continuous monitoring state
        self._monitoring_active = False
        self._monitoring_thread = None
        self._stop_monitoring = threading.Event()
        self._last_screen_hash = None
        self._last_screen_text = ""
        self._change_callback = None
        
        # Monitoring configuration
        self._monitor_interval = config.get('screen_monitoring', {}).get('interval_seconds', 3)
        self._min_change_chars = config.get('screen_monitoring', {}).get('min_change_chars', 50)
        
        self.logger.info(f"ScreenScanner initialized - Tesseract available: {self.tesseract_available}")
        
    def _get_mss_instance(self):
        """Get or create a thread-local mss instance."""
        try:
            if not hasattr(self._thread_local, 'sct'):
                self._thread_local.sct = mss.mss()
            return self._thread_local.sct
        except Exception as e:
            self.logger.warning(f"Failed to create thread-local mss instance: {e}")
            # Fallback to creating a new instance each time
            return mss.mss()
        
    def _configure_tesseract_path(self):
        """
        Explicitly configure Tesseract executable path to solve PATH issues.
        """
        try:
            import pytesseract
            
            # Common Tesseract installation paths on Windows
            possible_paths = [
                r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
                r'C:\Users\{}\AppData\Local\Tesseract-OCR\tesseract.exe'.format(os.getenv('USERNAME', '')),
                r'C:\tesseract\tesseract.exe'
            ]
            
            # Try to find existing tesseract executable
            tesseract_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    tesseract_path = path
                    break
                    
            if tesseract_path:
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
                self.logger.info(f"Tesseract path configured: {tesseract_path}")
            else:
                self.logger.warning("Tesseract executable not found in common paths")
                
        except ImportError:
            self.logger.warning("pytesseract not installed")
        except Exception as e:
            self.logger.warning(f"Error configuring tesseract path: {e}")
        
    def _check_tesseract_installation(self) -> bool:
        """
        Check if tesseract is installed and accessible.
        
        Returns:
            True if tesseract is available, False otherwise
        """
        try:
            # Try to import pytesseract
            import pytesseract
            
            # Try to get tesseract version using pytesseract
            version = pytesseract.get_tesseract_version()
            self.logger.info(f"Tesseract found: {version}")
            return True
                
        except Exception as e:
            self.logger.warning(f"Tesseract not available: {e}")
            return False
            
    def capture_full_screen(self) -> Optional[Image.Image]:
        """
        Capture the entire screen.
        
        Returns:
            PIL Image object of the screen capture, or None if failed
        """
        try:
            # Get thread-local mss instance
            sct = self._get_mss_instance()
            
            # Get all monitors and capture the primary one
            monitors = sct.monitors
            primary_monitor = monitors[1] if len(monitors) > 1 else monitors[0]
            
            # Capture screenshot
            screenshot = sct.grab(primary_monitor)
            
            # Convert to PIL Image
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            
            self.logger.debug("Full screen captured successfully")
            return img
            
        except Exception as e:
            self.logger.error(f"Failed to capture full screen: {e}")
            return None
            
    def capture_region(self, x: int, y: int, width: int, height: int) -> Optional[Image.Image]:
        """
        Capture a specific region of the screen.
        
        Args:
            x: X coordinate of the top-left corner
            y: Y coordinate of the top-left corner
            width: Width of the region
            height: Height of the region
            
        Returns:
            PIL Image object of the region capture, or None if failed
        """
        try:
            # Get thread-local mss instance
            sct = self._get_mss_instance()
            
            # Define the region to capture
            region = {
                "top": y,
                "left": x,
                "width": width,
                "height": height
            }
            
            # Capture the region
            screenshot = sct.grab(region)
            
            # Convert to PIL Image
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            
            self.logger.debug(f"Region captured: {x},{y} {width}x{height}")
            return img
            
        except Exception as e:
            self.logger.error(f"Failed to capture region: {e}")
            return None
            
    def extract_text_from_image(self, image: Image.Image) -> Optional[str]:
        """
        Extract text from an image using OCR.
        
        Args:
            image: PIL Image object to process
            
        Returns:
            Extracted text string, or None if failed
        """
        if not self.tesseract_available:
            error_msg = (
                "Tesseract OCR is not installed or not accessible. "
                "Please install Tesseract OCR:\n"
                "1. Download from: https://github.com/UB-Mannheim/tesseract/wiki\n"
                "2. Install and make sure 'Add to PATH' is checked\n"
                "3. Restart the application"
            )
            self.logger.error(error_msg)
            return f"OCR_ERROR: {error_msg}"
            
        try:
            import pytesseract
            
            # Perform OCR on the image
            text = pytesseract.image_to_string(image, lang='eng')
            
            # Clean up the extracted text
            text = text.strip()
            
            self.logger.debug(f"OCR extracted {len(text)} characters")
            return text if text else "No text detected in image"
            
        except Exception as e:
            error_msg = f"Failed to extract text from image: {e}"
            self.logger.error(error_msg)
            return f"OCR_ERROR: {error_msg}"
            
    def capture_and_extract_text(self) -> Optional[str]:
        """
        Convenience method to capture the full screen and extract text.
        
        Returns:
            Extracted text from the full screen, or error message if failed
        """
        if not self.tesseract_available:
            return (
                "Tesseract OCR not installed. Please install it from: "
                "https://github.com/UB-Mannheim/tesseract/wiki"
            )
            
        image = self.capture_full_screen()
        if image:
            return self.extract_text_from_image(image)
        else:
            return "Failed to capture screen"
            
    def capture_region_and_extract_text(self, x: int, y: int, width: int, height: int) -> Optional[str]:
        """
        Convenience method to capture a region and extract text.
        
        Args:
            x: X coordinate of the top-left corner
            y: Y coordinate of the top-left corner
            width: Width of the region
            height: Height of the region
            
        Returns:
            Extracted text from the region, or error message if failed
        """
        if not self.tesseract_available:
            return (
                "Tesseract OCR not installed. Please install it from: "
                "https://github.com/UB-Mannheim/tesseract/wiki"
            )
            
        image = self.capture_region(x, y, width, height)
        if image:
            return self.extract_text_from_image(image)
        else:
            return "Failed to capture screen region"
            
    def save_screenshot(self, filename: str, x: int = None, y: int = None, 
                       width: int = None, height: int = None) -> bool:
        """
        Save a screenshot to file.
        
        Args:
            filename: Path to save the screenshot
            x, y, width, height: Optional region coordinates. If None, captures full screen
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if all(param is not None for param in [x, y, width, height]):
                image = self.capture_region(x, y, width, height)
            else:
                image = self.capture_full_screen()
                
            if image:
                image.save(filename)
                self.logger.info(f"Screenshot saved to: {filename}")
                return True
            else:
                self.logger.error("Failed to capture image for saving")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to save screenshot: {e}")
            return False
            
    def get_screen_dimensions(self) -> Tuple[int, int]:
        """
        Get the dimensions of the primary screen.
        
        Returns:
            Tuple of (width, height)
        """
        try:
            sct = self._get_mss_instance()
            monitors = sct.monitors
            primary_monitor = monitors[1] if len(monitors) > 1 else monitors[0]
            
            width = primary_monitor["width"]
            height = primary_monitor["height"]
            
            return width, height
            
        except Exception as e:
            self.logger.error(f"Failed to get screen dimensions: {e}")
            return 1920, 1080  # Default fallback
            
    def get_monitor_count(self) -> int:
        """
        Get the number of available monitors.
        
        Returns:
            Number of monitors
        """
        try:
            sct = self._get_mss_instance()
            return len(sct.monitors) - 1  # Subtract 1 to exclude the "all monitors" entry
        except Exception as e:
            self.logger.error(f"Failed to get monitor count: {e}")
            return 1
            
    def get_installation_instructions(self) -> str:
        """
        Get installation instructions for tesseract.
        
        Returns:
            Installation instructions string
        """
        return """
Tesseract OCR Installation Instructions:

Windows:
1. Download the latest installer from:
   https://github.com/UB-Mannheim/tesseract/wiki
2. Run the installer (tesseract-ocr-w64-setup-*.exe)
3. During installation, make sure to check "Add to PATH"
4. Restart the Dia AI Assistant

Alternative (if you have package managers):
- Chocolatey: choco install tesseract
- Scoop: scoop install tesseract

After installation, restart the application to use OCR features.
        """ 

    def start_continuous_monitoring(self, change_callback: Callable[[str], None] = None):
        """
        Start continuous screen monitoring for changes.
        
        Args:
            change_callback: Function to call when screen content changes
        """
        if self._monitoring_active:
            self.logger.warning("Screen monitoring is already active")
            return
            
        if not self.tesseract_available:
            self.logger.error("Cannot start monitoring - Tesseract not available")
            return
            
        self._change_callback = change_callback
        self._monitoring_active = True
        self._stop_monitoring.clear()
        
        # Initialize with current screen content
        self._update_baseline_screen()
        
        # Start monitoring thread
        self._monitoring_thread = threading.Thread(
            target=self._monitor_screen_changes,
            daemon=True,
            name="ScreenMonitor"
        )
        self._monitoring_thread.start()
        
        self.logger.info(f"Started continuous screen monitoring (interval: {self._monitor_interval}s)")
        
    def stop_continuous_monitoring(self):
        """Stop continuous screen monitoring."""
        if not self._monitoring_active:
            return
            
        self._monitoring_active = False
        self._stop_monitoring.set()
        
        # Wait for thread to finish
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=2)
            
        self._change_callback = None
        self.logger.info("Stopped continuous screen monitoring")
        
    def _monitor_screen_changes(self):
        """Background thread that monitors for screen changes."""
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while self._monitoring_active and not self._stop_monitoring.is_set():
            try:
                # Capture current screen
                current_text = self.capture_and_extract_text()
                
                if current_text and not current_text.startswith("OCR_ERROR:"):
                    # Reset error counter on success
                    consecutive_errors = 0
                    
                    # Calculate content hash for comparison
                    content_hash = hashlib.md5(current_text.encode()).hexdigest()
                    
                    # Check if content has changed significantly
                    if self._has_significant_change(current_text):
                        self.logger.info("Significant screen content change detected")
                        
                        # Update baseline
                        self._last_screen_hash = content_hash
                        self._last_screen_text = current_text
                        
                        # Notify callback if provided
                        if self._change_callback:
                            try:
                                self._change_callback(current_text)
                            except Exception as e:
                                self.logger.error(f"Error in change callback: {e}")
                else:
                    consecutive_errors += 1
                    
                # Wait for next check
                if not self._stop_monitoring.wait(self._monitor_interval):
                    continue
                else:
                    break
                    
            except Exception as e:
                consecutive_errors += 1
                self.logger.error(f"Error in screen monitoring: {e}")
                
                # If too many consecutive errors, stop monitoring to prevent spam
                if consecutive_errors >= max_consecutive_errors:
                    self.logger.error(f"Too many consecutive errors ({consecutive_errors}), stopping screen monitoring")
                    self._monitoring_active = False
                    break
                    
                time.sleep(1)  # Brief pause before retrying
                
    def _update_baseline_screen(self):
        """Update the baseline screen content for comparison."""
        try:
            current_text = self.capture_and_extract_text()
            if current_text and not current_text.startswith("OCR_ERROR:"):
                self._last_screen_text = current_text
                self._last_screen_hash = hashlib.md5(current_text.encode()).hexdigest()
                self.logger.debug("Updated baseline screen content")
        except Exception as e:
            self.logger.error(f"Error updating baseline screen: {e}")
            
    def _has_significant_change(self, current_text: str) -> bool:
        """
        Check if the current screen content represents a significant change.
        
        Args:
            current_text: Current screen text content
            
        Returns:
            True if change is significant enough to report
        """
        if not self._last_screen_text:
            return True  # First capture is always significant
            
        # Compare text lengths
        length_diff = abs(len(current_text) - len(self._last_screen_text))
        if length_diff < self._min_change_chars:
            return False
            
        # Simple text similarity check
        common_chars = set(current_text.lower()) & set(self._last_screen_text.lower())
        if common_chars and len(common_chars) / max(len(current_text), len(self._last_screen_text)) > 0.8:
            return False  # Too similar
            
        return True
        
    def is_monitoring_active(self) -> bool:
        """Check if continuous monitoring is currently active."""
        return self._monitoring_active
        
    def get_last_screen_content(self) -> str:
        """Get the last captured screen content."""
        return self._last_screen_text 