"""
Document Processor Module
Integrates OCR and structured extraction
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from .ocr import OCREngine, OCRConfig
from .extractor import StructuredExtractor, ExtractionConfig, ExtractedField


class DocumentProcessorConfig(BaseModel):
    """Document processor configuration"""
    ocr: OCRConfig
    extraction: ExtractionConfig


class StructuredOutput(BaseModel):
    """Structured output"""
    filename: str
    raw_text: str
    extracted_fields: List[ExtractedField]
    low_confidence_fields: List[str]
    overall_confidence: float


class DocumentProcessor:
    """Document processor"""

    def __init__(self, config: DocumentProcessorConfig):
        self.config = config
        self.ocr_engine = OCREngine(config.ocr)
        self.extractor = StructuredExtractor(config.extraction)

    def process_file(self, file_path: str) -> StructuredOutput:
        """
        Process single file

        Args:
            file_path: File path

        Returns:
            Structured output
        """
        # Load images
        images = self._load_images(file_path)

        all_text = ""
        all_results = []

        # OCR process each image
        for img_path in images:
            ocr_result = self.ocr_engine.recognize(img_path)
            all_text += ocr_result['text'] + "\n"
            all_results.append(ocr_result)

        # Combine OCR results
        combined_ocr = {
            'text': all_text.strip(),
            'confidence': sum(r['confidence'] for r in all_results) / len(all_results) if all_results else 0,
            'bboxes': [bbox for r in all_results for bbox in r['bboxes']]
        }

        # Structured extraction
        extracted_fields = self.extractor.extract(all_text, combined_ocr)
        low_confidence = [f.name for f in extracted_fields if f.confidence < 80]

        return StructuredOutput(
            filename=Path(file_path).name,
            raw_text=all_text,
            extracted_fields=extracted_fields,
            low_confidence_fields=low_confidence,
            overall_confidence=combined_ocr['confidence']
        )

    def process_files_batch(self, file_paths: List[str]) -> List[StructuredOutput]:
        """
        Batch process files

        Args:
            file_paths: List of file paths

        Returns:
            List of structured outputs
        """
        results = []
        for file_path in file_paths:
            try:
                result = self.process_file(file_path)
                results.append(result)
            except Exception as e:
                # Create error result
                error_result = StructuredOutput(
                    filename=Path(file_path).name,
                    raw_text=f"Processing failed: {str(e)}",
                    extracted_fields=[],
                    low_confidence_fields=[],
                    overall_confidence=0.0
                )
                results.append(error_result)

        return results

    def _load_images(self, file_path: str) -> List[str]:
        """
        Load file as image list

        Args:
            file_path: File path

        Returns:
            List of image file paths
        """
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext in ['.jpg', '.jpeg', '.png']:
            return [file_path]
        elif ext == '.pdf':
            return self._convert_pdf_to_images(file_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    def _convert_pdf_to_images(self, pdf_path: str) -> List[str]:
        """Convert PDF to images"""
        try:
            import pdf2image
            import tempfile

            # Convert to images
            images = pdf2image.convert_from_path(pdf_path)

            # Save to temporary files
            temp_files = []
            for i, img in enumerate(images):
                temp_file = tempfile.NamedTemporaryFile(suffix=f'_page_{i}.png', delete=False)
                img.save(temp_file.name, 'PNG')
                temp_files.append(temp_file.name)

            return temp_files

        except ImportError:
            raise ImportError("pdf2image not installed")
        except Exception as e:
            raise RuntimeError(f"PDF conversion failed: {str(e)}")

    def save_results(self, results: List[StructuredOutput], output_dir: str, save_raw_text: bool = True, save_json: bool = True):
        """
        Save processing results

        Args:
            results: List of processing results
            output_dir: Output directory
            save_raw_text: Whether to save raw text
            save_json: Whether to save JSON
        """
        import json
        import pandas as pd

        os.makedirs(output_dir, exist_ok=True)

        # Save structured results for each file
        for result in results:
            base_name = Path(result.filename).stem

            if save_raw_text:
                raw_text_path = os.path.join(output_dir, f"{base_name}_raw.txt")
                with open(raw_text_path, 'w', encoding='utf-8') as f:
                    f.write(result.raw_text)

            if save_json:
                json_path = os.path.join(output_dir, f"{base_name}_structured.json")
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(result.dict(), f, ensure_ascii=False, indent=2)

        # Save validation list
        low_conf_rows = []
        for res in results:
            for field in res.extracted_fields:
                if field.confidence < 80:
                    low_conf_rows.append({
                        'filename': res.filename,
                        'field_name': field.name,
                        'extracted_value': field.value,
                        'confidence': field.confidence
                    })

        if low_conf_rows:
            df = pd.DataFrame(low_conf_rows)
            csv_path = os.path.join(output_dir, "validation_list.csv")
            df.to_csv(csv_path, index=False, encoding='utf-8')
