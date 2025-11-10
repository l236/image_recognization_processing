"""
API Client Module
Provides clean API interface
"""

from pathlib import Path
from typing import Dict, Any, List, Union
import json
import os

from ..core.processor import DocumentProcessor, DocumentProcessorConfig, ValidationConfig
from ..core.ocr import OCRConfig
from ..core.extractor import ExtractionConfig, FieldRule


class DocumentParserClient:
    """Document parser client"""

    def __init__(self, config_path: str = None, config_dict: Dict[str, Any] = None):
        """
        Initialize client

        Args:
            config_path: Configuration file path
            config_dict: Configuration dictionary
        """
        if config_path:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
        elif config_dict:
            config_data = config_dict
        else:
            # Try to load from default config.json first
            default_config_path = Path("config.json")
            if default_config_path.exists():
                try:
                    with open(default_config_path, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                    print("✅ Loaded configuration from config.json")
                except Exception as e:
                    print(f"⚠️  Could not load config.json: {e}, using defaults")
                    config_data = self._get_default_config()
            else:
                # Default configuration
                config_data = self._get_default_config()

        # Parse configuration
        ocr_config = OCRConfig(**config_data['ocr'])
        extraction_config = ExtractionConfig(**config_data['extraction'])
        validation_config = ValidationConfig(**config_data.get('validation', {}))
        processor_config = DocumentProcessorConfig(ocr=ocr_config, extraction=extraction_config, validation=validation_config)

        self.processor = DocumentProcessor(processor_config)

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "ocr": {
                "engine": "pytesseract",
                "custom_words": ["invoice", "contract", "amount", "date", "发票", "合同", "金额", "日期"],
                "lang": "chi_sim+eng"
            },
            "extraction": {
                "fields": [
                    {
                        "name": "Invoice Number",
                        "pattern": ["invoice number", "发票号码", "invoice no"],
                        "regex_patterns": ["Invoice No\\.?\\s*(\\w+)", "发票号码[:：]\\s*(\\w+)"]
                    },
                    {
                        "name": "Amount",
                        "pattern": ["total", "amount", "总计", "合计"],
                        "regex_patterns": ["\\$\\s*([\\d,\\.]+)", "￥\\s*([\\d,\\.]+)", "金额[:：]\\s*([\\d,\\.]+)"],
                        "post_process": "amount_normalize"
                    },
                    {
                        "name": "Date",
                        "pattern": ["date", "日期", "开票日期"],
                        "entity_type": "DATE",
                        "regex_patterns": ["\\d{4}[-年]\\d{1,2}[-月]\\d{1,2}日?", "\\d{4}/\\d{1,2}/\\d{1,2}"],
                        "post_process": "date_normalize"
                    }
                ]
            },
            "validation": {
                "confidence_threshold": 0.8,
                "required_fields": []
            }
        }

    def process_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Process single file

        Args:
            file_path: File path

        Returns:
            Structured result dictionary
        """
        result = self.processor.process_file(str(file_path))
        return result.dict()

    def process_files(self, file_paths: List[Union[str, Path]]) -> List[Dict[str, Any]]:
        """
        Batch process files

        Args:
            file_paths: List of file paths

        Returns:
            List of structured result dictionaries
        """
        paths = [str(p) for p in file_paths]
        results = self.processor.process_files_batch(paths)
        return [r.dict() for r in results]

    def process_directory(self, input_dir: Union[str, Path], output_dir: Union[str, Path] = None,
                         extensions: List[str] = None) -> List[Dict[str, Any]]:
        """
        Process all files in directory

        Args:
            input_dir: Input directory
            output_dir: Output directory (optional)
            extensions: File extension list (default: ['.jpg', '.jpeg', '.png', '.pdf'])

        Returns:
            List of structured result dictionaries
        """
        if extensions is None:
            extensions = ['.jpg', '.jpeg', '.png', '.pdf']

        input_path = Path(input_dir)
        file_paths = []

        for ext in extensions:
            file_paths.extend(input_path.glob(f"**/*{ext}"))
            file_paths.extend(input_path.glob(f"**/*{ext.upper()}"))

        results = self.process_files(file_paths)

        # Save results
        if output_dir:
            self.processor.save_results(
                [self.processor.process_file(str(p)) for p in file_paths],
                str(output_dir)
            )

        return results

    def extract_text(self, file_path: Union[str, Path]) -> str:
        """
        Extract text only (without structuring)

        Args:
            file_path: File path

        Returns:
            Extracted text
        """
        images = self.processor._load_images(str(file_path))
        all_text = ""

        for img_path in images:
            ocr_result = self.processor.ocr_engine.recognize(img_path)
            all_text += ocr_result['text'] + "\n"

        return all_text.strip()

    def update_config(self, ocr_config: Dict[str, Any] = None, extraction_config: Dict[str, Any] = None, validation_config: Dict[str, Any] = None):
        """
        Update configuration

        Args:
            ocr_config: OCR configuration dictionary
            extraction_config: Extraction configuration dictionary
            validation_config: Validation configuration dictionary
        """
        if ocr_config:
            self.processor.config.ocr = OCRConfig(**ocr_config)
            self.processor.ocr_engine = self.processor.ocr_engine.__class__(self.processor.config.ocr)

        if extraction_config:
            self.processor.config.extraction = ExtractionConfig(**extraction_config)
            self.processor.extractor = self.processor.extractor.__class__(self.processor.config.extraction)

        if validation_config:
            self.processor.config.validation = ValidationConfig(**validation_config)
