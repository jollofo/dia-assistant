# Dia AI Assistant

A proactive AI assistant that continuously analyzes conversation transcripts and provides real-time insights and actionable suggestions.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)

## Overview

Dia AI Assistant is an intelligent conversation companion that:
- **👁 Sees your screen** using OCR to analyze visual content
- **🎤 Hears conversations** through continuous audio transcription  
- **💬 Accepts text prompts** for direct AI interaction
- **🧠 Provides AI insights** and actionable suggestions
- **📊 Streams responses** in real-time with suggested actions

## Features

### 🎯 **Multi-Modal Input**
- **Screen Vision**: OCR-powered screen content analysis
- **Audio Listening**: Continuous speech recognition and transcription
- **Text Input**: Direct prompt entry for AI queries
- **Real-time Processing**: Instant AI analysis and response streaming

### 🤖 **Intelligent Analysis**
- **Context-Aware Insights**: AI understands what you're doing
- **Actionable Suggestions**: Relevant next steps and recommendations
- **Knowledge Lookup**: Instant definitions and explanations
- **Conversation Tracking**: Maintains context across interactions

### 🖥️ **Modern Interface**
- **Compact Overlay**: Stays on top, doesn't interfere with work
- **Streaming Output**: Responses appear in real-time
- **Visual Feedback**: Color-coded buttons and status indicators
- **Draggable Window**: Position anywhere on screen

## Installation

### Prerequisites

1. **Python 3.10+** installed on your system
2. **Ollama** with a compatible model (e.g., gemma3:latest)
3. **Tesseract OCR** for screen text extraction
4. **Microphone** access for audio input

### Step 1: Install Tesseract OCR

**🔧 Windows Installation (Required for screen analysis):**

**Option A: Download Installer (Recommended)**
1. Go to: https://github.com/UB-Mannheim/tesseract/wiki
2. Download the latest Windows installer: `tesseract-ocr-w64-setup-*.exe`
3. Run the installer as Administrator
4. **IMPORTANT**: During installation, check "Add Tesseract to your PATH"
5. Complete the installation

**Option B: Package Managers**
```powershell
# Using Chocolatey
choco install tesseract

# Using Scoop  
scoop install tesseract

# Using Winget
winget install --id UB-Mannheim.TesseractOCR
```

**Verify Installation:**
```bash
tesseract --version
```
You should see version information if installed correctly.

### Step 2: Setup Dia AI Assistant

1. **Clone or download the project**:
   ```bash
   git clone <repository-url>
   cd dia
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install and setup Ollama**:
   - Download from [ollama.ai](https://ollama.ai)
   - Install a compatible model:
     ```bash
     ollama pull gemma3:latest
     ```
   - Ensure Ollama is running on `http://localhost:11434`

4. **Configure environment** (optional):
   - Copy `.env.example` to `.env`
   - Modify settings as needed

5. **Run the application**:
   ```bash
   python main.py
   ```

## Configuration

The application uses `config.json` for configuration. Key settings include:

```json
{
    "ollama": {
        "base_url": "http://localhost:11434",
        "model": "gemma3:latest",
        "timeout": 30
    },
    "audio": {
        "sample_rate": 16000,
        "chunk_size": 1024,
        "channels": 1
    },
    "ui": {
        "overlay_width": 400,
        "overlay_height": 300,
        "transparency": 0.95,
        "position": {"x": 50, "y": 50}
    },
    "analysis": {
        "interval_seconds": 15,
        "max_transcript_length": 5000
    }
}
```

## Usage

### Starting the Assistant

1. Ensure Ollama is running with your chosen model
2. Run `python main.py`
3. The overlay window will appear with control buttons

### Using the Interface

#### **👁 Eye Button (Screen Analysis)**
- Click to capture and analyze current screen content
- AI will extract text and provide insights
- Suggests relevant actions based on what's visible

#### **🎤 Mic Button (Audio Listening)**
- Click to toggle continuous audio transcription
- Button turns red when actively listening
- AI analyzes conversations every 15 seconds

#### **💬 Text Input**
- Type questions or prompts directly
- Press Enter to submit
- AI provides immediate responses and suggestions

#### **✕ Close Button**
- Closes the assistant application

### Example Interactions

The assistant can help with:
- **Screen Analysis**: "I see you're working on a Python project. Would you like help debugging?"
- **Meeting Notes**: Automatic insights from ongoing conversations
- **Knowledge Lookup**: "Define machine learning" or "Explain REST APIs"
- **Task Suggestions**: Context-aware recommendations for next steps

## Troubleshooting

### Common Issues

1. **"Tesseract not found" Error**:
   - Install Tesseract OCR from the link above
   - Make sure "Add to PATH" was checked during installation
   - Restart the application after installation
   - Verify with: `tesseract --version`

2. **Microphone not working**:
   - Check system permissions for microphone access
   - Ensure no other applications are using the microphone
   - Try running as administrator (Windows)

3. **Ollama connection failed**:
   - Verify Ollama is running: `ollama list`
   - Check the model is installed: `ollama pull gemma3:latest`
   - Ensure correct URL in config.json

4. **UI not appearing**:
   - Check display settings and scaling
   - Try adjusting position in config.json
   - Ensure PyQt6 is properly installed

5. **Speech recognition errors**:
   - Check internet connection (Google Speech API)
   - Verify microphone quality and positioning
   - Adjust audio settings in config.json

### Performance Tips

- Use a smaller, faster LLM model for better response times
- Adjust `interval_seconds` for more or less frequent analysis
- Limit `max_transcript_length` to control memory usage
- Close other audio applications to avoid conflicts

## Dependencies

- **speechrecognition**: Audio-to-text conversion
- **pyaudio**: Microphone access
- **mss**: Screen capture functionality
- **pillow**: Image processing
- **pytesseract**: OCR capabilities
- **requests**: HTTP requests to Ollama
- **python-dotenv**: Environment configuration
- **PyQt6**: GUI framework

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions:
- Check the troubleshooting section above
- Review configuration settings
- Ensure all dependencies are properly installed
- Verify that Ollama and Tesseract are running and accessible

## Roadmap

Future enhancements may include:
- Browser automation for web tasks
- Integration with calendar and task management systems
- Voice command recognition and response
- Multi-language support
- Cloud deployment options
- Mobile companion app 