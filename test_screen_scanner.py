#!/usr/bin/env python3
"""
Test script for the fixed screen scanner functionality
"""
import sys
import threading
import time
from modules.screen_scanner import ScreenScanner

def test_basic_capture():
    """Test basic screen capture functionality."""
    print("Testing basic screen capture...")
    
    config = {
        'screen': {
            'monitor_index': 0,
            'ocr_language': 'eng'
        }
    }
    
    scanner = ScreenScanner(config)
    
    # Test screenshot capture
    success = scanner.save_screenshot("test_screenshot.png")
    if success:
        print("✓ Screenshot saved successfully")
    else:
        print("✗ Screenshot failed")
    
    # Test OCR on full screen
    text = scanner.capture_and_ocr()
    if text:
        print(f"✓ OCR extracted {len(text)} characters")
        print(f"Sample text: {text[:100]}...")
    else:
        print("✗ OCR failed")

def test_threaded_capture():
    """Test screen capture in threading environment to verify fix."""
    print("\nTesting threaded screen capture...")
    
    config = {
        'screen': {
            'monitor_index': 0,
            'ocr_language': 'eng'
        }
    }
    
    results = []
    
    def capture_worker(worker_id):
        """Worker function for threaded capture."""
        scanner = ScreenScanner(config)
        
        for i in range(3):
            print(f"Worker {worker_id}: Attempt {i+1}")
            text = scanner.capture_and_ocr()
            
            if text:
                results.append(f"Worker {worker_id}: Success ({len(text)} chars)")
            else:
                results.append(f"Worker {worker_id}: Failed")
            
            time.sleep(0.5)
    
    # Create multiple threads
    threads = []
    for i in range(3):
        thread = threading.Thread(target=capture_worker, args=(i,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Print results
    print("\nThreaded capture results:")
    for result in results:
        print(f"  {result}")

def test_region_capture():
    """Test region-specific capture."""
    print("\nTesting region capture...")
    
    config = {
        'screen': {
            'monitor_index': 0,
            'ocr_language': 'eng'
        }
    }
    
    scanner = ScreenScanner(config)
    
    # Test capturing a small region (top-left corner)
    text = scanner.capture_region_and_ocr(0, 0, 400, 200)
    if text:
        print(f"✓ Region OCR extracted {len(text)} characters")
        print(f"Sample text: {text[:100]}...")
    else:
        print("✗ Region OCR failed")

def main():
    """Run all tests."""
    print("🔍 Screen Scanner Fix Verification")
    print("=" * 40)
    
    try:
        test_basic_capture()
        test_threaded_capture()
        test_region_capture()
        
        print("\n✅ All tests completed!")
        print("If you see success messages above, the threading fix is working.")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 