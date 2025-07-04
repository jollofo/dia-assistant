"""
Screen Scanner Module
Provides on-demand screen capture and OCR functionality with intelligent change detection.
Enhanced with visual analysis, layout detection, and LLaVA vision model integration.
"""

import mss
from PIL import Image, ImageChops, ImageEnhance, ImageFilter
import logging
from typing import Dict, Any, Optional, Tuple, Callable, Set, List
import io
import subprocess
import sys
import os
import threading
import time
import hashlib
import difflib
import re
from collections import deque
import numpy as np
import cv2
import base64
import requests
import json

class ScreenScanner:
    """
    Handles screen capture and optical character recognition (OCR) functionality.
    Supports both on-demand scanning and continuous monitoring with intelligent change detection.
    Enhanced with visual analysis, layout detection, and LLaVA vision model integration.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize mss for screen capture
        self.sct = mss.mss()
        
        # Check for Tesseract availability
        self.tesseract_available = self._check_tesseract_availability()
        
        # Vision model configuration
        self.vision_config = config.get('vision', {})
        self.vision_enabled = self.vision_config.get('enabled', False)
        self.vision_model = self.vision_config.get('model', 'llava:v1.6')
        self.ollama_base_url = config.get('ollama', {}).get('base_url', 'http://localhost:11434')
        self.vision_timeout = config.get('ollama', {}).get('vision_timeout', 25)
        
        # Change detection variables
        self._last_screenshot_hash = None
        self._last_ocr_text = ""
        self._last_text_length = 0
        self._change_history = deque(maxlen=10)
        
        if not self.tesseract_available:
            self.logger.warning("Tesseract OCR not available. Text extraction will be limited.")
        
        if self.vision_enabled:
            self.logger.info(f"Vision analysis enabled with model: {self.vision_model}")
        else:
            self.logger.info("Vision analysis disabled - using OCR only")
        
        # Thread-local storage for mss instances
        self._thread_local = threading.local()
        
        # Configure Tesseract path explicitly
        self._configure_tesseract_path()
        
        # Check if OpenCV is available for enhanced visual analysis
        self.opencv_available = self._check_opencv_availability()
        
        # Continuous monitoring state
        self._monitoring_active = False
        self._monitoring_thread = None
        self._stop_monitoring = threading.Event()
        self._last_screen_hash = None
        self._last_screen_text = ""
        self._last_visual_hash = None
        self._change_callback = None
        
        # Advanced monitoring configuration
        monitor_config = config.get('screen_monitoring', {})
        self._monitor_interval = monitor_config.get('interval_seconds', 3)
        self._min_change_chars = monitor_config.get('min_change_chars', 50)
        self._similarity_threshold = monitor_config.get('similarity_threshold', 0.85)
        self._visual_change_threshold = monitor_config.get('visual_change_threshold', 0.15)
        self._major_change_threshold = monitor_config.get('major_change_threshold', 0.4)
        self._confidence_threshold = monitor_config.get('confidence_threshold', 0.5)
        
        # Change detection history for better analysis
        self._text_history = deque(maxlen=5)
        self._visual_history = deque(maxlen=5)
        self._change_timestamps = deque(maxlen=10)
        
        # Enhanced visual analysis cache
        self._ui_elements_cache = {}
        self._layout_cache = {}
        
        # Noise filtering patterns
        self._noise_patterns = [
            r'\d{2}:\d{2}:\d{2}',  # Timestamps
            r'\d{1,2}:\d{2}\s?(AM|PM)',  # Clock times
            r'(\d+)\s?%',  # Percentages (progress bars)
            r'(\d+)/(\d+)',  # Counts (page numbers, etc.)
            r'[|\\/-]',  # Loading animation characters
            r'●○◐◑◒◓',  # Loading dots
            r'Typing\.\.\.',  # Typing indicators
            r'Online|Offline|Away|Busy',  # Status indicators
        ]
        
        self.logger.info(f"ScreenScanner initialized with enhanced visual analysis - Tesseract: {self.tesseract_available}, OpenCV: {self.opencv_available}")
        
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
        
    def _check_tesseract_availability(self) -> bool:
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
            
    def _check_opencv_availability(self) -> bool:
        """Check if OpenCV is available for enhanced visual analysis."""
        try:
            import cv2
            self.logger.info(f"OpenCV available: {cv2.__version__}")
            return True
        except ImportError:
            self.logger.warning("OpenCV not available - enhanced visual analysis will be limited")
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
            
            # Preprocess image for better OCR accuracy
            processed_image = self._preprocess_image_for_ocr(image)
            
            # Perform OCR on the processed image
            text = pytesseract.image_to_string(processed_image, lang='eng')
            
            # Clean up the extracted text
            text = text.strip()
            
            self.logger.debug(f"OCR extracted {len(text)} characters")
            return text if text else "No text detected in image"
            
        except Exception as e:
            error_msg = f"Failed to extract text from image: {e}"
            self.logger.error(error_msg)
            return f"OCR_ERROR: {error_msg}"
    
    def _preprocess_image_for_ocr(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image to improve OCR accuracy.
        
        Args:
            image: Original PIL Image
            
        Returns:
            Preprocessed PIL Image
        """
        try:
            # Convert to grayscale for better OCR
            if image.mode != 'L':
                processed = image.convert('L')
            else:
                processed = image.copy()
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(processed)
            processed = enhancer.enhance(1.5)
            
            # Enhance sharpness
            enhancer = ImageEnhance.Sharpness(processed)
            processed = enhancer.enhance(1.2)
            
            # Apply slight noise reduction
            processed = processed.filter(ImageFilter.MedianFilter(size=3))
            
            # Scale up for better OCR (if image is small)
            width, height = processed.size
            if width < 1000 or height < 1000:
                scale_factor = max(1000 / width, 1000 / height, 1.5)
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                processed = processed.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            return processed
            
        except Exception as e:
            self.logger.warning(f"Image preprocessing failed, using original: {e}")
            return image
    
    def analyze_visual_elements(self, image: Image.Image) -> Dict[str, Any]:
        """
        Analyze visual elements in the screen capture.
        
        Args:
            image: PIL Image to analyze
            
        Returns:
            Dictionary containing visual analysis results
        """
        analysis = {
            'ui_elements': [],
            'layout_regions': [],
            'color_scheme': {},
            'text_regions': [],
            'interactive_elements': [],
            'dominant_colors': [],
            'has_dark_theme': False
        }
        
        try:
            # Basic color analysis without OpenCV
            analysis['color_scheme'] = self._analyze_color_scheme(image)
            analysis['has_dark_theme'] = self._detect_dark_theme(image)
            
            if self.opencv_available:
                # Enhanced analysis with OpenCV
                analysis.update(self._analyze_with_opencv(image))
            else:
                # Fallback analysis without OpenCV
                analysis.update(self._analyze_without_opencv(image))
                
        except Exception as e:
            self.logger.warning(f"Visual analysis failed: {e}")
            
        return analysis
    
    def _analyze_color_scheme(self, image: Image.Image) -> Dict[str, Any]:
        """Analyze the color scheme of the image."""
        try:
            # Get dominant colors
            colors = image.getcolors(maxcolors=256*256*256)
            if colors:
                # Sort by frequency
                colors.sort(key=lambda x: x[0], reverse=True)
                dominant_colors = [color[1] for color in colors[:5]]
                
                return {
                    'dominant_colors': dominant_colors,
                    'total_colors': len(colors),
                    'most_common': colors[0][1] if colors else None
                }
        except Exception as e:
            self.logger.debug(f"Color analysis failed: {e}")
            
        return {}
    
    def _detect_dark_theme(self, image: Image.Image) -> bool:
        """Detect if the image uses a dark theme."""
        try:
            # Convert to grayscale and calculate average brightness
            gray = image.convert('L')
            histogram = gray.histogram()
            
            # Calculate weighted average (dark pixels have more weight)
            total_pixels = sum(histogram)
            weighted_sum = sum(i * count for i, count in enumerate(histogram))
            average_brightness = weighted_sum / total_pixels
            
            # Dark theme if average brightness is below threshold
            return average_brightness < 85
            
        except Exception:
            return False
    
    def _analyze_with_opencv(self, image: Image.Image) -> Dict[str, Any]:
        """Enhanced visual analysis using OpenCV."""
        try:
            import cv2
            
            # Convert PIL to OpenCV format
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            analysis = {}
            
            # Detect edges for UI element boundaries
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filter contours to find potential UI elements
            ui_elements = []
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 100:  # Filter small noise
                    x, y, w, h = cv2.boundingRect(contour)
                    aspect_ratio = w / h if h > 0 else 0
                    
                    # Classify potential UI elements
                    element_type = self._classify_ui_element(w, h, aspect_ratio, area)
                    if element_type:
                        ui_elements.append({
                            'type': element_type,
                            'bounds': (x, y, w, h),
                            'area': area,
                            'aspect_ratio': aspect_ratio
                        })
            
            analysis['ui_elements'] = ui_elements
            
            # Detect text regions using MSER (Maximally Stable Extremal Regions)
            mser = cv2.MSER_create()
            regions, _ = mser.detectRegions(gray)
            
            text_regions = []
            for region in regions:
                if len(region) > 10:  # Filter small regions
                    x, y, w, h = cv2.boundingRect(region)
                    text_regions.append({
                        'bounds': (x, y, w, h),
                        'points': len(region)
                    })
            
            analysis['text_regions'] = text_regions
            
            # Detect horizontal and vertical lines (for layout analysis)
            horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
            vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))
            
            horizontal_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel)
            vertical_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, vertical_kernel)
            
            analysis['layout_lines'] = {
                'horizontal_detected': np.sum(horizontal_lines > 0),
                'vertical_detected': np.sum(vertical_lines > 0)
            }
            
            return analysis
            
        except Exception as e:
            self.logger.warning(f"OpenCV analysis failed: {e}")
            return {}
    
    def _analyze_without_opencv(self, image: Image.Image) -> Dict[str, Any]:
        """Fallback visual analysis without OpenCV."""
        try:
            width, height = image.size
            
            # Basic layout detection using PIL
            gray = image.convert('L')
            
            # Sample pixels to detect patterns
            sample_step = max(1, min(width, height) // 50)
            
            # Detect potential horizontal lines by checking pixel consistency
            horizontal_lines = 0
            for y in range(0, height, sample_step):
                row_pixels = [gray.getpixel((x, y)) for x in range(0, width, sample_step)]
                if len(set(row_pixels)) < len(row_pixels) * 0.3:  # Low variation suggests a line
                    horizontal_lines += 1
            
            # Detect potential vertical lines
            vertical_lines = 0
            for x in range(0, width, sample_step):
                col_pixels = [gray.getpixel((x, y)) for y in range(0, height, sample_step)]
                if len(set(col_pixels)) < len(col_pixels) * 0.3:
                    vertical_lines += 1
            
            return {
                'layout_lines': {
                    'horizontal_detected': horizontal_lines,
                    'vertical_detected': vertical_lines
                },
                'ui_elements': [],  # Limited without OpenCV
                'text_regions': []
            }
            
        except Exception as e:
            self.logger.warning(f"Fallback analysis failed: {e}")
            return {}
    
    def _classify_ui_element(self, width: int, height: int, aspect_ratio: float, area: int) -> Optional[str]:
        """Classify UI elements based on dimensions and aspect ratio."""
        # Button-like elements (roughly square or rectangular)
        if 20 <= width <= 200 and 15 <= height <= 60 and 0.3 <= aspect_ratio <= 8:
            return 'button'
        
        # Input field-like elements (wide and short)
        elif width > 100 and 20 <= height <= 50 and aspect_ratio > 3:
            return 'input_field'
        
        # Text block-like elements (medium width, variable height)
        elif width > 50 and height > 30 and 1 <= aspect_ratio <= 10:
            return 'text_block'
        
        # Window/panel-like elements (large rectangular areas)
        elif width > 200 and height > 100 and area > 20000:
            return 'panel'
        
        # Icon-like elements (small and roughly square)
        elif 10 <= width <= 50 and 10 <= height <= 50 and 0.5 <= aspect_ratio <= 2:
            return 'icon'
        
        return None
            
    def capture_and_extract_text(self) -> Optional[str]:
        """
        Convenience method to capture the full screen and extract text.
        
        Returns:
            Extracted text from the full screen, or error message if failed
        """
        try:
            # Capture the full screen
            image = self.capture_full_screen()
            if not image:
                return "Failed to capture screen"
                
            # Extract text using enhanced OCR
            text = self.extract_text_from_image(image)
            return text
            
        except Exception as e:
            error_msg = f"Screen capture and text extraction failed: {e}"
            self.logger.error(error_msg)
            return f"OCR_ERROR: {error_msg}"
    
    def get_comprehensive_screen_context(self) -> Dict[str, Any]:
        """
        Get comprehensive screen analysis including OCR text and visual elements.
        
        Returns:
            Dictionary containing:
            - ocr_text: Text extracted via OCR
            - visual_analysis: Visual elements and layout analysis
            - summary: Human-readable summary of screen content
            - confidence: Confidence score of the analysis
        """
        try:
            # Capture the screen
            image = self.capture_full_screen()
            if not image:
                return {
                    'ocr_text': "Failed to capture screen",
                    'visual_analysis': {},
                    'summary': "Screen capture failed",
                    'confidence': 0.0,
                    'timestamp': time.time()
                }
            
            # Extract text via OCR
            ocr_text = self.extract_text_from_image(image)
            
            # Analyze visual elements
            visual_analysis = self.analyze_visual_elements(image)
            
            # Generate comprehensive summary
            summary = self._generate_comprehensive_summary(ocr_text, visual_analysis)
            
            # Calculate confidence score
            confidence = self._calculate_analysis_confidence(ocr_text, visual_analysis)
            
            return {
                'ocr_text': ocr_text,
                'visual_analysis': visual_analysis,
                'summary': summary,
                'confidence': confidence,
                'timestamp': time.time(),
                'image_size': image.size,
                'has_opencv': self.opencv_available
            }
            
        except Exception as e:
            error_msg = f"Comprehensive screen analysis failed: {e}"
            self.logger.error(error_msg)
            return {
                'ocr_text': f"ERROR: {error_msg}",
                'visual_analysis': {},
                'summary': f"Analysis failed: {str(e)}",
                'confidence': 0.0,
                'timestamp': time.time()
            }
    
    def _generate_comprehensive_summary(self, ocr_text: str, visual_analysis: Dict[str, Any]) -> str:
        """
        Generate a human-readable summary combining OCR and visual analysis.
        
        Args:
            ocr_text: Text extracted from OCR
            visual_analysis: Visual analysis results
            
        Returns:
            Comprehensive summary string
        """
        try:
            summary_parts = []
            
            # Add OCR text information
            if ocr_text and not ocr_text.startswith("OCR_ERROR:") and len(ocr_text.strip()) > 10:
                # Clean and summarize text
                cleaned_text = self._clean_text_for_comparison(ocr_text)
                if len(cleaned_text) > 200:
                    text_preview = cleaned_text[:200] + "..."
                else:
                    text_preview = cleaned_text
                summary_parts.append(f"Text content: {text_preview}")
            
            # Add visual elements information
            ui_elements = visual_analysis.get('ui_elements', [])
            if ui_elements:
                element_counts = {}
                for element in ui_elements:
                    element_type = element.get('type', 'unknown')
                    element_counts[element_type] = element_counts.get(element_type, 0) + 1
                
                element_summary = []
                for element_type, count in element_counts.items():
                    element_summary.append(f"{count} {element_type}{'s' if count > 1 else ''}")
                
                if element_summary:
                    summary_parts.append(f"UI elements detected: {', '.join(element_summary)}")
            
            # Add layout information
            layout_info = visual_analysis.get('layout_lines', {})
            if layout_info:
                layout_desc = []
                if layout_info.get('horizontal_detected', 0) > 10:
                    layout_desc.append("structured horizontal layout")
                if layout_info.get('vertical_detected', 0) > 10:
                    layout_desc.append("structured vertical layout")
                
                if layout_desc:
                    summary_parts.append(f"Layout: {', '.join(layout_desc)}")
            
            # Add theme information
            if visual_analysis.get('has_dark_theme'):
                summary_parts.append("Dark theme interface")
            else:
                summary_parts.append("Light theme interface")
            
            # Add color information
            color_info = visual_analysis.get('color_scheme', {})
            if color_info.get('total_colors'):
                summary_parts.append(f"Color complexity: {color_info['total_colors']} distinct colors")
            
            # Add text regions information
            text_regions = visual_analysis.get('text_regions', [])
            if len(text_regions) > 5:
                summary_parts.append(f"Multiple text areas detected ({len(text_regions)} regions)")
            
            # Combine all parts
            if summary_parts:
                return ". ".join(summary_parts) + "."
            else:
                return "Screen content detected but analysis inconclusive."
                
        except Exception as e:
            self.logger.warning(f"Summary generation failed: {e}")
            return f"Screen analysis completed with limited results: {str(e)}"
    
    def _calculate_analysis_confidence(self, ocr_text: str, visual_analysis: Dict[str, Any]) -> float:
        """
        Calculate confidence score for the analysis.
        
        Args:
            ocr_text: OCR extracted text
            visual_analysis: Visual analysis results
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        try:
            confidence_factors = []
            
            # OCR text confidence
            if ocr_text and not ocr_text.startswith("OCR_ERROR:"):
                text_length = len(ocr_text.strip())
                if text_length > 100:
                    confidence_factors.append(0.9)
                elif text_length > 50:
                    confidence_factors.append(0.7)
                elif text_length > 20:
                    confidence_factors.append(0.5)
                else:
                    confidence_factors.append(0.3)
            else:
                confidence_factors.append(0.1)
            
            # Visual analysis confidence
            ui_elements = visual_analysis.get('ui_elements', [])
            if len(ui_elements) > 5:
                confidence_factors.append(0.8)
            elif len(ui_elements) > 2:
                confidence_factors.append(0.6)
            elif len(ui_elements) > 0:
                confidence_factors.append(0.4)
            else:
                confidence_factors.append(0.2)
            
            # Layout structure confidence
            layout_info = visual_analysis.get('layout_lines', {})
            total_layout_elements = layout_info.get('horizontal_detected', 0) + layout_info.get('vertical_detected', 0)
            if total_layout_elements > 20:
                confidence_factors.append(0.7)
            elif total_layout_elements > 10:
                confidence_factors.append(0.5)
            else:
                confidence_factors.append(0.3)
            
            # OpenCV availability bonus
            if self.opencv_available:
                confidence_factors.append(0.1)  # Small bonus
            
            # Calculate weighted average
            if confidence_factors:
                return min(1.0, sum(confidence_factors) / len(confidence_factors) + 0.1)
            else:
                return 0.1
                
        except Exception:
            return 0.5  # Default moderate confidence
            
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
        """Background thread that monitors for screen changes with intelligent detection."""
        consecutive_errors = 0
        max_consecutive_errors = 5
        last_major_change = 0
        
        while self._monitoring_active and not self._stop_monitoring.is_set():
            try:
                # Capture current screen
                current_image = self.capture_full_screen()
                current_text = None
                
                if current_image:
                    # Calculate visual hash for quick comparison
                    visual_hash = self._calculate_visual_hash(current_image)
                    
                    # Check for visual changes first (faster than OCR)
                    if self._has_significant_visual_change(visual_hash):
                        # Only do OCR if visual changes are detected
                        current_text = self.extract_text_from_image(current_image)
                        
                        if current_text and not current_text.startswith("OCR_ERROR:"):
                            # Reset error counter on success
                            consecutive_errors = 0
                            
                            # Perform comprehensive change analysis
                            change_analysis = self._analyze_screen_change(current_text, visual_hash)
                            
                            if change_analysis['is_significant']:
                                current_time = time.time()
                                
                                # Prevent spam by enforcing minimum time between major changes
                                time_since_last = current_time - last_major_change
                                min_interval = 5  # Minimum 5 seconds between major change notifications
                                
                                # Only notify if confidence is high enough (0.5 or higher)
                                if change_analysis['confidence'] >= self._confidence_threshold and (change_analysis['is_major'] or time_since_last >= min_interval):
                                    self.logger.info(f"Significant screen change detected: {change_analysis['type']}")
                                    
                                    # Update baseline
                                    self._update_baseline_screen_data(current_text, visual_hash)
                                    
                                    # Record change timestamp
                                    self._change_timestamps.append(current_time)
                                    last_major_change = current_time
                                    
                                    # Notify callback with enhanced context
                                    if self._change_callback:
                                        try:
                                            enriched_content = self._enrich_screen_content(current_text, change_analysis)
                                            self._change_callback(enriched_content)
                                        except Exception as e:
                                            self.logger.error(f"Error in change callback: {e}")
                                else:
                                    self.logger.debug(f"Change detected but confidence too low: {change_analysis['confidence']:.2f} < {self._confidence_threshold}")
                            else:
                                self.logger.debug(f"Screen change not significant: {change_analysis['type']}")
                    else:
                        self.logger.debug("No significant visual changes detected")
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
                
    def _calculate_visual_hash(self, image: Image.Image) -> str:
        """Calculate a perceptual hash for visual comparison."""
        try:
            # Resize to small size for faster processing
            small_image = image.resize((32, 32), Image.Resampling.LANCZOS)
            
            # Convert to grayscale
            gray_image = small_image.convert('L')
            
            # Calculate average pixel value
            pixels = list(gray_image.getdata())
            avg_pixel = sum(pixels) / len(pixels)
            
            # Create hash based on pixels above/below average
            hash_bits = []
            for pixel in pixels:
                hash_bits.append('1' if pixel >= avg_pixel else '0')
            
            # Convert to hex string
            hash_str = ''.join(hash_bits)
            return hashlib.md5(hash_str.encode()).hexdigest()[:16]
            
        except Exception as e:
            self.logger.error(f"Error calculating visual hash: {e}")
            return ""
            
    def _has_significant_visual_change(self, current_visual_hash: str) -> bool:
        """Check if visual changes are significant enough to warrant OCR."""
        if not self._last_visual_hash or not current_visual_hash:
            return True
            
        # Compare visual hashes
        if current_visual_hash == self._last_visual_hash:
            return False
            
        # Calculate hamming distance for perceptual comparison
        if len(current_visual_hash) == len(self._last_visual_hash):
            hamming_distance = sum(c1 != c2 for c1, c2 in zip(current_visual_hash, self._last_visual_hash))
            similarity = 1 - (hamming_distance / len(current_visual_hash))
            
            # Store in history for trend analysis
            self._visual_history.append(similarity)
            
            # Consider change significant if similarity is below threshold
            return similarity < (1 - self._visual_change_threshold)
        
        return True
        
    def _analyze_screen_change(self, current_text: str, visual_hash: str) -> Dict[str, Any]:
        """Perform comprehensive analysis of screen changes."""
        if not self._last_screen_text or not current_text:
            return {
                'is_significant': True,
                'is_major': True,
                'type': 'initial_capture',
                'confidence': 1.0,
                'details': 'First screen capture'
            }
            
        # Clean and normalize text for comparison
        clean_current = self._clean_text_for_comparison(current_text)
        clean_last = self._clean_text_for_comparison(self._last_screen_text)
        
        # Calculate various similarity metrics
        text_similarity = self._calculate_text_similarity(clean_current, clean_last)
        structure_similarity = self._calculate_structure_similarity(current_text, self._last_screen_text)
        semantic_changes = self._detect_semantic_changes(current_text, self._last_screen_text)
        
        # Store in history
        self._text_history.append(text_similarity)
        
        # Determine change significance
        analysis = {
            'text_similarity': text_similarity,
            'structure_similarity': structure_similarity,
            'semantic_changes': semantic_changes,
            'is_significant': False,
            'is_major': False,
            'type': 'minor_change',
            'confidence': 0.0,
            'details': ''
        }
        
        # Major change indicators
        if text_similarity < 0.3:
            analysis.update({
                'is_significant': True,
                'is_major': True,
                'type': 'major_content_change',
                'confidence': 1 - text_similarity,
                'details': 'Significant content difference detected'
            })
        elif structure_similarity < 0.4:
            analysis.update({
                'is_significant': True,
                'is_major': True,
                'type': 'layout_change',
                'confidence': 1 - structure_similarity,
                'details': 'Page layout or structure changed'
            })
        elif semantic_changes['has_major_changes']:
            analysis.update({
                'is_significant': True,
                'is_major': True,
                'type': 'semantic_change',
                'confidence': semantic_changes['confidence'],
                'details': f"Semantic changes: {', '.join(semantic_changes['changes'])}"
            })
        # Moderate changes
        elif text_similarity < self._similarity_threshold:
            analysis.update({
                'is_significant': True,
                'is_major': False,
                'type': 'content_update',
                'confidence': (self._similarity_threshold - text_similarity) / self._similarity_threshold,
                'details': 'Moderate content changes detected'
            })
        
        return analysis
        
    def _clean_text_for_comparison(self, text: str) -> str:
        """Remove noise and normalize text for better comparison."""
        if not text:
            return ""
            
        cleaned = text
        
        # Remove common UI noise patterns
        for pattern in self._noise_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Normalize whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Remove very short isolated words (often OCR noise)
        words = cleaned.split()
        filtered_words = [word for word in words if len(word) > 2 or word.isalnum()]
        
        return ' '.join(filtered_words).strip().lower()
        
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings using multiple methods."""
        if not text1 or not text2:
            return 0.0
            
        # Use SequenceMatcher for similarity
        similarity = difflib.SequenceMatcher(None, text1, text2).ratio()
        
        # Also check for common subsequences
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if words1 and words2:
            word_similarity = len(words1 & words2) / len(words1 | words2)
            # Combine both metrics
            similarity = (similarity * 0.7) + (word_similarity * 0.3)
            
        return similarity
        
    def _calculate_structure_similarity(self, text1: str, text2: str) -> float:
        """Calculate structural similarity (line breaks, formatting, etc.)."""
        if not text1 or not text2:
            return 0.0
            
        lines1 = text1.split('\n')
        lines2 = text2.split('\n')
        
        # Compare line count similarity
        line_count_similarity = 1 - abs(len(lines1) - len(lines2)) / max(len(lines1), len(lines2), 1)
        
        # Compare line length patterns
        lens1 = [len(line) for line in lines1]
        lens2 = [len(line) for line in lines2]
        
        if lens1 and lens2:
            # Use sequence matcher on line lengths to detect structural changes
            structure_similarity = difflib.SequenceMatcher(None, lens1, lens2).ratio()
        else:
            structure_similarity = line_count_similarity
            
        return (line_count_similarity * 0.3) + (structure_similarity * 0.7)
        
    def _detect_semantic_changes(self, current_text: str, last_text: str) -> Dict[str, Any]:
        """Detect semantic changes that indicate important events."""
        changes = []
        confidence = 0.0
        
        # Common indicators of significant changes
        indicators = {
            'new_page': [r'Loading', r'Welcome to', r'Sign in', r'Login', r'Home', r'Dashboard'],
            'navigation': [r'Back to', r'Go to', r'Navigate to', r'Switch to'],
            'errors': [r'Error', r'Failed', r'Unable to', r'Not found', r'Access denied'],
            'completion': [r'Complete', r'Finished', r'Success', r'Done', r'Saved'],
            'forms': [r'Submit', r'Enter', r'Required', r'Please fill', r'Form'],
        }
        
        current_lower = current_text.lower()
        last_lower = last_text.lower()
        
        for change_type, patterns in indicators.items():
            current_matches = sum(1 for pattern in patterns if re.search(pattern, current_lower))
            last_matches = sum(1 for pattern in patterns if re.search(pattern, last_lower))
            
            if current_matches > last_matches:
                changes.append(f"new_{change_type}")
                confidence += 0.2
            elif current_matches < last_matches and last_matches > 0:
                changes.append(f"lost_{change_type}")
                confidence += 0.1
                
        # Check for URL/title changes (often indicate navigation)
        if self._detect_url_or_title_change(current_text, last_text):
            changes.append("navigation_change")
            confidence += 0.3
            
        return {
            'has_major_changes': confidence > 0.3,
            'changes': changes,
            'confidence': min(confidence, 1.0)
        }
        
    def _detect_url_or_title_change(self, current_text: str, last_text: str) -> bool:
        """Detect if URL or page title has changed."""
        # Look for common title patterns
        title_patterns = [
            r'<title>(.*?)</title>',
            r'document\.title\s*=\s*["\']([^"\']*)["\']',
            r'[A-Z][^a-z]*[A-Z].*?(?:\||—|-).*?[A-Z]',  # Title-like patterns
        ]
        
        url_patterns = [
            r'https?://[^\s]+',
            r'www\.[^\s]+',
            r'[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        ]
        
        for pattern in title_patterns + url_patterns:
            current_matches = set(re.findall(pattern, current_text, re.IGNORECASE))
            last_matches = set(re.findall(pattern, last_text, re.IGNORECASE))
            
            if current_matches != last_matches:
                return True
                
        return False
        
    def _update_baseline_screen_data(self, text: str, visual_hash: str):
        """Update baseline screen content and visual hash."""
        try:
            self._last_screen_text = text
            self._last_screen_hash = hashlib.md5(text.encode()).hexdigest()
            self._last_visual_hash = visual_hash
            self.logger.debug("Updated baseline screen data")
        except Exception as e:
            self.logger.error(f"Error updating baseline screen: {e}")
            
    def _enrich_screen_content(self, content: str, analysis: Dict[str, Any]) -> str:
        """Format screen content with proper structure and clean formatting."""
        if not content:
            return "No readable content detected on screen."
        
        # Clean and format the content
        formatted_content = self._format_screen_content(content)
        
        return formatted_content
        
    def _format_screen_content(self, content: str) -> str:
        """Format raw screen content into well-structured text."""
        if not content:
            return ""
        
        # Remove asterisks and other formatting characters, but preserve structure
        cleaned = content.replace('#', '')
        
        # Split into lines for processing
        lines = [line.strip() for line in cleaned.split('\n') if line.strip()]
        
        if not lines:
            return "No readable content found."
        
        formatted_lines = []
        current_section = []
        
        for line in lines:
            # Skip very short lines (likely noise)
            if len(line) < 3:
                continue
                
            # Detect headings (lines that are short and likely titles)
            if self._is_likely_heading(line):
                # If we have accumulated content, add it as a paragraph
                if current_section:
                    paragraph = ' '.join(current_section)
                    if len(paragraph) > 10:  # Only add substantial paragraphs
                        formatted_lines.append(self._format_paragraph(paragraph))
                    current_section = []
                
                # Add the heading
                formatted_lines.append(f"\n## {line.title()}")
                
            # Detect list items (including asterisk items)
            elif self._is_list_item(line):
                # Flush current section as paragraph first
                if current_section:
                    paragraph = ' '.join(current_section)
                    if len(paragraph) > 10:
                        formatted_lines.append(self._format_paragraph(paragraph))
                    current_section = []
                
                # Add list item
                clean_item = self._clean_list_item(line)
                if clean_item:
                    formatted_lines.append(f"• {clean_item}")
                    
            # Regular content lines
            else:
                current_section.append(line)
        
        # Add any remaining content as final paragraph
        if current_section:
            paragraph = ' '.join(current_section)
            if len(paragraph) > 10:
                formatted_lines.append(self._format_paragraph(paragraph))
        
        # Join and clean up the result
        result = '\n'.join(formatted_lines)
        
        # Clean up excessive whitespace
        result = re.sub(r'\n{3,}', '\n\n', result)
        result = re.sub(r' {2,}', ' ', result)
        
        return result.strip()
        
    def _is_likely_heading(self, line: str) -> bool:
        """Determine if a line is likely a heading."""
        if not line:
            return False
            
        # Check length (headings are usually shorter)
        if len(line) > 60:
            return False
            
        # Check for heading indicators
        heading_indicators = [
            line.isupper(),  # ALL CAPS
            len(line.split()) <= 6,  # Short phrases (increased from 5)
            line.endswith(':'),  # Ends with colon
            any(word in line.lower() for word in ['menu', 'navigation', 'header', 'title', 'section', 'page', 'home', 'contact', 'about'])
        ]
        
        # Must meet at least 2 criteria
        return sum(heading_indicators) >= 2
        
    def _is_list_item(self, line: str) -> bool:
        """Determine if a line is a list item."""
        if not line:
            return False
            
        # Common list item patterns
        list_patterns = [
            r'^\d+[\.\)]\s',     # 1. or 1)
            r'^[-•·]\s',         # - or • or ·
            r'^\*\s',            # * (asterisk)
            r'^\w+:\s',          # Label:
            r'^→\s',             # Arrow
            r'^[A-Z]{1,3}:\s',   # Short labels like "ID:", "URL:"
            r'^\*\s*\w+\s*\d+:', # * Feature 1:
        ]
        
        return any(re.match(pattern, line) for pattern in list_patterns)
        
    def _clean_list_item(self, line: str) -> str:
        """Clean up list item formatting."""
        # Remove common list prefixes
        cleaned = re.sub(r'^(\d+[\.\)]|[-•·]|→|\*)\s*', '', line)
        cleaned = cleaned.strip()
        
        # Remove underscores
        cleaned = cleaned.replace('_', '')
        
        # Capitalize first letter
        if cleaned:
            cleaned = cleaned[0].upper() + cleaned[1:] if len(cleaned) > 1 else cleaned.upper()
            
        return cleaned
        
    def _format_paragraph(self, text: str) -> str:
        """Format text as a proper paragraph."""
        if not text:
            return ""
            
        # Clean up spacing
        cleaned = re.sub(r'\s+', ' ', text.strip())
        
        # Ensure proper sentence capitalization
        sentences = cleaned.split('. ')
        formatted_sentences = []
        
        for sentence in sentences:
            if sentence:
                sentence = sentence.strip()
                if sentence and not sentence[0].isupper():
                    sentence = sentence[0].upper() + sentence[1:] if len(sentence) > 1 else sentence.upper()
                formatted_sentences.append(sentence)
        
        result = '. '.join(formatted_sentences)
        
        # Ensure paragraph ends with proper punctuation
        if result and not result.endswith(('.', '!', '?', ':')):
            result += '.'
            
        return f"\n{result}"
        
    def _update_baseline_screen(self):
        """Update the baseline screen content for comparison."""
        try:
            current_image = self.capture_full_screen()
            if current_image:
                current_text = self.extract_text_from_image(current_image)
                visual_hash = self._calculate_visual_hash(current_image)
                
                if current_text and not current_text.startswith("OCR_ERROR:"):
                    self._update_baseline_screen_data(current_text, visual_hash)
        except Exception as e:
            self.logger.error(f"Error updating baseline screen: {e}")
            
    def _has_significant_change(self, current_text: str) -> bool:
        """
        Legacy method for backward compatibility.
        Now uses the more sophisticated analysis.
        """
        if not current_text:
            return False
            
        # Use the new comprehensive analysis
        if hasattr(self, '_last_visual_hash'):
            # Quick visual check first
            current_image = self.capture_full_screen()
            if current_image:
                visual_hash = self._calculate_visual_hash(current_image)
                if not self._has_significant_visual_change(visual_hash):
                    return False
                    
                analysis = self._analyze_screen_change(current_text, visual_hash)
                return analysis['is_significant']
        
        # Fallback to simple comparison if visual analysis not available
        if not self._last_screen_text:
            return True
            
        length_diff = abs(len(current_text) - len(self._last_screen_text))
        if length_diff < self._min_change_chars:
            return False
            
        # Use text similarity from new method
        clean_current = self._clean_text_for_comparison(current_text)
        clean_last = self._clean_text_for_comparison(self._last_screen_text)
        similarity = self._calculate_text_similarity(clean_current, clean_last)
        
        return similarity < self._similarity_threshold
        
    def is_monitoring_active(self) -> bool:
        """Check if continuous monitoring is currently active."""
        return self._monitoring_active
        
    def get_last_screen_content(self) -> str:
        """Get the last captured screen content."""
        return self._last_screen_text 

    def _image_to_base64(self, image: Image.Image, max_size: int = None, quality: int = 85) -> str:
        """
        Convert PIL Image to base64 string for vision model input.
        
        Args:
            image: PIL Image to convert
            max_size: Maximum image dimension (auto-resize if larger)
            quality: JPEG quality (1-100)
            
        Returns:
            Base64 encoded image string
        """
        try:
            # Use configured settings if not provided
            if max_size is None:
                max_size = self.vision_config.get('max_image_size', 1344)
            if quality is None:
                quality = self.vision_config.get('image_quality', 85)
            
            # Resize image if too large (LLaVA works best with reasonable sizes)
            if max(image.size) > max_size:
                ratio = max_size / max(image.size)
                new_size = tuple(int(dim * ratio) for dim in image.size)
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Save to bytes buffer
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=quality, optimize=True)
            
            # Encode to base64
            image_bytes = buffer.getvalue()
            base64_string = base64.b64encode(image_bytes).decode('utf-8')
            
            return base64_string
            
        except Exception as e:
            self.logger.error(f"Failed to convert image to base64: {e}")
            return ""
    
    def analyze_screen_with_vision(self, image: Image.Image, prompt: str = None) -> Dict[str, Any]:
        """
        Analyze screenshot using LLaVA vision model for comprehensive understanding.
        
        Args:
            image: Screenshot to analyze
            prompt: Custom prompt for analysis (optional)
            
        Returns:
            Dict containing vision analysis results
        """
        if not self.vision_enabled:
            return {"error": "Vision analysis disabled", "success": False}
        
        try:
            # Convert image to base64
            base64_image = self._image_to_base64(image)
            if not base64_image:
                return {"error": "Failed to encode image", "success": False}
            
            # Default prompt for comprehensive screen analysis
            if prompt is None:
                prompt = """Analyze this screenshot comprehensively. Describe:
1. What type of application or interface this is
2. Key UI elements visible (buttons, menus, forms, etc.)
3. Any text content or data displayed
4. The current state or context of the interface
5. Any notable visual elements or layout

Provide a clear, structured description focusing on actionable information."""
            
            # Prepare request to Ollama LLaVA
            payload = {
                "model": self.vision_model,
                "prompt": prompt,
                "images": [base64_image],
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temperature for consistent analysis
                    "top_p": 0.9
                }
            }
            
            # Make request to Ollama API
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json=payload,
                timeout=self.vision_timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                vision_text = result.get('response', '').strip()
                
                if vision_text:
                    return {
                        "success": True,
                        "analysis": vision_text,
                        "model": self.vision_model,
                        "confidence": 0.85,  # High confidence for vision models
                        "analysis_type": "vision",
                        "image_size": image.size,
                        "prompt_used": prompt
                    }
                else:
                    return {"error": "Empty response from vision model", "success": False}
            else:
                return {"error": f"Vision API error: {response.status_code}", "success": False}
                
        except requests.RequestException as e:
            self.logger.error(f"Vision model request failed: {e}")
            return {"error": f"Request failed: {e}", "success": False}
        except Exception as e:
            self.logger.error(f"Vision analysis failed: {e}")
            return {"error": f"Analysis failed: {e}", "success": False}
    
    def get_hybrid_screen_analysis(self, image: Image.Image = None) -> Dict[str, Any]:
        """
        Get comprehensive screen analysis combining vision model and OCR.
        
        Args:
            image: Screenshot to analyze (captures new one if None)
            
        Returns:
            Dict containing combined analysis results
        """
        try:
            # Capture screen if no image provided
            if image is None:
                image = self.capture_full_screen()
                if not image:
                    return {"error": "Failed to capture screen", "success": False}
            
            results = {
                "success": True,
                "timestamp": time.time(),
                "image_size": image.size,
                "analysis_methods": []
            }
            
            # Try vision analysis first if enabled
            if self.vision_enabled:
                vision_result = self.analyze_screen_with_vision(image)
                if vision_result.get("success"):
                    results["vision_analysis"] = vision_result.get("analysis", "")
                    results["vision_confidence"] = vision_result.get("confidence", 0.0)
                    results["analysis_methods"].append("vision")
                    results["primary_method"] = "vision"
                else:
                    results["vision_error"] = vision_result.get("error", "Unknown error")
            
            # Always try OCR as well (for text extraction)
            if self.tesseract_available:
                ocr_text = self.extract_text_from_image_enhanced(image)
                if ocr_text and not ocr_text.startswith("OCR_ERROR"):
                    results["ocr_text"] = ocr_text
                    results["analysis_methods"].append("ocr")
                    if "primary_method" not in results:
                        results["primary_method"] = "ocr"
                else:
                    results["ocr_error"] = "Failed to extract text"
            
            # Enhanced visual analysis
            if self.opencv_available:
                try:
                    visual_analysis = self.analyze_ui_elements(image)
                    if visual_analysis:
                        results["ui_elements"] = visual_analysis
                        results["analysis_methods"].append("visual_detection")
                except Exception as e:
                    results["visual_analysis_error"] = str(e)
            
            # Combine results into a comprehensive summary
            if results["analysis_methods"]:
                results["summary"] = self._create_analysis_summary(results)
                results["confidence"] = self._calculate_overall_confidence(results)
            else:
                results["success"] = False
                results["error"] = "All analysis methods failed"
            
            return results
            
        except Exception as e:
            self.logger.error(f"Hybrid screen analysis failed: {e}")
            return {"error": str(e), "success": False}
    
    def _create_analysis_summary(self, results: Dict[str, Any]) -> str:
        """Create a comprehensive summary from all analysis methods."""
        summary_parts = []
        
        # Primary analysis (vision or OCR)
        if "vision_analysis" in results:
            summary_parts.append(f"Visual Analysis: {results['vision_analysis']}")
        
        if "ocr_text" in results and results["ocr_text"]:
            ocr_text = results["ocr_text"][:500]  # Limit OCR text length
            summary_parts.append(f"Text Content: {ocr_text}")
        
        if "ui_elements" in results:
            ui_info = results["ui_elements"]
            ui_summary = f"UI Elements detected: {ui_info.get('total_elements', 0)} elements"
            if ui_info.get('buttons'):
                ui_summary += f", {len(ui_info['buttons'])} buttons"
            if ui_info.get('text_blocks'):
                ui_summary += f", {len(ui_info['text_blocks'])} text blocks"
            summary_parts.append(ui_summary)
        
        return " | ".join(summary_parts) if summary_parts else "No analysis available"
    
    def _calculate_overall_confidence(self, results: Dict[str, Any]) -> float:
        """Calculate overall confidence score from all analysis methods."""
        confidences = []
        
        if "vision_confidence" in results:
            confidences.append(results["vision_confidence"])
        
        if "ocr_text" in results and results["ocr_text"]:
            # OCR confidence based on text length and cleanliness
            text_length = len(results["ocr_text"])
            noise_ratio = len(re.findall(r'[^\w\s]', results["ocr_text"])) / max(text_length, 1)
            ocr_confidence = min(0.9, 0.3 + (text_length / 1000) * 0.4 - noise_ratio * 0.2)
            confidences.append(max(0.1, ocr_confidence))
        
        if "ui_elements" in results:
            ui_confidence = min(0.8, results["ui_elements"].get("total_elements", 0) * 0.1)
            confidences.append(ui_confidence)
        
        return sum(confidences) / len(confidences) if confidences else 0.0 