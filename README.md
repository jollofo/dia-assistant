# Dia AI Assistant

A voice-controlled AI assistant that can listen to speech, analyze screen content, and perform automated actions through web browsers.

## Features

- **Voice Recognition**: Continuously listens for voice commands using speech recognition
- **Screen Analysis**: Captures and analyzes screen content using OCR
- **Intent Recognition**: Uses OpenAI GPT to understand user intent from voice and visual context
- **Browser Automation**: Performs actions like sending emails through browser automation via Browserbase
- **Enhanced Visual Overlay**: Cluely-inspired visual feedback system with animated indicators and minimal dashboard
- **Transparent UI**: Provides a non-intrusive overlay for status updates with close functionality
- **Live Audio Transcription**: Real-time meeting captions with both cloud (AssemblyAI) and local (Whisper) options
- **System Tray Integration**: Runs in the background with system tray controls

## Architecture

The project follows a modular architecture with four main components:

### 1. Input Perception (The Senses)
- **AudioListener**: Captures microphone input and transcribes speech in a background thread
- **ScreenScanner**: Takes screenshots and extracts text using OCR

### 2. Orchestration (The Brain)
- **Orchestrator**: Main logic coordinator that processes inputs and determines actions
- Uses OpenAI GPT to analyze speech and screen context for intent recognition

### 3. Action Agents (The Hands)
- **BaseAgent**: Abstract base class for all action agents
- **BrowserbaseEmailAgent**: Automates email sending through Gmail via Browserbase API

### 4. User Interface (The Face)
- **VisualOverlay**: Enhanced Cluely-inspired visual feedback system with dashboard
- **OverlayWindow**: Simple transparent, always-on-top status display
- **System Tray**: Background operation with context menu controls

## Project Structure

```
dia/
├── core/
│   ├── __init__.py
│   ├── orchestrator.py      # Main brain logic
│   └── agent_manager.py     # Agent coordination
├── modules/
│   ├── __init__.py
│   ├── audio_listener.py    # Voice input capture
│   ├── screen_scanner.py    # Screen content analysis
│   └── agents/
│       ├── __init__.py
│       ├── base_agent.py    # Agent interface
│       └── email_agent.py   # Email automation
├── ui/
│   ├── __init__.py
│   ├── overlay.py           # Simple status overlay window
│   └── visual_overlay.py    # Enhanced Cluely-inspired overlay
├── main.py                  # Application entry point
├── requirements.txt         # Python dependencies
├── config.json             # Configuration settings
├── .env                    # Environment variables (API keys)
└── README.md               # This file
```

## Setup Instructions

### Prerequisites

1. **Python 3.10+** installed
2. **Tesseract OCR** engine installed and accessible in system PATH
3. **LLM Provider** - Choose one:
   - **Ollama** (Recommended for testing): Free local LLM server
   - **OpenAI**: Requires API key for GPT models
4. **Browserbase API Key** for browser automation

### Installation

