#!/usr/bin/env python3
"""
Setup script for Ollama and SQLCoder model
"""

import requests
import subprocess
import sys
import time
import os

def check_ollama_installed():
    """Check if Ollama is installed"""
    try:
        result = subprocess.run(['ollama', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Ollama is installed: {result.stdout.strip()}")
            return True
        else:
            print("❌ Ollama is not properly installed")
            return False
    except FileNotFoundError:
        print("❌ Ollama is not installed")
        return False

def check_ollama_running():
    """Check if Ollama server is running"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print("✅ Ollama server is running")
            return True
        else:
            print("❌ Ollama server is not responding properly")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Ollama server is not running")
        return False

def start_ollama_server():
    """Start Ollama server"""
    print("🚀 Starting Ollama server...")
    try:
        # Start Ollama in background
        subprocess.Popen(['ollama', 'serve'], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)
        
        # Wait for server to start
        print("⏳ Waiting for Ollama server to start...")
        for i in range(30):  # Wait up to 30 seconds
            time.sleep(1)
            if check_ollama_running():
                print("✅ Ollama server started successfully")
                return True
        
        print("❌ Ollama server failed to start within 30 seconds")
        return False
    except Exception as e:
        print(f"❌ Error starting Ollama server: {e}")
        return False

def check_sqlcoder_model():
    """Check if SQLCoder model is installed"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            sqlcoder_found = any(model.get('name', '').startswith('sqlcoder') for model in models)
            if sqlcoder_found:
                print("✅ SQLCoder model is installed")
                return True
            else:
                print("❌ SQLCoder model is not installed")
                return False
        else:
            print("❌ Could not check for SQLCoder model")
            return False
    except Exception as e:
        print(f"❌ Error checking for SQLCoder model: {e}")
        return False

def install_sqlcoder_model():
    """Install SQLCoder model"""
    print("📥 Installing SQLCoder model...")
    print("This may take several minutes depending on your internet connection...")
    
    try:
        result = subprocess.run(['ollama', 'pull', 'sqlcoder'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ SQLCoder model installed successfully")
            return True
        else:
            print(f"❌ Error installing SQLCoder model: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error running ollama pull: {e}")
        return False

def test_sqlcoder():
    """Test SQLCoder model with a simple query"""
    print("🧪 Testing SQLCoder model...")
    
    test_prompt = """You are an expert SQL query generator for SQLite. Generate a simple SQL query.

### DATABASE SCHEMA
Table `test` has columns: `id`, `name`.

### USER QUESTION
Show all records from test table.

### SQL QUERY
"""
    
    payload = {
        "model": "sqlcoder",
        "prompt": test_prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 50
        }
    }
    
    try:
        response = requests.post("http://localhost:11434/api/generate", 
                               json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            sql = result.get('response', '').strip()
            print(f"✅ SQLCoder test successful. Generated: {sql}")
            return True
        else:
            print(f"❌ SQLCoder test failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error testing SQLCoder: {e}")
        return False

def main():
    print("🤖 Ollama Setup for SQLCoder")
    print("=" * 40)
    
    # Step 1: Check if Ollama is installed
    if not check_ollama_installed():
        print("\n📋 To install Ollama:")
        print("1. Visit https://ollama.ai/")
        print("2. Download and install Ollama for your platform")
        print("3. Run this script again")
        return
    
    # Step 2: Check if Ollama server is running
    if not check_ollama_running():
        print("\n🚀 Starting Ollama server...")
        if not start_ollama_server():
            print("\n📋 Manual steps:")
            print("1. Open a terminal/command prompt")
            print("2. Run: ollama serve")
            print("3. Keep the terminal open")
            print("4. Run this script again in another terminal")
            return
    
    # Step 3: Check if SQLCoder model is installed
    if not check_sqlcoder_model():
        print("\n📥 Installing SQLCoder model...")
        if not install_sqlcoder_model():
            print("\n📋 Manual installation:")
            print("1. Open a terminal/command prompt")
            print("2. Run: ollama pull sqlcoder")
            print("3. Wait for download to complete")
            print("4. Run this script again")
            return
    
    # Step 4: Test SQLCoder
    if test_sqlcoder():
        print("\n🎉 Setup complete! You can now run the application:")
        print("streamlit run enhanced_app.py")
    else:
        print("\n❌ Setup incomplete. Please check the errors above.")

if __name__ == "__main__":
    main() 