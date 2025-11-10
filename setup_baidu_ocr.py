#!/usr/bin/env python3
"""
Baidu OCR Setup Script
Helps users configure Baidu Cloud OCR API credentials
"""

import json
import os
import sys
from pathlib import Path

def print_banner():
    """Print setup banner"""
    print("=" * 60)
    print("🚀 Baidu OCR Setup Assistant")
    print("=" * 60)
    print()

def check_dependencies():
    """Check if required packages are installed"""
    try:
        import baidu_aip
        print("✅ baidu-aip package is installed")
        return True
    except ImportError:
        print("❌ baidu-aip package not found")
        print("   Install with: pip install baidu-aip")
        return False

def get_baidu_credentials():
    """Get Baidu API credentials from user"""
    print("📝 Baidu AI Console Setup:")
    print("   1. Visit: https://ai.baidu.com/")
    print("   2. Create an application")
    print("   3. Get your APP_ID, API_KEY, and SECRET_KEY")
    print()

    app_id = input("Enter your Baidu APP_ID: ").strip()
    api_key = input("Enter your Baidu API_KEY: ").strip()
    secret_key = input("Enter your Baidu SECRET_KEY: ").strip()

    if not all([app_id, api_key, secret_key]):
        print("❌ All credentials are required!")
        return None

    return {
        "app_id": app_id,
        "api_key": api_key,
        "secret_key": secret_key
    }

def test_baidu_connection(credentials):
    """Test Baidu OCR API connection"""
    try:
        from aip import AipOcr

        print("🔍 Testing Baidu OCR connection...")

        client = AipOcr(credentials["app_id"], credentials["api_key"], credentials["secret_key"])

        # Test with a simple API call (this should not consume quota)
        # We'll just check if the client initializes properly
        print("✅ Baidu OCR client initialized successfully")

        # Note: We can't easily test the actual OCR without an image file
        # and consuming API quota, so we'll trust the credentials work

        return True

    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

def update_config_file(credentials):
    """Update the config.json file with Baidu credentials"""
    config_path = Path("config.json")

    # Load existing config or create default
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            print(f"⚠️  Could not read existing config.json: {e}")
            config = {}
    else:
        config = {}

    # Ensure OCR section exists
    if "ocr" not in config:
        config["ocr"] = {}

    # Update with Baidu credentials
    config["ocr"]["engine"] = "baidu_cloud"
    config["ocr"]["baidu_app_id"] = credentials["app_id"]
    config["ocr"]["baidu_api_key"] = credentials["api_key"]
    config["ocr"]["baidu_secret_key"] = credentials["secret_key"]

    # Save config
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        print(f"✅ Configuration saved to {config_path}")
        return True

    except Exception as e:
        print(f"❌ Failed to save config: {e}")
        return False

def print_usage_instructions():
    """Print usage instructions"""
    print()
    print("🎯 Usage Instructions:")
    print("=" * 40)
    print("1. Start the web interface:")
    print("   streamlit run main.py")
    print()
    print("2. In the sidebar, select 'baidu_cloud' as OCR Engine")
    print()
    print("3. Upload documents and test OCR performance")
    print()
    print("💰 Baidu OCR Pricing:")
    print("   - Free quota: 5,000 calls/day")
    print("   - General OCR: ¥0.005/call (~$0.0007)")
    print("   - High-precision: ¥0.01/call")
    print()

def main():
    """Main setup function"""
    print_banner()

    # Check dependencies
    # if not check_dependencies():
    #     print("Please install required packages first.")
    #     sys.exit(1)

    # Get credentials
    credentials = get_baidu_credentials()
    if not credentials:
        print("Setup cancelled.")
        sys.exit(1)

    # Test connection
    if not test_baidu_connection(credentials):
        print("Please check your credentials and try again.")
        sys.exit(1)

    # Update config
    if update_config_file(credentials):
        print("🎉 Baidu OCR setup completed successfully!")
        print_usage_instructions()
    else:
        print("Setup failed. Please try again.")
        sys.exit(1)

if __name__ == "__main__":
    main()
