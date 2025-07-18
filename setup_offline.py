import os
import sys
import requests

def check_offline_requirements():
    """Check if all requirements for offline operation are met"""
    print("🔍 Checking offline requirements...")
    
    # Check database
    if os.path.exists('db/bank_exchange.db'):
        print("✅ Database: db/bank_exchange.db")
    else:
        print("❌ Database missing: db/bank_exchange.db")
        print("   Run: python create_bank_exchange_db.py")
    
    # Check data files
    data_files = [
        'data/data_dictionary.xlsx',
        'data/role_access.xlsx',
        'data/schema.pdf',
        'data/er_diagram.jpeg'
    ]
    for file in data_files:
        if os.path.exists(file):
            print(f"✅ Data: {file}")
        else:
            print(f"❌ Data missing: {file}")
            print(f"   Run the appropriate create_*.py script")
    
    # Check Ollama
    print("\n🤖 Checking Ollama setup...")
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            sqlcoder_found = any(model.get('name', '').startswith('sqlcoder') for model in models)
            if sqlcoder_found:
                print("✅ SQLCoder model found in Ollama")
            else:
                print("❌ SQLCoder model not found in Ollama")
                print("   Run: ollama pull sqlcoder")
        else:
            print("❌ Ollama API not responding properly")
    except requests.exceptions.ConnectionError:
        print("❌ Ollama not running or not accessible")
        print("   Start Ollama: ollama serve")
        print("   Install SQLCoder: ollama pull sqlcoder")
    except Exception as e:
        print(f"❌ Error checking Ollama: {e}")
    
    # Check Python packages
    required_packages = [
        'streamlit', 'pandas', 'plotly', 'fpdf', 
        'sentence_transformers', 'requests', 'openpyxl'
    ]
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ Package: {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ Package missing: {package}")
    
    if missing_packages:
        print(f"\n📦 Install missing packages:")
        print(f"pip install {' '.join(missing_packages)}")
    
    print("\n🎯 Offline Setup Summary:")
    print("1. All data files should be in data/ folder")
    print("2. Ollama should be running with sqlcoder model installed")
    print("3. All Python packages should be installed")
    print("4. Run: streamlit run enhanced_app.py")
    print("\n📋 Ollama Setup Commands:")
    print("   ollama serve                    # Start Ollama server")
    print("   ollama pull sqlcoder           # Install SQLCoder model")
    print("   ollama list                    # Check installed models")

if __name__ == "__main__":
    check_offline_requirements() 