"""
Screen Scanner Module
Provides on-demand screen capture and OCR functionality.
"""

import mss
from PIL import Image
import logging
from typing import Dict, Any, Optional, Tuple
import io
import subprocess
import sys

class ScreenScanner:
    """
    Handles screen capture and optical character recognition (OCR) functionality.
    Operates on-demand when requested by other components.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize screenshot interface
        self.sct = mss.mss()
        
        # Check if tesseract is available
        self.tesseract_available = self._check_tesseract_installation()
        
        self.logger.info(f"ScreenScanner initialized - Tesseract available: {self.tesseract_available}")
        
    def _check_tesseract_installation(self) -> bool:
        """
        Check if tesseract is installed and accessible.
        
        Returns:
            True if tesseract is available, False otherwise
        """
        try:
            # Try to import pytesseract
            import pytesseract
            
            # Try to run tesseract command
            result = subprocess.run(['tesseract', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                version_info = result.stdout.split('\n')[0]
                self.logger.info(f"Tesseract found: {version_info}")
                return True
            else:
                self.logger.warning("Tesseract command failed")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.warning("Tesseract command timed out")
            return False
        except FileNotFoundError:
            self.logger.warning("Tesseract executable not found in PATH")
            return False
        except ImportError:
            self.logger.warning("pytesseract module not available")
            return False
        except Exception as e:
            self.logger.warning(f"Error checking tesseract: {e}")
            return False
            
    def capture_full_screen(self) -> Optional[Image.Image]:
        """
        Capture the entire screen.
        
        Returns:
            PIL Image object of the screen capture, or None if failed
        """
        try:
            # Get all monitors and capture the primary one
            monitors = self.sct.monitors
            primary_monitor = monitors[1] if len(monitors) > 1 else monitors[0]
            
            # Capture screenshot
            screenshot = self.sct.grab(primary_monitor)
            
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
            # Define the region to capture
            region = {
                "top": y,
                "left": x,
                "width": width,
                "height": height
            }
            
            # Capture the region
            screenshot = self.sct.grab(region)
            
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
            monitors = self.sct.monitors
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
            return len(self.sct.monitors) - 1  # Subtract 1 to exclude the "all monitors" entry
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