1. **Clone or create the project directory**:
   ```bash
   mkdir dia-assistant
   cd dia-assistant
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Tesseract OCR**:
   - **Windows**: Download from [GitHub Tesseract releases](https://github.com/UB-Mannheim/tesseract/wiki)
   - **macOS**: `brew install tesseract`
   - **Linux**: `sudo apt-get install tesseract-ocr`

5. **Install and setup Ollama (Recommended for testing)**:
   ```bash
   # Install Ollama (see https://ollama.ai)
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # Start Ollama server
   ollama serve
   
   # Pull a model (in another terminal)
   ollama pull llama3.2
   ```

6. **Configure environment variables**:
   The `.env` file is already configured for Ollama by default:
   ```bash
   # For Ollama (default)
   LLM_PROVIDER=ollama
   OLLAMA_MODEL=llama3.2
   
   # For OpenAI (if preferred)
   # LLM_PROVIDER=openai
   # OPENAI_API_KEY=your_openai_api_key_here
   
   BROWSERBASE_API_KEY=your_browserbase_api_key_here
   ```

7. **Test Ollama setup** (if using Ollama):
   ```bash
   python test_ollama.py
   ```

8. **Test the Visual Overlay** (optional demo):
   ```bash
   python demo_visual_overlay.py
   ```

9. **Configure settings**:
   Adjust `config.json` for your preferences (audio sensitivity, UI position, etc.)

### Running the Application

```bash
python main.py
```

The application will:
1. Start in the background with a system tray icon
2. Begin listening for voice input
3. Show status updates in a transparent overlay
4. Process voice commands and perform actions

### Usage

1. **Voice Commands**: Speak naturally - the system will transcribe and analyze your speech
2. **Email Example**: "Send an email to john@example.com with subject 'Meeting' saying 'Let's meet tomorrow'"
3. **System Tray**: Right-click the tray icon for options like testing voice input or quitting
4. **Status Overlay**: Shows current status in the top-right corner (configurable)
5. **Live Captions**: Use "Toggle Live Captions" in system tray to start real-time transcription
6. **Close Application**: Use the close button (×) in the overlay UI or the "Quit" option in system tray

## Visual Overlay Features

The enhanced visual overlay system provides a Cluely-inspired interface with:

### 🎨 **Visual Feedback**
- **Animated Pulsing Indicators**: Color-coded status indicators that pulse during active states
- **State-Based Colors**: 
  - 🔵 Blue: Listening for voice input
  - 🟠 Orange: Processing speech/intent
  - 🟢 Green: Action completed successfully
  - 🔴 Red: Error occurred
  - ⚪ Gray: Idle/ready state

### 📊 **Minimal Dashboard**
- **Status Cards**: Real-time information display
  - Current system status
  - Active LLM model
  - Action count
  - Confidence levels
- **Progress Indicators**: Animated progress bars during processing
- **Activity Logging**: Tracks recent system activities

### 🎛️ **Interactive Controls**
- **Minimize/Restore**: Toggle between full and compact view
- **Close Button**: Quit the entire application directly from the overlay UI
- **Settings Button**: Access configuration options
- **Drag-to-Move**: Reposition overlay anywhere on screen
- **Resize**: Drag window edges/corners to resize to your preferred size
- **Auto-Hide**: Automatically hides after inactivity

### ⚡ **Smart Behavior**
- **Context-Aware**: Shows relevant information based on current state
- **Non-Intrusive**: Transparent background, stays out of the way
- **Always-on-Top**: Visible over other applications
- **Responsive**: Smooth animations and transitions
- **Dynamic Sizing**: Resizable windows with size preferences saved to configuration
- **Adaptive Layout**: Content scales appropriately with window size changes

To try the visual overlay demo:
```bash
python demo_visual_overlay.py
```

## Configuration

### Audio Settings (`config.json`)
- `energy_threshold`: Microphone sensitivity (default: 300)
- `pause_threshold`: Silence duration to end speech (default: 1.0s)
- `timeout`: Max listening time per attempt (default: 5.0s)

### UI Settings
- `overlay_position`: Where to show status overlay ("top-right", "top-left", etc.)
- `overlay_opacity`: Transparency level (0.0-1.0)
- `status_timeout`: How long to show status messages (ms)
- `overlay_size`: Preferred width and height for overlay windows
- `overlay_resize_enabled`: Enable/disable window resizing functionality

### Transcription Settings
- `provider`: Transcription provider ("whisper" or "assemblyai")
- `sample_rate`: Audio sample rate (16000 recommended)
- `language`: Language code for transcription ("en", "es", "fr", etc.)
- `whisper_model`: Whisper model size ("tiny", "base", "small", "medium", "large")
- `whisper_interval`: Seconds between Whisper transcriptions (3.0 recommended)
- `device_index`: Audio input device (null = default)
- `ui.position`: Caption position ("bottom-center", "top-center", etc.)
- `ui.font_size`: Caption text size (14 recommended)
- `ui.auto_hide`: Automatically hide captions after silence

### Screen Settings
- `monitor_index`: Which monitor to capture (0 = primary)
- `ocr_language`: Language for OCR text recognition (default: "eng")

## Live Captions & Transcription

The Dia AI Assistant now includes real-time audio transcription capabilities for meeting captions and audio analysis.

### 🎤 **Features**
- **Real-time Transcription**: Live captions from microphone or system audio
- **Multiple Providers**: Choose between cloud (AssemblyAI) or local (Whisper) transcription
- **Meeting Transcripts**: Automatic saving of transcribed text with timestamps
- **Customizable Display**: Adjustable caption positioning, font size, and auto-hide settings

### 🔧 **Supported Transcription Providers**

**AssemblyAI (Cloud-based)**:
- High accuracy real-time transcription
- Supports partial and final transcripts
- Requires API key and billing setup
- Best for production use

**OpenAI Whisper (Local)**:
- Free local transcription
- Multiple model sizes (tiny, base, small, medium, large)
- No internet required after setup
- Better privacy (all processing local)

### 📱 **Using Live Captions**

1. **Start Live Captions**: Right-click system tray → "Toggle Live Captions"
2. **Caption Display**: Appears at bottom-center of screen (configurable)
3. **Save Transcript**: Click "💾 Save" button or use system tray option
4. **Clear Captions**: Click "🗑 Clear" button to reset display
5. **Stop Captions**: Click "×" button or toggle from system tray

### ⚙️ **Configuration**

Configure transcription in `config.json`:

```json
{
  "transcription": {
    "provider": "whisper",
    "sample_rate": 16000,
    "language": "en",
    "whisper_model": "base",
    "whisper_interval": 3.0,
    "ui": {
      "position": "bottom-center",
      "opacity": 0.9,
      "font_size": 14,
      "auto_hide": true,
      "hide_delay": 5000
    }
  }
}
```

### 🚀 **Setup Instructions**

**For AssemblyAI**:
1. Get API key from [AssemblyAI](https://www.assemblyai.com)
2. Add to `.env`: `ASSEMBLYAI_API_KEY=your_api_key_here`
3. Set `"provider": "assemblyai"` in config

**For Whisper**:
1. Install with: `pip install faster-whisper`
2. Choose model size in config: `"whisper_model": "base"`
3. First run will download the model automatically

## Supported Intents

Currently supported voice commands:

- **SEND_EMAIL**: Send emails through Gmail
  - Extracts: recipient email, subject, message body
  - Example: "Send an email to sarah@company.com about the project update"

## Extending the System

### Adding New Agents

1. Create a new agent class inheriting from `BaseAgent`
2. Implement the `execute(entities)` method
3. Register the agent in `AgentManager`
4. Update the LLM prompt in `Orchestrator` to recognize the new intent

### Example: Adding a Calendar Agent

```python
# modules/agents/calendar_agent.py
from modules.agents.base_agent import BaseAgent

