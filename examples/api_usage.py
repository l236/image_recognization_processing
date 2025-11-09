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
    sample_file = "/Users/likangjia/image_recognization_processing/test_files/course.png"

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
            "lang": "chi_sim+eng",
            "page_segmentation_mode": 3
        },
        "extraction": {
            "fields": [
                {
                    "name": "Invoice Number",
                    "pattern": ["invoice number", "发票号码"],
                    "description": "Invoice number field",
                    "regex_patterns": ["Invoice No\\.?\\s*(\\w+)", "发票号码[:：]\\s*(\\w+)"]
                },
                {
                    "name": "Amount",
                    "pattern": ["total", "amount", "总计"],
                    "description": "Amount field",
                    "regex_patterns": ["\\$\\s*([\\d,\\.]+)", "￥\\s*([\\d,\\.]+)"],
                    "post_process": "amount_normalize"
                },
                {
                    "name": "Date",
                    "pattern": ["date", "日期"],
                    "description": "Date field",
                    "regex_patterns": ["\\d{4}[-/]\\d{1,2}[-/]\\d{1,2}"],
                    "post_process": "date_normalize"
                }
            ]
        },
        "validation": {
            "confidence_threshold": 0.8,
            "required_fields": ["Invoice Number", "Amount"],
            "amount_format": {
                "decimal_places": 2,
                "thousand_separator": ",",
                "decimal_separator": "."
            },
            "date_format": "YYYY-MM-DD"
        }
    }

    response = requests.put(f"{base_url}/config", json=new_config)
    if response.status_code == 200:
        print("✓ Configuration updated successfully")
    else:
        print(f"✗ Configuration update failed: {response.text}")

    # 6. Get updated configuration
    print("\\nGet updated configuration:")
    response = requests.get(f"{base_url}/config")
    if response.status_code == 200:
        config = response.json()
        print("Configuration sections:", list(config.keys()))
        print(f"OCR language: {config['ocr']['lang']}")
        print(f"Validation threshold: {config['validation']['confidence_threshold']}")
        print(f"Required fields: {config['validation']['required_fields']}")
    else:
        print(f"Failed to get configuration: {response.text}")

    print("\nAPI usage completed")

if __name__ == "__main__":
    main()
