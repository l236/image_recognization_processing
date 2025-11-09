#!/usr/bin/env python3
"""
spaCy Model Setup Script
Helps download and verify spaCy models required for document processing
"""

import subprocess
import sys
import os

def run_command(cmd, description):
    """Run a command and return success status"""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"Error: {e.stderr}")
        return False

def check_spacy_installation():
    """Check if spaCy is installed"""
    try:
        import spacy
        version = spacy.__version__
        print(f"✅ spaCy {version} is installed")
        return True
    except ImportError:
        print("❌ spaCy is not installed")
        return False

def download_model(model_name, description):
    """Download a spaCy model"""
    cmd = f"python -m spacy download {model_name}"
    return run_command(cmd, f"Downloading {description} ({model_name})")

def test_model(model_name, description):
    """Test if a spaCy model can be loaded"""
    try:
        import spacy
        nlp = spacy.load(model_name)
        print(f"✅ {description} loaded successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to load {description}: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 spaCy Model Setup for Document Parser")
    print("=" * 50)

    # Check spaCy installation
    if not check_spacy_installation():
        print("\n📦 Installing spaCy...")
        if not run_command("pip install spacy==3.7.2", "Installing spaCy"):
            print("❌ Failed to install spaCy. Please install manually: pip install spacy==3.7.2")
            sys.exit(1)

    # Download Chinese model (primary)
    print("\n📥 Downloading spaCy models...")
    if not download_model("zh_core_web_sm", "Chinese model"):
        print("⚠️  Chinese model download failed, trying alternative method...")
        # Try alternative download method
        try:
            import spacy
            spacy.cli.download("zh_core_web_sm")
            print("✅ Chinese model downloaded via alternative method")
        except Exception as e:
            print(f"❌ Alternative download also failed: {e}")

    # Download English model (fallback)
    download_model("en_core_web_sm", "English model")

    # Test models
    print("\n🧪 Testing model loading...")

    chinese_loaded = test_model("zh_core_web_sm", "Chinese model (zh_core_web_sm)")
    english_loaded = test_model("en_core_web_sm", "English model (en_core_web_sm)")

    # Summary
    print("\n" + "=" * 50)
    print("📋 Setup Summary:")

    if chinese_loaded:
        print("✅ Chinese model (zh_core_web_sm): Available")
    else:
        print("❌ Chinese model (zh_core_web_sm): Not available")
        print("   This is required for optimal Chinese document processing")

    if english_loaded:
        print("✅ English model (en_core_web_sm): Available (fallback)")
    else:
        print("❌ English model (en_core_web_sm): Not available")
        print("   At least one model is required")

    if chinese_loaded or english_loaded:
        print("\n🎉 Setup completed! You can now use the document parser.")
        print("   Run: streamlit run main.py")
        print("   Or:  python -m doc_parser.api.service")
    else:
        print("\n❌ Setup failed. Please check the errors above and try again.")
        print("   Manual installation:")
        print("   pip install spacy==3.7.2")
        print("   python -m spacy download zh_core_web_sm")
        print("   python -m spacy download en_core_web_sm")
        sys.exit(1)

if __name__ == "__main__":
    main()
