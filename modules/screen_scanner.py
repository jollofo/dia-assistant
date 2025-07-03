"""
Screen Scanner Module
Provides on-demand screen capture and OCR functionality with intelligent change detection.
"""

import mss
from PIL import Image, ImageChops
import logging
from typing import Dict, Any, Optional, Tuple, Callable, Set
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

class ScreenScanner:
    """
    Handles screen capture and optical character recognition (OCR) functionality.
    Supports both on-demand scanning and continuous monitoring with intelligent change detection.
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
        
        self.logger.info(f"ScreenScanner initialized with intelligent change detection - Tesseract available: {self.tesseract_available}")
        
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