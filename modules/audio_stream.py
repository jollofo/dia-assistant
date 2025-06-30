import threading
import queue
import numpy as np
import time
import sys
import pyaudio

class AudioDataStream(threading.Thread):
    """
    Thread for continuously capturing audio data using a non-blocking 
    PyAudio stream, which is more robust against data loss.
    """
    def __init__(self, output_queue: queue.Queue, config: dict):
        super().__init__(daemon=True)
        self.output_queue = output_queue
        self.internal_queue = queue.Queue()
        self.config = config
        
        # Audio settings
        self.sample_rate = 16000
        self.chunk_duration_seconds = 5
        self.frames_per_buffer = 1024 # Smaller chunk size for callback
        self.audio_format = pyaudio.paInt16
        self.channels = 1
        
        self.frames_to_collect = self.sample_rate * self.chunk_duration_seconds
        self.running = True
        self.p = pyaudio.PyAudio()
        print("AudioDataStream initialized with PyAudio.")

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """This callback is executed in a separate thread by PyAudio."""
        self.internal_queue.put(in_data)
        return (None, pyaudio.paContinue)

    def run(self):
        """The main loop for the audio data stream thread."""
        try:
            device_info = self.p.get_default_input_device_info()
            device_index = device_info['index']
            print(f"Using microphone: {device_info['name']}")

            stream = self.p.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.frames_per_buffer,
                input_device_index=device_index,
                stream_callback=self._audio_callback
            )
            stream.start_stream()

            collected_frames = []
            while self.running:
                # Get a small chunk from the callback via the internal queue
                chunk_bytes = self.internal_queue.get()
                collected_frames.append(chunk_bytes)

                # Check if we have collected enough frames for a 5-second segment
                num_bytes = len(b''.join(collected_frames))
                num_samples = num_bytes // 2 # 16-bit samples (2 bytes)
                
                if num_samples >= self.frames_to_collect:
                    full_chunk_bytes = b''.join(collected_frames)
                    
                    # Convert the raw bytes to a numpy array of float32, which Whisper expects
                    audio_np = np.frombuffer(full_chunk_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                    self.output_queue.put(audio_np)
                    collected_frames = [] # Reset for the next segment
            
            # Cleanup
            stream.stop_stream()
            stream.close()
            self.p.terminate()
            print("PyAudio stream stopped.")

        except Exception as e:
            print(f"FATAL: PyAudio stream error: {e}", file=sys.stderr)
            print("Please ensure you have a working microphone.", file=sys.stderr)

    def stop(self):
        """Stops the thread's main loop."""
        self.running = False


class AudioTranscriber(threading.Thread):
    """
    Thread for transcribing audio chunks from a queue using Whisper.
    """
    def __init__(self, input_queue: queue.Queue, output_queue: queue.Queue, config: dict):
        super().__init__(daemon=True)
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.config = config
        self.running = True
        
        try:
            import whisper
            # Load the whisper model. "base" is a good starting point.
            self.model = whisper.load_model("base")
            print("Whisper model loaded successfully.")
        except ImportError:
            print("FATAL: 'openai-whisper' is not installed. Please run 'pip install openai-whisper'.", file=sys.stderr)
            self.model = None
        except Exception as e:
            print(f"FATAL: Could not load Whisper model: {e}", file=sys.stderr)
            self.model = None

    def run(self):
        """The main loop for the audio transcription thread."""
        if not self.model:
            print("Audio transcriber not running due to initialization failure.", file=sys.stderr)
            return

        print("Audio transcriber thread started.")
        while self.running:
            try:
                # Get raw audio data from the queue
                audio_chunk = self.input_queue.get()
                
                # The audio from soundcard is multi-channel, whisper expects mono.
                # We can average the channels or just take the first one.
                if audio_chunk.ndim > 1:
                    audio_chunk = audio_chunk[:, 0]

                # Process with Whisper
                result = self.model.transcribe(audio_chunk.astype(np.float32), fp16=False)
                text = result.get("text", "").strip()

                if text:
                    print(f"Audio Stream: Transcribed: '{text}'")
                    self.output_queue.put(text)
                
                self.input_queue.task_done()

            except queue.Empty:
                # This is okay, just means no audio to process right now
                time.sleep(0.1)
            except Exception as e:
                print(f"Error during audio transcription: {e}", file=sys.stderr)
                time.sleep(1)
        
        print("Audio transcriber thread finished.")

    def stop(self):
        """Stops the thread's main loop."""
        self.running = False 