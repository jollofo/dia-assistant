"""
Screen Scanner Module - Thread-safe screen capture and OCR with fallback mechanisms
"""
import mss
import pytesseract
from PIL import Image, ImageGrab
import io
import json
import threading
import sys
from typing import Optional
import os


class ScreenScanner:
    """
    Thread-safe ScreenScanner that captures screenshots and extracts text using OCR.
    Implements fallback mechanisms to handle threading issues with mss library.
    """
    
    def __init__(self, config: dict):
        """
        Initialize the ScreenScanner with configuration parameters.
        
        Args:
            config: Dictionary containing application configuration settings
        """
        self.config = config
        self.monitor_index = self.config.get('SCREEN_MONITOR_INDEX', 0)
        self.ocr_language = self.config.get('SCREEN_OCR_LANGUAGE', 'eng')
        
        # Set Tesseract command path and TESSDATA_PREFIX environment variable
        tesseract_cmd = self.config.get('TESSERACT_CMD_PATH')
        if tesseract_cmd and os.path.exists(tesseract_cmd):
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
            
            # Derive TESSDATA_PREFIX from the executable path
            tesseract_dir = os.path.dirname(tesseract_cmd)
            tessdata_dir = os.path.join(tesseract_dir, 'tessdata')
            
            if os.path.exists(tessdata_dir):
                os.environ['TESSDATA_PREFIX'] = tessdata_dir
                print(f"Set TESSDATA_PREFIX to: {tessdata_dir}")
            else:
                print(f"Warning: 'tessdata' directory not found at {tessdata_dir}", file=sys.stderr)
        
        # Thread-local storage for MSS instances
        self._thread_local = threading.local()
        
        # Initialize primary MSS instance for monitor discovery
        try:
            self._primary_sct = mss.mss()
            self.monitors = self._primary_sct.monitors
            if self.monitor_index >= len(self.monitors):
                self.monitor_index = 0  # Fallback to primary monitor
            self._mss_available = True
        except Exception as e:
            print(f"Warning: MSS initialization failed: {e}")
            self.monitors = [{"top": 0, "left": 0, "width": 1920, "height": 1080}]  # Default monitor
            self._mss_available = False
        
        print(f"Screen scanner initialized. Using monitor {self.monitor_index}")
        print(f"Available monitors: {len(self.monitors)}")
        print(f"MSS available: {self._mss_available}")
    
    def _get_mss_instance(self):
        """
        Get or create a thread-local MSS instance.
        This solves the threading issue with srcdc attribute.
        
        Returns:
            mss.mss: Thread-local MSS instance or None if failed
        """
        if not self._mss_available:
            return None
            
        if not hasattr(self._thread_local, 'sct'):
            try:
                self._thread_local.sct = mss.mss()
            except Exception as e:
                print(f"Failed to create thread-local MSS instance: {e}")
                return None
        
        return self._thread_local.sct
    
    def _capture_with_mss(self, region=None):
        """
        Capture screenshot using MSS with thread-safe handling.
        
        Args:
            region: Optional region dict for partial capture
            
        Returns:
            PIL.Image: Captured image or None if failed
        """
        try:
            sct = self._get_mss_instance()
            if not sct:
                return None
            
            if region:
                screenshot = sct.grab(region)
            else:
                monitor = self.monitors[self.monitor_index]
                screenshot = sct.grab(monitor)
            
            # Convert to PIL Image
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            return img
            
        except Exception as e:
            print(f"MSS capture failed: {e}")
            return None
    
    def _capture_with_pil(self, region=None):
        """
        Capture screenshot using PIL ImageGrab as fallback.
        
        Args:
            region: Optional region tuple (left, top, right, bottom) for partial capture
            
        Returns:
            PIL.Image: Captured image or None if failed
        """
        try:
            if region:
                # Convert region dict to PIL format (left, top, right, bottom)
                if isinstance(region, dict):
                    bbox = (region['left'], region['top'], 
                           region['left'] + region['width'], 
                           region['top'] + region['height'])
                else:
                    bbox = region
                img = ImageGrab.grab(bbox=bbox)
            else:
                img = ImageGrab.grab()
            
            return img
            
        except Exception as e:
            print(f"PIL ImageGrab capture failed: {e}")
            return None
    
    def capture_and_ocr(self) -> Optional[str]:
        """
        Capture a screenshot and extract text using OCR with fallback mechanisms.
        
        Returns:
            str: Extracted text from the screen, or None if error occurs
        """
        try:
            # Try MSS first, then fallback to PIL
            img = self._capture_with_mss()
            if img is None:
                print("MSS failed, trying PIL ImageGrab fallback...")
                img = self._capture_with_pil()
            
            if img is None:
                print("All capture methods failed")
                return None
            
            # Perform OCR
            text = pytesseract.image_to_string(img, lang=self.ocr_language)
            
            # Clean up the text
            text = self._clean_text(text)
            
            print(f"Extracted {len(text)} characters from screen")
            return text
            
        except Exception as e:
            print(f"Error capturing screen or performing OCR: {e}")
            return None
    
    def capture_region_and_ocr(self, x: int, y: int, width: int, height: int) -> Optional[str]:
        """
        Capture a specific region of the screen and extract text using OCR.
        
        Args:
            x: X coordinate of the region
            y: Y coordinate of the region
            width: Width of the region
            height: Height of the region
            
        Returns:
            str: Extracted text from the region, or None if error occurs
        """
        try:
            # Define the region for MSS (dict format)
            mss_region = {"top": y, "left": x, "width": width, "height": height}
            
            # Try MSS first
            img = self._capture_with_mss(mss_region)
            
            if img is None:
                print("MSS region capture failed, trying PIL ImageGrab fallback...")
                # Define region for PIL (tuple format: left, top, right, bottom)
                pil_region = (x, y, x + width, y + height)
                img = self._capture_with_pil(pil_region)
            
            if img is None:
                print("All region capture methods failed")
                return None
            
            # Perform OCR
            text = pytesseract.image_to_string(img, lang=self.ocr_language)
            
            # Clean up the text
            text = self._clean_text(text)
            
            print(f"Extracted {len(text)} characters from region ({x},{y},{width},{height})")
            return text
            
        except Exception as e:
            print(f"Error capturing region or performing OCR: {e}")
            return None
    
    def save_screenshot(self, filename: str) -> bool:
        """
        Save a screenshot to a file with fallback mechanisms.
        
        Args:
            filename: Path to save the screenshot
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Try MSS first, then fallback to PIL
            img = self._capture_with_mss()
            if img is None:
                print("MSS failed for screenshot save, trying PIL ImageGrab...")
                img = self._capture_with_pil()
            
            if img is None:
                print("All capture methods failed for screenshot save")
                return False
            
            # Save the image
            img.save(filename)
            print(f"Screenshot saved to {filename}")
            return True
            
        except Exception as e:
            print(f"Error saving screenshot: {e}")
            return False
    
    def _clean_text(self, text: str) -> str:
        """
        Clean up extracted text by removing extra whitespace and formatting.
        
        Args:
            text: Raw text from OCR
            
        Returns:
            str: Cleaned text
        """
        if not text:
            return ""
        
        # Remove extra whitespace and normalize line breaks
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        cleaned_text = ' '.join(lines)
        
        # Remove excessive spaces
        while '  ' in cleaned_text:
            cleaned_text = cleaned_text.replace('  ', ' ')
        
        return cleaned_text.strip()
    
    def __del__(self):
        """Clean up resources when the scanner is destroyed."""
        try:
            if hasattr(self, '_primary_sct'):
                self._primary_sct.close()
            if hasattr(self._thread_local, 'sct'):
                self._thread_local.sct.close()
        except:
            pass  # Ignore cleanup errors 