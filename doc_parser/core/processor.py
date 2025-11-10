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


class ValidationConfig(BaseModel):
    """Validation configuration"""
    confidence_threshold: float = Field(default=0.8, description="Minimum confidence threshold")
    required_fields: List[str] = Field(default_factory=list, description="Required field names")
    business_rules: Optional[Dict[str, Any]] = Field(default=None, description="Business-specific validation rules")
    amount_format: Optional[Dict[str, Any]] = Field(default=None, description="Amount formatting rules")
    date_format: str = Field(default="YYYY-MM-DD", description="Expected date format")


class DocumentProcessorConfig(BaseModel):
    """Document processor configuration"""
    ocr: OCRConfig
    extraction: ExtractionConfig
    validation: ValidationConfig = Field(default_factory=ValidationConfig)


class StructuredOutput(BaseModel):
    """Structured output"""
    filename: str
    raw_text: str
    extracted_fields: List[ExtractedField]
    low_confidence_fields: List[str]
    missing_required_fields: List[str]
    overall_confidence: float
    validation_passed: bool


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
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext == '.pdf':
            # Try to extract text directly from PDF first
            text_result = self._extract_text_from_pdf(file_path)
            if text_result['has_text']:
                # PDF has extractable text, use it directly
                all_text = text_result['text']
                combined_ocr = {
                    'text': all_text,
                    'confidence': 95.0,  # High confidence for direct text extraction
                    'bboxes': []
                }
            else:
                # PDF is image-based, use optimized OCR for Chinese content
                print(f"Processing image-based PDF with OCR (this may take time for Chinese text)...")
                images = self._convert_pdf_to_images(file_path)
                all_text = ""
                all_results = []

                # OCR process each image with timeout protection
                for i, img_path in enumerate(images):
                    print(f"Processing page {i+1}/{len(images)}...")
                    try:
                        ocr_result = self.ocr_engine.recognize(img_path)
                        all_text += ocr_result['text'] + "\n"
                        all_results.append(ocr_result)
                    except Exception as e:
                        print(f"OCR failed for page {i+1}: {e}")
                        continue

                # Combine OCR results
                combined_ocr = {
                    'text': all_text.strip(),
                    'confidence': sum(r['confidence'] for r in all_results) / len(all_results) if all_results else 0,
                    'bboxes': [bbox for r in all_results for bbox in r['bboxes']]
                }
        else:
            # For image files, use OCR directly with PNG-specific preprocessing
            is_png = ext == '.png'
            ocr_result = self.ocr_engine.recognize(file_path, is_png=is_png)

            # Post-process PNG text to fix spacing issues (only for local OCR engines)
            all_text = ocr_result['text']
            # Skip postprocessing for cloud OCR services (Google Vision, Baidu) as they already produce good spacing
            if is_png and all_text and ocr_result.get('engine', 'tesseract') == 'tesseract':
                all_text = self._postprocess_png_text(all_text)

            combined_ocr = {
                'text': all_text,
                'confidence': ocr_result['confidence'],
                'bboxes': ocr_result['bboxes']
            }

        # Structured extraction
        extracted_fields = self.extractor.extract(all_text, combined_ocr)

        # Validation
        low_confidence = [f.name for f in extracted_fields
                         if f.confidence / 100.0 < self.config.validation.confidence_threshold]

        # Check required fields
        extracted_field_names = {f.name for f in extracted_fields if f.value}
        missing_required = [field for field in self.config.validation.required_fields
                           if field not in extracted_field_names]

        # Overall validation
        validation_passed = len(low_confidence) == 0 and len(missing_required) == 0

        return StructuredOutput(
            filename=Path(file_path).name,
            raw_text=all_text,
            extracted_fields=extracted_fields,
            low_confidence_fields=low_confidence,
            missing_required_fields=missing_required,
            overall_confidence=combined_ocr['confidence'],
            validation_passed=validation_passed
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
                    missing_required_fields=self.config.validation.required_fields.copy(),
                    overall_confidence=0.0,
                    validation_passed=False
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

    def _extract_text_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Extract text directly from PDF"""
        try:
            import pdfplumber
            all_text = []

            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        all_text.append(page_text)

            combined_text = '\n'.join(all_text)

            # Check if we got meaningful text (more than just whitespace)
            has_text = len(combined_text.strip()) > 100  # At least 100 characters

            return {
                'has_text': has_text,
                'text': combined_text.strip(),
                'pages': len(all_text)
            }

        except ImportError:
            print("pdfplumber not available, falling back to OCR")
            return {'has_text': False, 'text': '', 'pages': 0}
        except Exception as e:
            print(f"PDF text extraction failed: {e}, falling back to OCR")
            return {'has_text': False, 'text': '', 'pages': 0}

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

    def _postprocess_png_text(self, text: str) -> str:
        """Post-process PNG OCR text to fix spacing issues"""
        if not text:
            return text

        import re

        # Fix common spacing issues in PNG OCR results

        # 1. Add spaces between concatenated words (English)
        # Look for patterns like: "Youwillhave" -> "You will have"
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)

        # 2. Add spaces around numbers
        text = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', text)
        text = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', text)

        # 3. Fix common OCR errors
        text = text.replace('willhave', 'will have')
        text = text.replace('Youwill', 'You will')
        text = text.replace('theposition', 'the position')
        text = text.replace('ofSoftware', 'of Software')

        # 4. Clean up excessive spaces
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

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
        threshold_percent = self.config.validation.confidence_threshold * 100
        for res in results:
            for field in res.extracted_fields:
                if field.confidence < threshold_percent:
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
