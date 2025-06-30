#!/usr/bin/env python3
"""
Script to help set up qwen or deepseek models for Dia AI Assistant
"""
import subprocess
import sys
import json

def run_command(cmd):
    """Run a command and return the result."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def check_ollama_service():
    """Check if Ollama service is running."""
    print("🔍 Checking Ollama service...")
    success, stdout, stderr = run_command("ollama list")
    
    if success:
        print("✅ Ollama is running!")
        return True, stdout
    else:
        print("❌ Ollama service not running or not installed")
        print("💡 Try running: ollama serve")
        return False, ""

def list_available_models():
    """List currently installed models."""
    success, stdout, stderr = run_command("ollama list")
    if success and stdout.strip():
        print("\n📋 Currently installed models:")
        lines = stdout.strip().split('\n')[1:]  # Skip header
        models = []
        for line in lines:
            if line.strip():
                model_name = line.split()[0]
                models.append(model_name)
                print(f"   • {model_name}")
        return models
    else:
        print("\n📋 No models currently installed")
        return []

def suggest_models():
    """Suggest qwen and deepseek models to install."""
    print("\n🧠 Recommended models for your use case:")
    
    recommendations = [
        {
            "name": "qwen2.5:7b",
            "description": "Qwen 2.5 (7B) - Good balance of performance and speed",
            "size": "~4.4GB"
        },
        {
            "name": "qwen2.5:14b", 
            "description": "Qwen 2.5 (14B) - Better performance, larger size",
            "size": "~8.2GB"
        },
        {
            "name": "deepseek-coder:6.7b",
            "description": "DeepSeek Coder (6.7B) - Excellent for coding tasks",
            "size": "~3.8GB"
        },
        {
            "name": "qwen2.5-coder:7b",
            "description": "Qwen 2.5 Coder (7B) - Code-specialized version",
            "size": "~4.4GB"
        }
    ]
    
    for i, model in enumerate(recommendations, 1):
        print(f"\n{i}. {model['name']}")
        print(f"   {model['description']}")
        print(f"   Size: {model['size']}")
    
    return recommendations

def install_model(model_name):
    """Install a specific model."""
    print(f"\n📥 Installing {model_name}...")
    print("This may take several minutes depending on your internet connection...")
    
    success, stdout, stderr = run_command(f"ollama pull {model_name}")
    
    if success:
        print(f"✅ Successfully installed {model_name}")
        return True
    else:
        print(f"❌ Failed to install {model_name}")
        print(f"Error: {stderr}")
        return False

def update_config(model_name):
    """Update the config.json file with the selected model."""
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        
        config['OLLAMA_MODEL'] = model_name
        
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✅ Updated config.json to use model: {model_name}")
        return True
    except Exception as e:
        print(f"❌ Failed to update config.json: {e}")
        return False

def main():
    """Main setup function."""
    print("🎯 Dia AI Assistant - Model Setup")
    print("=" * 50)
    
    # Check if Ollama is running
    running, models_output = check_ollama_service()
    if not running:
        print("\n💡 Please start Ollama first:")
        print("   1. Open a new terminal")
        print("   2. Run: ollama serve")
        print("   3. Then run this script again")
        return 1
    
    # List current models
    current_models = list_available_models()
    
    # Suggest models
    recommendations = suggest_models()
    
    print(f"\n🤔 Which model would you like to use?")
    print("Enter the number (1-4) or type a custom model name:")
    
    try:
        choice = input("\nYour choice: ").strip()
        
        # Handle numeric choices
        if choice.isdigit():
            choice_num = int(choice)
            if 1 <= choice_num <= len(recommendations):
                selected_model = recommendations[choice_num - 1]["name"]
            else:
                print("Invalid choice!")
                return 1
        else:
            # Handle custom model name
            selected_model = choice
        
        print(f"\n🎯 Selected model: {selected_model}")
        
        # Check if model is already installed
        if selected_model in current_models:
            print("✅ Model already installed!")
        else:
            # Install the model
            if not install_model(selected_model):
                return 1
        
        # Update config
        if update_config(selected_model):
            print(f"\n🚀 Setup complete! Your Dia AI Assistant is now configured to use {selected_model}")
            print("\nYou can now run: python main.py")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n👋 Setup cancelled")
        return 0
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 