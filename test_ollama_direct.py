#!/usr/bin/env python3
"""
Simple test script to verify Ollama connectivity and model availability
"""
import ollama
import json

def test_ollama_connection():
    """Test if Ollama is running and accessible."""
    print("🔍 Testing Ollama Connection...")
    
    try:
        client = ollama.Client()
        
        # Test connection by listing models
        models = client.list()
        print("✅ Ollama is running!")
        
        print(f"\n📋 Available models ({len(models['models'])} found):")
        for model in models['models']:
            print(f"   • {model['name']}")
            
        return client, models
        
    except Exception as e:
        print(f"❌ Ollama connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure Ollama is installed: https://ollama.ai")
        print("2. Start Ollama service: ollama serve")
        print("3. Check if Ollama is running: ollama list")
        return None, None

def test_model_query(client, model_name="qwen3"):
    """Test if we can query a specific model."""
    print(f"\n🧠 Testing model '{model_name}'...")
    
    try:
        # Simple test query
        response = client.chat(
            model=model_name, 
            messages=[{'role': 'user', 'content': 'Hello! Just say "Hi" back.'}]
        )
        
        result = response['message']['content']
        print(f"✅ Model '{model_name}' responded: {result}")
        return True
        
    except Exception as e:
        print(f"❌ Model '{model_name}' failed: {e}")
        
        # Suggest alternatives
        print(f"\nSuggestions:")
        print(f"1. Install the model: ollama pull {model_name}")
        print("2. Try a common model like: ollama pull llama3.2")
        print("3. Update config.json to use an available model")
        return False

def suggest_fix():
    """Suggest how to fix the config."""
    print(f"\n🔧 Recommended fix for config.json:")
    
    suggested_config = {
        "AI_PROVIDER": "ollama",
        "OLLAMA_MODEL": "llama3.2",  # More common model
        "GEMINI_API_KEY": "YOUR_GOOGLE_API_KEY", 
        "TESSERACT_CMD_PATH": "C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
        "SCREEN_MONITOR_INDEX": 0,
        "SCREEN_OCR_LANGUAGE": "eng"
    }
    
    print(json.dumps(suggested_config, indent=2))

def main():
    """Main test function."""
    print("🎯 Dia AI Assistant - Ollama Debug Test")
    print("=" * 50)
    
    # Test connection
    client, models = test_ollama_connection()
    if not client:
        return 1
    
    # Load current config
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        current_model = config.get('OLLAMA_MODEL', 'qwen3')
        print(f"\n⚙️  Current config model: {current_model}")
    except Exception as e:
        print(f"❌ Could not load config.json: {e}")
        return 1
    
    # Test the configured model
    success = test_model_query(client, current_model)
    
    if not success:
        # Test with a common alternative
        print(f"\n🔄 Trying fallback model 'llama3.2'...")
        fallback_success = test_model_query(client, "llama3.2")
        
        if fallback_success:
            suggest_fix()
    
    print(f"\n✅ Test completed!")
    return 0 if success else 1

if __name__ == "__main__":
    import sys
    sys.exit(main()) 