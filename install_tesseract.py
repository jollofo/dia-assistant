#!/usr/bin/env python3
"""
Tesseract OCR Installation Helper for Dia AI Assistant
This script helps detect and fix tesseract PATH issues on Windows.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def check_tesseract():
    """Check if tesseract is accessible."""
    try:
        result = subprocess.run(['tesseract', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ Tesseract is working correctly!")
            version = result.stdout.split('\n')[0]
            print(f"   {version}")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    
    print("❌ Tesseract not found in PATH")
    return False

def find_tesseract_windows():
    """Find tesseract installation on Windows."""
    common_paths = [
        "C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
        "C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe",
        "C:\\Users\\{}\\AppData\\Local\\Programs\\Tesseract-OCR\\tesseract.exe".format(os.getenv('USERNAME')),
        "C:\\tesseract\\tesseract.exe"
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            print(f"✅ Found tesseract at: {path}")
            return Path(path).parent
    
    print("❌ Tesseract installation not found in common locations")
    return None

def add_to_path_instructions(tesseract_dir):
    """Provide instructions to add tesseract to PATH."""
    print("\n🔧 To fix the PATH issue:")
    print("1. Copy this path:", str(tesseract_dir))
    print("2. Open Windows Settings > System > About")
    print("3. Click 'Advanced system settings'")
    print("4. Click 'Environment Variables'")
    print("5. Under 'System Variables', find and select 'Path'")
    print("6. Click 'Edit' > 'New'")
    print("7. Paste the tesseract path and click 'OK'")
    print("8. Restart this application")
    
    print(f"\nOr run this command as Administrator:")
    print(f'setx /M PATH "%PATH%;{tesseract_dir}"')

def main():
    """Main function to check and help fix tesseract installation."""
    print("🔍 Dia AI Assistant - Tesseract OCR Checker")
    print("=" * 50)
    
    # Check current status
    if check_tesseract():
        print("\n🎉 Your tesseract installation is working perfectly!")
        return
    
    # Windows-specific help
    if platform.system() == "Windows":
        print("\n🔍 Searching for tesseract installation...")
        tesseract_dir = find_tesseract_windows()
        
        if tesseract_dir:
            add_to_path_instructions(tesseract_dir)
        else:
            print("\n📥 Tesseract needs to be installed:")
            print("1. Download from: https://github.com/UB-Mannheim/tesseract/wiki")
            print("2. Run: tesseract-ocr-w64-setup-*.exe")
            print("3. During installation, check 'Add Tesseract to your PATH'")
            print("4. Restart this application")
            
            print("\n💡 Alternative quick install:")
            print("If you have chocolatey: choco install tesseract")
            print("If you have scoop: scoop install tesseract")
    else:
        print("\n📥 Install tesseract for your system:")
        print("Ubuntu/Debian: sudo apt install tesseract-ocr")
        print("macOS: brew install tesseract")
        print("Other: See https://tesseract-ocr.github.io/tessdoc/Installation.html")

if __name__ == "__main__":
    main() 