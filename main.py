import os
import json
import cv2
import numpy as np
from PIL import Image
import pytesseract
from google.cloud import vision
import spacy
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import pdf2image
import pdfplumber
import pandas as pd
import streamlit as st
from pathlib import Path

# Configuration Models
class FieldRule(BaseModel):
    name: str
    pattern: str
    description: str
    entity_type: Optional[str] = None

class ExtractionConfig(BaseModel):
    fields: List[FieldRule]

class OCRConfig(BaseModel):
    engine: str = "pytesseract"  # or "google_vision"
    custom_words: List[str] = []
    lang: str = "chi_sim+eng"

# Output Models
class ExtractedField(BaseModel):
    name: str
    value: Optional[str]
    confidence: float
    bbox: Optional[List[int]] = None

class StructuredOutput(BaseModel):
    filename: str
    raw_text: str
    extracted_fields: List[ExtractedField]
    low_confidence_fields: List[str]

# OCR Engine
class OCREngine:
    def __init__(self, config: OCRConfig):
        self.config = config
        if config.engine == "google_vision":
            self.client = vision.ImageAnnotatorClient()
        else:
            pytesseract.pytesseract.tesseract_cmd = r'/usr/local/bin/tesseract'  # Adjust path as needed

    def preprocess_image(self, image: Image.Image) -> Image.Image:
        # Convert to OpenCV format
        img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        # Noise reduction
        img = cv2.medianBlur(img, 3)

        # Deskew
        img = self.deskew(img)

        return Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

    def deskew(self, img):
        # Simple deskew using Hough transform
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLines(edges, 1, np.pi/180, 200)

        if lines is not None:
            angles = []
            for line in lines:
                rho, theta = line[0]
                angle = theta * 180 / np.pi - 90
                if abs(angle) < 30:  # Only consider angles within 30 degrees
                    angles.append(angle)

            if angles:
                median_angle = np.median(angles)
                if abs(median_angle) > 1:  # Only rotate if angle is significant
                    (h, w) = img.shape[:2]
                    center = (w // 2, h // 2)
                    M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
                    img = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

        return img

    def recognize_text(self, image: Image.Image) -> Dict[str, Any]:
        if self.config.engine == "google_vision":
            return self._google_vision_ocr(image)
        else:
            return self._tesseract_ocr(image)

    def _tesseract_ocr(self, image: Image.Image) -> Dict[str, Any]:
        # Preprocess
        processed_img = self.preprocess_image(image)

        # Custom config
        custom_config = f'--psm 6 -l {self.config.lang}'
        if self.config.custom_words:
            word_list = '+'.join(self.config.custom_words)
            custom_config += f' --user-words /tmp/custom_words.txt'
            with open('/tmp/custom_words.txt', 'w') as f:
                f.write('\n'.join(self.config.custom_words))

        # OCR
        data = pytesseract.image_to_data(processed_img, config=custom_config, output_type=pytesseract.Output.DICT)

        # Extract text and confidence
        text = ' '.join([word for word in data['text'] if word.strip()])
        confidences = [conf for conf in data['conf'] if conf != -1]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        return {
            'text': text,
            'confidence': avg_confidence,
            'bboxes': [(data['left'][i], data['top'][i], data['width'][i], data['height'][i]) for i in range(len(data['text'])) if data['text'][i].strip()]
        }

    def _google_vision_ocr(self, image: Image.Image) -> Dict[str, Any]:
        # Convert PIL to bytes
        from io import BytesIO
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        content = buffer.getvalue()

        image = vision.Image(content=content)
        response = self.client.text_detection(image=image)
        texts = response.text_annotations

        if texts:
            full_text = texts[0].description
            # Google Vision doesn't provide per-word confidence easily, use a default high confidence
            confidence = 95.0
            # Bboxes would need parsing from vertices
            bboxes = []
        else:
            full_text = ""
            confidence = 0.0
            bboxes = []

        return {
            'text': full_text,
            'confidence': confidence,
            'bboxes': bboxes
        }

# Structured Extraction
class StructuredExtractor:
    def __init__(self, config: ExtractionConfig):
        self.config = config
        self.nlp = spacy.load("zh_core_web_sm")  # Assuming Chinese, adjust as needed

    def extract(self, text: str, ocr_result: Dict) -> List[ExtractedField]:
        doc = self.nlp(text)
        extracted = []

        for field in self.config.fields:
            value, confidence, bbox = self._extract_field(field, doc, ocr_result)
            extracted.append(ExtractedField(
                name=field.name,
                value=value,
                confidence=confidence,
                bbox=bbox
            ))

        return extracted

    def _extract_field(self, field: FieldRule, doc, ocr_result: Dict) -> tuple:
        # Simple pattern matching - in real implementation, use more sophisticated NLP
        # For demo, assume patterns are keywords
        pattern = field.pattern.lower()
        text_lower = ocr_result['text'].lower()

        if pattern in text_lower:
            # Find position
            start = text_lower.find(pattern)
            # Extract value after pattern (simplified)
            value_start = start + len(pattern)
            value = ocr_result['text'][value_start:value_start+20].strip()  # Next 20 chars as value
            confidence = 85.0  # Placeholder
            bbox = None  # Would need to map to actual bbox
        else:
            value = None
            confidence = 0.0
            bbox = None

        return value, confidence, bbox

# Input Handler
class InputHandler:
    @staticmethod
    def process_input(file_path: str) -> List[Image.Image]:
        ext = Path(file_path).suffix.lower()
        if ext in ['.jpg', '.jpeg', '.png']:
            return [Image.open(file_path)]
        elif ext == '.pdf':
            return InputHandler._process_pdf(file_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    @staticmethod
    def _process_pdf(file_path: str) -> List[Image.Image]:
        # Try to extract text first
        with pdfplumber.open(file_path) as pdf:
            has_text = any(page.extract_text().strip() for page in pdf.pages)

        if has_text:
            # Mixed PDF - extract text and images separately
            # For simplicity, convert to images and OCR
            return pdf2image.convert_from_path(file_path)
        else:
            # Image PDF
            return pdf2image.convert_from_path(file_path)

# Main Processor
class DocumentProcessor:
    def __init__(self, ocr_config: OCRConfig, extraction_config: ExtractionConfig):
        self.ocr_engine = OCREngine(ocr_config)
        self.extractor = StructuredExtractor(extraction_config)

    def process_file(self, file_path: str) -> StructuredOutput:
        images = InputHandler.process_input(file_path)
        all_text = ""
        all_results = []

        for img in images:
            ocr_result = self.ocr_engine.recognize_text(img)
            all_text += ocr_result['text'] + "\n"
            all_results.append(ocr_result)

        # Combine OCR results
        combined_ocr = {
            'text': all_text,
            'confidence': sum(r['confidence'] for r in all_results) / len(all_results) if all_results else 0,
            'bboxes': [bbox for r in all_results for bbox in r['bboxes']]
        }

        extracted_fields = self.extractor.extract(all_text, combined_ocr)
        low_confidence = [f.name for f in extracted_fields if f.confidence < 80]

        return StructuredOutput(
            filename=Path(file_path).name,
            raw_text=all_text,
            extracted_fields=extracted_fields,
            low_confidence_fields=low_confidence
        )

# Batch Processing
def process_batch(folder_path: str, output_dir: str, ocr_config: OCRConfig, extraction_config: ExtractionConfig):
    processor = DocumentProcessor(ocr_config, extraction_config)
    os.makedirs(output_dir, exist_ok=True)

    results = []
    for file_path in Path(folder_path).glob("*"):
        if file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.pdf']:
            try:
                result = processor.process_file(str(file_path))

                # Save raw text
                with open(f"{output_dir}/{file_path.stem}_raw.txt", 'w', encoding='utf-8') as f:
                    f.write(result.raw_text)

                # Save structured JSON
                with open(f"{output_dir}/{file_path.stem}_structured.json", 'w', encoding='utf-8') as f:
                    json.dump(result.dict(), f, ensure_ascii=False, indent=2)

                results.append(result.dict())

            except Exception as e:
                print(f"Error processing {file_path}: {e}")

    # Save validation CSV
    low_conf_rows = []
    for res in results:
        for field in res['extracted_fields']:
            if field['confidence'] < 80:
                low_conf_rows.append({
                    'filename': res['filename'],
                    'field_name': field['name'],
                    'extracted_value': field['value'],
                    'confidence': field['confidence']
                })

    if low_conf_rows:
        df = pd.DataFrame(low_conf_rows)
        df.to_csv(f"{output_dir}/validation_list.csv", index=False, encoding='utf-8')

# Streamlit UI
def main():
    st.title("OCR and Structured Extraction Tool")

    # Load configs from file
    with open("config.json", 'r', encoding='utf-8') as f:
        config_data = json.load(f)

    ocr_config = OCRConfig(**config_data['ocr'])
    extraction_config = ExtractionConfig(**config_data['extraction'])

    processor = DocumentProcessor(ocr_config, extraction_config)

    uploaded_file = st.file_uploader("Upload file", type=['jpg', 'png', 'pdf'])

    if uploaded_file:
        # Save uploaded file temporarily
        temp_path = f"/tmp/{uploaded_file.name}"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        result = processor.process_file(temp_path)

        st.subheader("Raw Text")
        st.text_area("OCR Result", result.raw_text, height=200)

        st.subheader("Extracted Fields")
        for field in result.extracted_fields:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**{field.name}**")
            with col2:
                st.write(field.value or "Not extracted")
            with col3:
                st.write(f"Confidence: {field.confidence:.1f}%")

        if result.low_confidence_fields:
            st.subheader("Fields requiring manual verification")
            st.write(", ".join(result.low_confidence_fields))

        # Manual correction
        st.subheader("Manual correction")
        corrected_fields = {}
        for field in result.extracted_fields:
            corrected_value = st.text_input(f"Correct {field.name}", value=field.value or "")
            corrected_fields[field.name] = corrected_value

        if st.button("Regenerate JSON"):
            # Update fields with corrections
            for field in result.extracted_fields:
                if field.name in corrected_fields:
                    field.value = corrected_fields[field.name]
                    field.confidence = 100.0  # Assume manual correction is 100%

            result.low_confidence_fields = []

            st.download_button(
                "Download structured JSON",
                data=result.json(indent=2),
                file_name="structured_output.json",
                mime="application/json"
            )

if __name__ == "__main__":
    main()
