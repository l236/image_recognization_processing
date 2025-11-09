#!/usr/bin/env python3
"""
Basic usage example
Demonstrates how to use doc_parser for document processing
"""

from doc_parser import DocumentParserClient
from pathlib import Path
import json

def main():
    """Basic usage example"""

    # 1. Initialize client with default configuration
    print("Initializing document parser client...")
    client = DocumentParserClient()

    # 2. Process single file
    sample_file = "/Users/likangjia/image_recognization_processing/test_files/course.png"  # Replace with actual file path

    if Path(sample_file).exists():
        print(f"Processing file: {sample_file}")

        # Process file and get results
        result = client.process_file(sample_file)

        print("Processing results:")
        print(f"Filename: {result['filename']}")
        print(f"Raw text length: {len(result['raw_text'])}")
        print(f"Number of extracted fields: {len(result['extracted_fields'])}")

        # Display extracted fields
        for field in result['extracted_fields']:
            print(f"  {field['name']}: {field['value']} (Confidence: {field['confidence']:.1f}%)")

        # Display low confidence fields
        if result['low_confidence_fields']:
            print(f"Fields requiring manual verification: {', '.join(result['low_confidence_fields'])}")

    else:
        print(f"Sample file does not exist: {sample_file}")
        print("Please provide a valid file path")

    # 3. Batch process directory
    input_dir = "/Users/likangjia/image_recognization_processing/test_files"  # Replace with actual directory path
    output_dir = "/Users/likangjia/image_recognization_processing/output_files"  # Replace with output directory path

    if Path(input_dir).exists():
        print(f"\nBatch processing directory: {input_dir}")

        results = client.process_directory(input_dir, output_dir)

        print(f"Processed {len(results)} files")
        print(f"Results saved to: {output_dir}")

    # 4. Extract text only
    if Path(sample_file).exists():
        print("\nExtract text only:")
        text = client.extract_text(sample_file)
        print(f"Extracted text length: {len(text)}")
        print(f"Text preview: {text[:200]}...")

    # 5. Update configuration
    print("\nConfiguration update example:")
    new_config = {
        "ocr": {
            "engine": "pytesseract",
            "custom_words": ["invoice", "contract", "amount", "date", "custom terms"],
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

    client.update_config(ocr_config=new_config['ocr'], extraction_config=new_config['extraction'])
    print("Configuration updated")

if __name__ == "__main__":
    main()
