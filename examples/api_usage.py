#!/usr/bin/env python3
"""
API usage example
Demonstrates how to use HTTP API for document processing
"""

import requests
import json
from pathlib import Path

def main():
    """API usage example"""

    # API server address
    base_url = "http://localhost:8000"

    # Sample file path
    sample_file = "path/to/your/document.pdf"

    print("API usage example")
    print(f"Server address: {base_url}")

    # 1. Health check
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print("✓ Server running normally")
        else:
            print("✗ Server not responding")
            return
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to server, please ensure API service is running")
        print("Run command: python -m doc_parser.api.service")
        return

    # 2. Get current configuration
    print("\nGet current configuration:")
    response = requests.get(f"{base_url}/config")
    if response.status_code == 200:
        config = response.json()
        print(json.dumps(config, indent=2, ensure_ascii=False))

    # 3. Process single file
    if Path(sample_file).exists():
        print(f"\nProcessing file: {sample_file}")

        with open(sample_file, 'rb') as f:
            files = {'file': (Path(sample_file).name, f, 'application/pdf')}
            response = requests.post(f"{base_url}/process/file", files=files)

        if response.status_code == 200:
            result = response.json()
            print("Processing results:")
            print(f"Filename: {result['filename']}")
            print(f"Raw text length: {len(result['raw_text'])}")
            print(f"Number of extracted fields: {len(result['extracted_fields'])}")

            for field in result['extracted_fields']:
                print(f"  {field['name']}: {field['value']} (Confidence: {field['confidence']:.1f}%)")
        else:
            print(f"Processing failed: {response.text}")

    # 4. Extract text only
    if Path(sample_file).exists():
        print("\nExtract text only:")

        with open(sample_file, 'rb') as f:
            files = {'file': (Path(sample_file).name, f, 'application/pdf')}
            response = requests.post(f"{base_url}/extract/text", files=files)

        if response.status_code == 200:
            result = response.json()
            text = result['text']
            print(f"Extracted text length: {len(text)}")
            print(f"Text preview: {text[:200]}...")
        else:
            print(f"Extraction failed: {response.text}")

    # 5. Update configuration
    print("\nUpdate configuration:")
    new_config = {
        "ocr": {
            "engine": "pytesseract",
            "custom_words": ["invoice", "contract", "amount", "date"],
            "lang": "chi_sim+eng"
        },
        "extraction": {
            "fields": [
                {
                    "name": "Invoice Number",
                    "pattern": "invoice number",
                    "description": "Invoice number field"
                },
                {
                    "name": "Amount",
                    "pattern": "total",
                    "description": "Amount field"
                }
            ]
        }
    }

    response = requests.put(f"{base_url}/config", json=new_config)
    if response.status_code == 200:
        print("✓ Configuration updated successfully")
    else:
        print(f"✗ Configuration update failed: {response.text}")

    print("\nAPI usage completed")

if __name__ == "__main__":
    main()
