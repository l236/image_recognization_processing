"""
Batch processing utility
Command-line batch document processing
"""

import argparse
import sys
from pathlib import Path
from typing import List

from ..api.client import DocumentParserClient


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Batch OCR and structured extraction tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage examples:
  # Process single file
  python -m doc_parser.utils.batch /path/to/file.pdf -o /output/dir

  # Batch process directory
  python -m doc_parser.utils.batch /input/dir -o /output/dir

  # Use custom configuration
  python -m doc_parser.utils.batch /input/dir -o /output/dir -c /path/to/config.json
        """
    )

    parser.add_argument(
        "input",
        help="Input file path or directory path"
    )

    parser.add_argument(
        "-o", "--output",
        required=True,
        help="Output directory path"
    )

    parser.add_argument(
        "-c", "--config",
        help="Configuration file path (JSON format)"
    )

    parser.add_argument(
        "--extensions",
        nargs="+",
        default=[".jpg", ".jpeg", ".png", ".pdf"],
        help="File extensions to process (default: .jpg .jpeg .png .pdf)"
    )

    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively process subdirectories"
    )

    args = parser.parse_args()

    # Initialize client
    try:
        client = DocumentParserClient(config_path=args.config)
    except Exception as e:
        print(f"Initialization failed: {e}", file=sys.stderr)
        sys.exit(1)

    input_path = Path(args.input)
    output_path = Path(args.output)

    # Ensure output directory exists
    output_path.mkdir(parents=True, exist_ok=True)

    # Collect files
    if input_path.is_file():
        files_to_process = [input_path]
    elif input_path.is_dir():
        files_to_process = collect_files(input_path, args.extensions, args.recursive)
    else:
        print(f"Input path does not exist: {input_path}", file=sys.stderr)
        sys.exit(1)

    if not files_to_process:
        print("No files found to process", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(files_to_process)} files to process")

    # Process files
    processed_count = 0
    error_count = 0

    for file_path in files_to_process:
        try:
            print(f"Processing: {file_path}")
            result = client.process_file(file_path)

            # Save results
            save_result(result, output_path, file_path)

            processed_count += 1

        except Exception as e:
            print(f"Processing failed {file_path}: {e}", file=sys.stderr)
            error_count += 1

    print(f"\nProcessing completed:")
    print(f"  Success: {processed_count}")
    print(f"  Failed: {error_count}")
    print(f"  Results saved to: {output_path}")


def collect_files(directory: Path, extensions: List[str], recursive: bool) -> List[Path]:
    """Collect files to process"""
    files = []

    if recursive:
        pattern = "**/*"
    else:
        pattern = "*"

    for ext in extensions:
        files.extend(directory.glob(f"{pattern}{ext}"))
        files.extend(directory.glob(f"{pattern}{ext.upper()}"))

    return sorted(list(set(files)))  # Remove duplicates and sort


def save_result(result: dict, output_dir: Path, original_file: Path):
    """Save processing results"""
    base_name = original_file.stem

    # Save raw text
    raw_text_path = output_dir / f"{base_name}_raw.txt"
    with open(raw_text_path, 'w', encoding='utf-8') as f:
        f.write(result['raw_text'])

    # Save structured JSON
    json_path = output_dir / f"{base_name}_structured.json"
    import json
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
