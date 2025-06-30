#!/usr/bin/env python3
"""
Test script for live audio transcription functionality

This script demonstrates the real-time transcription capabilities
of the Dia AI Assistant without running the full application.
"""
import sys
import json
from PyQt6.QtWidgets import QApplication
from modules.audio_transcriber import TranscriptionManager
from ui.captions_overlay import CaptionsOverlay


def load_config():
    """Load configuration for testing."""
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Default config for testing
        return {
            "transcription": {
                "provider": "whisper",
                "sample_rate": 16000,
                "chunk_duration": 2.0,
                "language": "en",
                "whisper_model": "tiny",  # Use tiny model for faster testing
                "whisper_interval": 3.0,
                "device_index": None,
                "channels": 1,
                "ui": {
                    "position": "bottom-center",
                    "opacity": 0.9,
                    "max_lines": 3,
                    "font_size": 14,
                    "auto_hide": False,  # Keep visible for testing
                    "hide_delay": 5000,
                    "size": {
                        "width": 600,
                        "height": 150
                    }
                }
            }
        }


def main():
    """Run the transcription test."""
    print("🎤 Dia AI Assistant - Live Transcription Test")
    print("=" * 50)
    
    # Create Qt application
    app = QApplication(sys.argv)
    
    # Load configuration
    config = load_config()
    
    # Initialize transcription manager
    try:
        transcription_manager = TranscriptionManager(config)
        print("✅ Transcription manager initialized")
    except Exception as e:
        print(f"❌ Failed to initialize transcription manager: {e}")
        print("\nTroubleshooting:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. For Whisper: pip install faster-whisper")
        print("3. For AssemblyAI: pip install assemblyai[extras]")
        print("4. Check audio device permissions")
        return 1
    
    # Initialize captions overlay
    captions_overlay = CaptionsOverlay(config)
    print("✅ Captions overlay initialized")
    
    # Connect signals
    transcription_manager.captions_updated.connect(captions_overlay.update_captions)
    
    def on_transcription_status(is_active):
        status = "🟢 ACTIVE" if is_active else "🔴 STOPPED"
        print(f"Transcription status: {status}")
        if is_active:
            captions_overlay.show_overlay()
    
    def on_transcription_error(error):
        print(f"❌ Transcription error: {error}")
    
    transcription_manager.transcription_status_changed.connect(on_transcription_status)
    transcription_manager.error_occurred.connect(on_transcription_error)
    
    # Show available audio devices
    devices = transcription_manager.get_available_devices()
    print(f"\n📱 Available audio devices ({len(devices)} found):")
    for device in devices:
        print(f"  {device['index']}: {device['name']} ({device['channels']} channels)")
    
    # Show configuration
    provider = config.get('transcription', {}).get('provider', 'whisper')
    print(f"\n⚙️  Configuration:")
    print(f"  Provider: {provider}")
    print(f"  Sample Rate: {config.get('transcription', {}).get('sample_rate', 16000)} Hz")
    print(f"  Language: {config.get('transcription', {}).get('language', 'en')}")
    
    if provider == 'whisper':
        model = config.get('transcription', {}).get('whisper_model', 'base')
        print(f"  Whisper Model: {model}")
    
    # Start transcription
    print(f"\n🚀 Starting live transcription...")
    print("   Speak into your microphone to see real-time captions!")
    print("   Press Ctrl+C to stop")
    
    try:
        transcription_manager.start_live_captions()
        
        # Run the application
        return app.exec()
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopping transcription...")
        transcription_manager.stop_live_captions()
        return 0
    except Exception as e:
        print(f"\n❌ Error during transcription: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 