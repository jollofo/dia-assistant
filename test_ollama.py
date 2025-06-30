#!/usr/bin/env python3
"""
Test script to verify Ollama connectivity and model availability
"""
import os
import sys
try:
    import ollama
except ImportError:
    print("Error: ollama package not installed. Run: pip install ollama")
    sys.exit(1)

def test_ollama_connection():
    """Test connection to Ollama server."""
    try:
        # Test connection
        models = ollama.list()
        print("✅ Successfully connected to Ollama!")
        
        if 'models' in models and models['models']:
            print(f"📋 Available models: {len(models['models'])}")
            for model in models['models']:
                model_name = model.get('name', model.get('model', str(model)))
                print(f"  - {model_name}")
        else:
            print("📋 No models found. You may need to pull a model first.")
            print("   Example: ollama pull llama3.2")
        
        return True
    except Exception as e:
        print(f"❌ Failed to connect to Ollama: {e}")
        print("Make sure Ollama is running with: ollama serve")
        return False

def test_model_response(model_name="llama3.2"):
    """Test a simple chat with the specified model."""
    try:
        print(f"\n🧪 Testing model: {model_name}")
        
        response = ollama.chat(
            model=model_name,
            messages=[
                {
                    "role": "user", 
                    "content": "Respond with only this JSON: {\"status\": \"working\", \"model\": \"" + model_name + "\"}"
                }
            ],
            options={
                "temperature": 0.1,
                "num_predict": 100
            }
        )
        
        result = response['message']['content']
        print(f"✅ Model response: {result}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to get response from model {model_name}: {e}")
        print(f"Try pulling the model with: ollama pull {model_name}")
        return False

def main():
    """Main test function."""
    print("🔍 Testing Ollama setup for Dia AI Assistant\n")
    
    # Load environment variables if .env exists
    if os.path.exists('.env'):
        from dotenv import load_dotenv
        load_dotenv()
    
    # Test connection
    if not test_ollama_connection():
        return False
    
    # Get model from environment or use default
    model_name = os.getenv('OLLAMA_MODEL', 'llama3.2')
    
    # Test model response
    if not test_model_response(model_name):
        return False
    
    print(f"\n🎉 Ollama setup is working! You can now run the Dia AI Assistant with model: {model_name}")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 