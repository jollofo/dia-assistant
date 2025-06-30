import threading
import queue
import time
import sys
from collections import deque

# Conditionally import AI clients
try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    import ollama
except ImportError:
    ollama = None


class AIWorker(threading.Thread):
    """
    Thread that aggregates data from input streams, generates a context-aware 
    prompt, and queries an LLM for a relevant suggestion.
    """
    def __init__(self, config: dict, visual_queue: queue.Queue, audio_queue: queue.Queue, text_queue: queue.Queue, response_queue: queue.Queue):
        super().__init__(daemon=True)
        # Queues for receiving data from various input threads
        self.visual_queue = visual_queue
        self.audio_queue = audio_queue
        self.text_queue = text_queue
        self.raw_audio_queue = queue.Queue() # For raw bytes from mic before transcription
        
        # Queue for sending responses back to the orchestrator
        self.response_queue = response_queue
        
        self.config = config
        self.running = True
        self.history = deque(maxlen=20)  # Increased to store more context
        self.visual_mode_enabled = False
        
        self.client = None
        self.provider = self.config.get("AI_PROVIDER", "ollama").lower()
        
        if self.provider == "gemini":
            self._init_gemini()
        elif self.provider == "ollama":
            self._init_ollama()
        else:
            print(f"FATAL: Unknown AI_PROVIDER '{self.provider}' in config.json.", file=sys.stderr)

    def _init_gemini(self):
        if not genai:
            print("FATAL: 'google-generativeai' package not installed.", file=sys.stderr); return
        try:
            api_key = self.config.get("GEMINI_API_KEY")
            if not api_key or api_key == "YOUR_GOOGLE_API_KEY":
                print("FATAL: Gemini API key not found or is a placeholder.", file=sys.stderr); return
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel('gemini-pro')
            print("AIWorker initialized with Gemini Pro.")
        except Exception as e:
            print(f"FATAL: Could not initialize Gemini model: {e}", file=sys.stderr)

    def _init_ollama(self):
        if not ollama:
            print("FATAL: 'ollama' package not installed.", file=sys.stderr); return
        try:
            self.client = ollama.Client()
            self.client.list() # Test connection
            print(f"AIWorker initialized with Ollama client.")
        except Exception as e:
            print(f"FATAL: Could not connect to Ollama: {e}", file=sys.stderr)
            print("Please ensure the Ollama application is running.", file=sys.stderr)
            self.client = None

    def _query_model(self, prompt, stream=False):
        """
        Dispatches the prompt to the configured AI provider.
        If stream=True, yields the response chunks. Otherwise, returns the full response.
        """
        if not self.client:
            if stream: yield "Error: AI provider not initialized."
            else: return "Error: AI provider not initialized."
            return

        if self.provider == "gemini":
            try:
                response_generator = self.client.generate_content(prompt, stream=stream)
                if stream:
                    for chunk in response_generator:
                        if chunk.text:
                            yield chunk.text
                else:
                    return response_generator.text.strip()
            except Exception as e:
                error_msg = f"Error querying Gemini: {e}"
                print(f"DEBUG: {error_msg}")
                if stream: yield error_msg
                else: return error_msg

        elif self.provider == "ollama":
            model_name = self.config.get("OLLAMA_MODEL", "llama3")
            print(f"DEBUG: Querying Ollama model '{model_name}' (stream={stream})")
            try:
                response_generator = self.client.chat(
                    model=model_name, 
                    messages=[{'role': 'user', 'content': prompt}],
                    stream=stream
                )
                
                if stream:
                    for chunk in response_generator:
                        content = chunk['message']['content']
                        if content:
                            yield content
                else:
                    return response_generator['message']['content'].strip()

            except Exception as e:
                error_msg = f"Error: Could not connect to Ollama model '{model_name}'."
                print(f"DEBUG: Ollama query failed: {e}")
                if stream: yield error_msg
                else: return error_msg

    def run(self):
        """The main loop for the AI worker thread."""
        if not self.client:
            print("AI Worker not running due to initialization failure.", file=sys.stderr); return
            
        print(f"AI worker thread started, using provider: {self.provider}")
        while self.running:
            visual_text, audio_text, manual_text = None, None, None
            
            # Only process visual queue if the mode is enabled
            if self.visual_mode_enabled:
                try: visual_text = self.visual_queue.get_nowait(); self.history.appendleft(f"Screen: {visual_text[:100]}...")
                except queue.Empty: pass

            try: audio_text = self.audio_queue.get_nowait(); self.history.appendleft(f"User Speech: {audio_text}")
            except queue.Empty: pass
            try: manual_text = self.text_queue.get_nowait(); self.history.appendleft(f"User Input: {manual_text}")
            except queue.Empty: pass

            if visual_text or audio_text or manual_text:
                try:
                    self.response_queue.put(("STATUS", "THINKING"))
                    prompt = self._construct_prompt(visual_text, audio_text, manual_text)
                    
                    self.response_queue.put(("STREAM_START", None))
                    full_response = ""
                    # Query the model with streaming enabled
                    for chunk in self._query_model(prompt, stream=True):
                        full_response += chunk
                        self.response_queue.put(("STREAM_CONTENT", chunk))
                    
                    self.response_queue.put(("STREAM_END", None))
                    # Store the FULL response for better context in future queries
                    self.history.appendleft(f"AI: {full_response}")
                    print(f"\n--- AI Suggestion ({self.provider}) --- \n{full_response}\n")

                except Exception as e:
                    print(f"Error querying AI provider '{self.provider}': {e}", file=sys.stderr)
                    self.response_queue.put(("STATUS", f"Error: {str(e)}"))
            time.sleep(1)
    
    def _construct_prompt(self, visual_text, audio_text, manual_text):
        """Constructs the prompt for the LLM based on current context and history."""
        history_str = "\n".join([f"- {item}" for item in self.history]) if self.history else "None"
        
        prompt = f"""You are a helpful AI assistant. Your goal is to provide relevant, contextual responses based on the user's current situation and our conversation history.

CONVERSATION HISTORY (most recent first):
{history_str}

CURRENT CONTEXT:
- User Input: "{manual_text or 'None'}"
- Screen Content: "{visual_text or 'Not available.'}"
- User Speech: "{audio_text or 'Not available.'}"

Instructions:
- Reference our previous conversation when relevant
- If the user is asking a follow-up question, build on previous responses
- Provide helpful, contextual answers based on both current input and conversation history
- Be conversational and remember what we've discussed

Response:"""
        return prompt

    def stop(self):
        """Stops the thread's main loop."""
        self.running = False 