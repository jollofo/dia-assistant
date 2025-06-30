"""
Audio Transcriber Module - Real-time audio transcription for live captions

Supports both cloud-based (AssemblyAI) and local (OpenAI Whisper) transcription
for real-time meeting captions and audio analysis.
"""
import os
import threading
import queue
import time
import json
from typing import Callable, Optional, Dict, Any
from PyQt5.QtCore import QObject, pyqtSignal, QThread
import sounddevice as sd
import numpy as np
import wave
import tempfile

try:
    import assemblyai as aai
    ASSEMBLYAI_AVAILABLE = True
except ImportError:
    ASSEMBLYAI_AVAILABLE = False
    print("AssemblyAI not available - install with: pip install assemblyai[extras]")

try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print("Whisper not available - install with: pip install faster-whisper")


class AudioTranscriber(QObject):
    """
    Real-time audio transcriber with support for multiple backends.
    """
    
    # Signals for real-time transcription events
    transcript_received = pyqtSignal(str, bool)  # text, is_final
    transcription_started = pyqtSignal()
    transcription_stopped = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the audio transcriber.
        
        Args:
            config: Configuration dictionary with transcription settings
        """
        super().__init__()
        
        self.config = config.get('transcription', {})
        self.provider = self.config.get('provider', 'whisper')  # 'assemblyai' or 'whisper'
        self.sample_rate = self.config.get('sample_rate', 16000)
        self.chunk_duration = self.config.get('chunk_duration', 2.0)  # seconds
        self.language = self.config.get('language', 'en')
        
        # Audio capture settings
        self.device_index = self.config.get('device_index', None)  # None = default
        self.channels = self.config.get('channels', 1)  # Mono
        
        # State management
        self.is_transcribing = False
        self.audio_queue = queue.Queue()
        self.transcription_thread = None
        self.audio_thread = None
        
        # Provider-specific initialization
        self._init_provider()
        
        print(f"Audio transcriber initialized with {self.provider} provider")
    
    def _init_provider(self):
        """Initialize the selected transcription provider."""
        if self.provider == 'assemblyai':
            if not ASSEMBLYAI_AVAILABLE:
                raise ImportError("AssemblyAI not available. Install with: pip install assemblyai[extras]")
            
            api_key = os.getenv('ASSEMBLYAI_API_KEY')
            if not api_key:
                raise ValueError("ASSEMBLYAI_API_KEY environment variable required for AssemblyAI provider")
            
            aai.settings.api_key = api_key
            self.assemblyai_transcriber = None
            
        elif self.provider == 'whisper':
            if not WHISPER_AVAILABLE:
                raise ImportError("Whisper not available. Install with: pip install faster-whisper")
            
            model_size = self.config.get('whisper_model', 'base')
            print(f"Loading Whisper model: {model_size}")
            self.whisper_model = WhisperModel(model_size, device="cpu", compute_type="int8")
            
        else:
            raise ValueError(f"Unknown transcription provider: {self.provider}")
    
    def start_transcription(self):
        """Start real-time audio transcription."""
        if self.is_transcribing:
            print("Transcription already running")
            return
        
        try:
            self.is_transcribing = True
            
            # Start audio capture thread
            self.audio_thread = threading.Thread(target=self._audio_capture_loop, daemon=True)
            self.audio_thread.start()
            
            # Start transcription thread based on provider
            if self.provider == 'assemblyai':
                self._start_assemblyai_transcription()
            elif self.provider == 'whisper':
                self._start_whisper_transcription()
            
            self.transcription_started.emit()
            print("Real-time transcription started")
            
        except Exception as e:
            self.error_occurred.emit(f"Failed to start transcription: {str(e)}")
            self.is_transcribing = False
    
    def stop_transcription(self):
        """Stop real-time audio transcription."""
        if not self.is_transcribing:
            return
        
        print("Stopping transcription...")
        self.is_transcribing = False
        
        # Stop AssemblyAI transcriber if running
        if hasattr(self, 'assemblyai_transcriber') and self.assemblyai_transcriber:
            try:
                self.assemblyai_transcriber.close()
            except Exception as e:
                print(f"Error closing AssemblyAI transcriber: {e}")
        
        # Wait for threads to finish
        if self.audio_thread and self.audio_thread.is_alive():
            self.audio_thread.join(timeout=2.0)
        
        if self.transcription_thread and self.transcription_thread.is_alive():
            self.transcription_thread.join(timeout=2.0)
        
        self.transcription_stopped.emit()
        print("Transcription stopped")
    
    def _audio_capture_loop(self):
        """Capture audio from the selected device."""
        try:
            chunk_frames = int(self.sample_rate * self.chunk_duration)
            
            def audio_callback(indata, frames, time, status):
                if status:
                    print(f"Audio capture status: {status}")
                
                if self.is_transcribing:
                    # Convert to mono if stereo
                    if indata.shape[1] > 1:
                        audio_data = np.mean(indata, axis=1)
                    else:
                        audio_data = indata[:, 0]
                    
                    # Add to queue for transcription
                    self.audio_queue.put(audio_data.copy())
            
            with sd.InputStream(
                device=self.device_index,
                channels=self.channels,
                samplerate=self.sample_rate,
                blocksize=chunk_frames,
                callback=audio_callback,
                dtype=np.float32
            ):
                print(f"Audio capture started - Device: {self.device_index}, Sample Rate: {self.sample_rate}")
                while self.is_transcribing:
                    time.sleep(0.1)
                    
        except Exception as e:
            self.error_occurred.emit(f"Audio capture error: {str(e)}")
    
    def _start_assemblyai_transcription(self):
        """Start AssemblyAI real-time transcription."""
        try:
            def on_data(transcript: aai.RealtimeTranscript):
                if not transcript.text:
                    return
                
                is_final = isinstance(transcript, aai.RealtimeFinalTranscript)
                self.transcript_received.emit(transcript.text, is_final)
            
            def on_error(error: aai.RealtimeError):
                self.error_occurred.emit(f"AssemblyAI error: {error}")
            
            def on_open(session_opened: aai.RealtimeSessionOpened):
                print(f"AssemblyAI session opened: {session_opened.session_id}")
            
            def on_close():
                print("AssemblyAI session closed")
            
            self.assemblyai_transcriber = aai.RealtimeTranscriber(
                on_data=on_data,
                on_error=on_error,
                on_open=on_open,
                on_close=on_close,
                sample_rate=self.sample_rate,
            )
            
            # Connect and stream audio
            self.assemblyai_transcriber.connect()
            
            # Start streaming thread
            self.transcription_thread = threading.Thread(
                target=self._assemblyai_stream_loop, 
                daemon=True
            )
            self.transcription_thread.start()
            
        except Exception as e:
            self.error_occurred.emit(f"AssemblyAI setup error: {str(e)}")
    
    def _assemblyai_stream_loop(self):
        """Stream audio data to AssemblyAI."""
        try:
            while self.is_transcribing:
                try:
                    # Get audio data from queue
                    audio_data = self.audio_queue.get(timeout=1.0)
                    
                    # Convert float32 to int16 for AssemblyAI
                    audio_int16 = (audio_data * 32767).astype(np.int16)
                    audio_bytes = audio_int16.tobytes()
                    
                    # Stream to AssemblyAI
                    self.assemblyai_transcriber.stream(audio_bytes)
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    if self.is_transcribing:
                        print(f"Streaming error: {e}")
                        
        except Exception as e:
            self.error_occurred.emit(f"AssemblyAI streaming error: {str(e)}")
    
    def _start_whisper_transcription(self):
        """Start local Whisper transcription."""
        self.transcription_thread = threading.Thread(
            target=self._whisper_transcription_loop, 
            daemon=True
        )
        self.transcription_thread.start()
    
    def _whisper_transcription_loop(self):
        """Process audio chunks with Whisper."""
        try:
            audio_buffer = []
            buffer_duration = 0.0
            transcription_interval = self.config.get('whisper_interval', 3.0)  # seconds
            
            while self.is_transcribing:
                try:
                    # Collect audio data
                    audio_data = self.audio_queue.get(timeout=1.0)
                    audio_buffer.append(audio_data)
                    buffer_duration += self.chunk_duration
                    
                    # Transcribe when we have enough audio
                    if buffer_duration >= transcription_interval:
                        # Combine audio chunks
                        combined_audio = np.concatenate(audio_buffer)
                        
                        # Save to temporary file for Whisper
                        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                            temp_path = temp_file.name
                            
                            # Write WAV file
                            with wave.open(temp_path, 'wb') as wav_file:
                                wav_file.setnchannels(1)
                                wav_file.setsampwidth(2)  # 16-bit
                                wav_file.setframerate(self.sample_rate)
                                
                                # Convert to int16
                                audio_int16 = (combined_audio * 32767).astype(np.int16)
                                wav_file.writeframes(audio_int16.tobytes())
                        
                        try:
                            # Transcribe with Whisper
                            segments, info = self.whisper_model.transcribe(
                                temp_path,
                                language=self.language if self.language != 'auto' else None
                            )
                            
                            # Combine all segments into one text
                            text_parts = []
                            for segment in segments:
                                text_parts.append(segment.text)
                            
                            text = ' '.join(text_parts).strip()
                            if text:
                                # Emit as final transcript (Whisper doesn't do partial)
                                self.transcript_received.emit(text, True)
                                
                        except Exception as e:
                            print(f"Whisper transcription error: {e}")
                        finally:
                            # Clean up temp file
                            try:
                                os.unlink(temp_path)
                            except:
                                pass
                        
                        # Reset buffer
                        audio_buffer = []
                        buffer_duration = 0.0
                        
                except queue.Empty:
                    continue
                except Exception as e:
                    if self.is_transcribing:
                        print(f"Whisper processing error: {e}")
                        
        except Exception as e:
            self.error_occurred.emit(f"Whisper transcription error: {str(e)}")
    
    def get_available_devices(self) -> list:
        """Get list of available audio input devices."""
        try:
            devices = sd.query_devices()
            input_devices = []
            
            for i, device in enumerate(devices):
                if device['max_input_channels'] > 0:
                    input_devices.append({
                        'index': i,
                        'name': device['name'],
                        'channels': device['max_input_channels'],
                        'sample_rate': device['default_samplerate']
                    })
            
            return input_devices
        except Exception as e:
            print(f"Error getting audio devices: {e}")
            return []
    
    def set_device(self, device_index: Optional[int]):
        """Set the audio input device."""
        self.device_index = device_index
        print(f"Audio device set to: {device_index}")


class TranscriptionManager(QObject):
    """
    Manager class for coordinating transcription with the UI and other components.
    """
    
    # Signals for UI updates
    captions_updated = pyqtSignal(str, bool)  # text, is_final
    transcription_status_changed = pyqtSignal(bool)  # is_active
    error_occurred = pyqtSignal(str)
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the transcription manager."""
        super().__init__()
        
        self.config = config
        self.transcriber = AudioTranscriber(config)
        self.transcript_log = []
        
        # Connect transcriber signals
        self.transcriber.transcript_received.connect(self._on_transcript_received)
        self.transcriber.transcription_started.connect(
            lambda: self.transcription_status_changed.emit(True)
        )
        self.transcriber.transcription_stopped.connect(
            lambda: self.transcription_status_changed.emit(False)
        )
        self.transcriber.error_occurred.connect(self.error_occurred.emit)
        
        print("Transcription manager initialized")
    
    def start_live_captions(self):
        """Start live captions transcription."""
        self.transcriber.start_transcription()
    
    def stop_live_captions(self):
        """Stop live captions transcription."""
        self.transcriber.stop_transcription()
    
    def _on_transcript_received(self, text: str, is_final: bool):
        """Handle received transcript."""
        # Add to log if final
        if is_final and text.strip():
            timestamp = time.strftime("%H:%M:%S")
            self.transcript_log.append({
                'timestamp': timestamp,
                'text': text.strip()
            })
        
        # Emit for UI updates
        self.captions_updated.emit(text, is_final)
    
    def save_transcript(self, filepath: str):
        """Save the transcript log to a file."""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("# Meeting Transcript\n\n")
                f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                for entry in self.transcript_log:
                    f.write(f"[{entry['timestamp']}] {entry['text']}\n\n")
            
            print(f"Transcript saved to: {filepath}")
            return True
            
        except Exception as e:
            self.error_occurred.emit(f"Failed to save transcript: {str(e)}")
            return False
    
    def clear_transcript(self):
        """Clear the transcript log."""
        self.transcript_log.clear()
        print("Transcript log cleared")
    
    def get_available_devices(self):
        """Get available audio input devices."""
        return self.transcriber.get_available_devices()
    
    def set_audio_device(self, device_index: Optional[int]):
        """Set the audio input device."""
        self.transcriber.set_device(device_index) 