class CalendarAgent(BaseAgent):
    def execute(self, entities):
        # Implement calendar event creation
        pass

# Register in agent_manager.py
self.agent_registry["CREATE_EVENT"] = CalendarAgent
```

## Troubleshooting

### Common Issues

1. **"No module named 'speech_recognition'"**
   - Ensure virtual environment is activated
   - Run `pip install -r requirements.txt`

2. **"Tesseract not found"**
   - Install Tesseract OCR and add to system PATH
   - On Windows, may need to set TESSDATA_PREFIX environment variable

3. **"OpenAI API Error"** (if using OpenAI)
   - Check API key in `.env` file
   - Ensure you have OpenAI credits available
   - Try switching to Ollama for testing: set `LLM_PROVIDER=ollama` in `.env`

3. **"Ollama connection error"** (if using Ollama)
   - Make sure Ollama is running: `ollama serve`
   - Check if model is installed: `ollama list`
   - Pull your model: `ollama pull llama3.2`
   - Test with: `python test_ollama.py`

4. **"Browserbase API Error"**
   - Verify Browserbase API key
   - Check internet connection

5. **"Permission denied for microphone"**
   - Grant microphone permissions to Python/terminal
   - On macOS: System Preferences > Security & Privacy > Microphone

### Debug Mode

Set `DEBUG=true` in `.env` for verbose logging.

## Development

### Testing Voice Input
Use the "Test Voice Input" option in the system tray menu to simulate voice commands without speaking.

### Switching LLM Providers
To switch between Ollama and OpenAI, edit `.env`:

**For local testing with Ollama (free)**:
```bash
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2  # or llama3, codellama, etc.
```

**For production with OpenAI**:
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=your_api_key_here
```

