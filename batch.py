#!/usr/bin/env python3
import argparse
import json
from main import process_batch, OCRConfig, ExtractionConfig

def main():
    parser = argparse.ArgumentParser(description="Batch OCR and Structured Extraction")
    parser.add_argument("input_folder", help="Input folder containing images/PDFs")
    parser.add_argument("output_folder", help="Output folder for results")
    parser.add_argument("--config", default="config.json", help="Configuration file path")

    args = parser.parse_args()

    # Load config
    with open(args.config, 'r', encoding='utf-8') as f:
        config_data = json.load(f)

    ocr_config = OCRConfig(**config_data['ocr'])
    extraction_config = ExtractionConfig(**config_data['extraction'])

    process_batch(args.input_folder, args.output_folder, ocr_config, extraction_config)
    print(f"Batch processing completed. Results saved to {args.output_folder}")

if __name__ == "__main__":
    main()