### Adding New Features
The modular architecture makes it easy to extend:
- Add new input methods in `modules/`
- Create new agents for different actions
- Extend the UI with additional windows or notifications

## Changelog

### Version 1.1 (December 2024)

**New Features:**
- ✨ **UI Close Functionality**: Added close buttons to both overlay types allowing users to quit the application directly from the UI
  - Visual overlay: Red × button in the controls section with hover effects
  - Standard overlay: "× Close" button with Material Design red styling
- 🔗 **Enhanced Signal Connections**: Connected close button signals to main application quit functionality
- 📏 **Dynamic Resizing**: Made both overlay windows fully resizable with intelligent constraints
  - Drag window edges/corners to resize to preferred dimensions
  - Smart cursor changes indicate resize directions (horizontal, vertical, diagonal)
  - Size preferences automatically saved to configuration file
  - Minimum/maximum size constraints prevent unusable window sizes
- 🎤 **Live Audio Transcription**: Real-time meeting captions and audio transcription
  - Support for both cloud (AssemblyAI) and local (OpenAI Whisper) transcription
  - Live captions overlay with Material Design styling
  - Automatic transcript saving with timestamps
  - Configurable caption positioning, font size, and auto-hide behavior
  - System tray controls for easy toggle and transcript management

**Improvements:**
- 📖 **Documentation Updates**: Updated README with comprehensive close and resize functionality documentation
- 🎨 **UI Consistency**: Consistent close button styling across both overlay types
- 🛡️ **Graceful Shutdown**: Close buttons trigger the same graceful shutdown process as system tray quit
- 🔧 **Persistent Preferences**: User resize preferences saved and restored across application restarts
- 📐 **Adaptive Positioning**: Window positioning logic handles dynamic sizes correctly

**Technical Changes:**
- Added `close_requested` pyqtSignal to both OverlayWindow and VisualOverlay classes
- Enhanced control layout in visual overlay to accommodate close button
- Updated signal connections in main.py to handle close requests
- Replaced `setFixedSize()` with dynamic sizing using `setMinimumSize()`, `setMaximumSize()`, and `resize()`
- Implemented custom mouse event handlers for resize detection and execution
- Added configuration support for `overlay_size` and `overlay_resize_enabled` settings
- Enhanced positioning logic to work with variable window dimensions
- Created new `AudioTranscriber` class with multi-provider support (AssemblyAI, Whisper)
- Implemented `TranscriptionManager` for coordinating transcription with UI components
- Added `CaptionsOverlay` window for displaying live captions with Material Design
- Integrated real-time audio capture using sounddevice library
- Added comprehensive transcription configuration options to config.json

### Version 1.0 (November 2024)
- 🚀 Initial release with complete modular architecture
- 🎯 Voice recognition and screen analysis capabilities
- 🤖 OpenAI/Ollama LLM integration for intent recognition
- 📧 Email automation through Browserbase
- 🎨 Enhanced visual overlay with Cluely-inspired design
- 🖥️ System tray integration

## License

This project is provided as-is for educational and development purposes.

## Contributing

Feel free to fork and enhance the project. Key areas for improvement:
- Additional action agents (calendar, file management, etc.)
- Better error handling and retry logic
- Multi-language support
- Voice training for better recognition
- Security enhancements for API key management 