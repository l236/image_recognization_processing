"""
OCR Engine Module
Supports multiple OCR engines and image preprocessing
"""

import cv2
import numpy as np
from PIL import Image
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class OCRConfig(BaseModel):
    """OCR Configuration"""
    engine: str = Field(default="pytesseract", description="OCR engine: pytesseract or google_vision")
    custom_words: List[str] = Field(default_factory=list, description="Custom dictionary words")
    lang: str = Field(default="chi_sim+eng", description="Language setting")
    google_credentials_path: Optional[str] = Field(default=None, description="Google Vision credentials path")


class OCREngine:
    """OCR Engine Class"""

    def __init__(self, config: OCRConfig):
        self.config = config
        self._init_engine()

    def _init_engine(self):
        """Initialize OCR engine"""
        if self.config.engine == "google_vision":
            try:
                from google.cloud import vision
                import os
                if self.config.google_credentials_path:
                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.config.google_credentials_path
                self.client = vision.ImageAnnotatorClient()
            except ImportError:
                raise ImportError("google-cloud-vision not installed")
        else:
            try:
                import pytesseract
                # Set tesseract path (adjust according to system)
                pytesseract.pytesseract.tesseract_cmd = self._find_tesseract()
            except ImportError:
                raise ImportError("pytesseract not installed")

    def _find_tesseract(self) -> str:
        """Find tesseract executable"""
        import platform
        system = platform.system().lower()

        common_paths = [
            '/usr/local/bin/tesseract',
            '/usr/bin/tesseract',
            'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'
        ]

        for path in common_paths:
            if Path(path).exists():
                return path

        # Default path
        return '/usr/local/bin/tesseract'

    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """Image preprocessing"""
        # Convert to OpenCV format
        img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        # Noise reduction
        img = cv2.medianBlur(img, 3)

        # Deskew
        img = self._deskew(img)

        return Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

    def _deskew(self, img: np.ndarray) -> np.ndarray:
        """Deskew image"""
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
                    img = cv2.warpAffine(img, M, (w, h),
                                       flags=cv2.INTER_CUBIC,
                                       borderMode=cv2.BORDER_REPLICATE)

        return img

    def recognize(self, image_path: str) -> Dict[str, Any]:
        """
        Recognize text in image

        Args:
            image_path: Image file path

        Returns:
            Dictionary containing text, confidence, and bounding boxes
        """
        image = Image.open(image_path)

        if self.config.engine == "google_vision":
            return self._google_vision_ocr(image)
        else:
            return self._tesseract_ocr(image)

    def _tesseract_ocr(self, image: Image.Image) -> Dict[str, Any]:
        """Tesseract OCR"""
        import pytesseract

        # Preprocessing
        processed_img = self.preprocess_image(image)

        # Custom configuration
        custom_config = f'--psm 6 -l {self.config.lang}'
        if self.config.custom_words:
            # Create temporary dictionary file
            import tempfile
            import os
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write('\n'.join(self.config.custom_words))
                temp_dict_path = f.name

            custom_config += f' --user-words {temp_dict_path}'

        try:
            # OCR
            data = pytesseract.image_to_data(processed_img,
                                           config=custom_config,
                                           output_type=pytesseract.Output.DICT)

            # Extract text and confidence
            text = ' '.join([word for word in data['text'] if word.strip()])
            confidences = [conf for conf in data['conf'] if conf != -1]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            # Bounding boxes
            bboxes = [(data['left'][i], data['top'][i], data['width'][i], data['height'][i])
                     for i in range(len(data['text'])) if data['text'][i].strip()]

            return {
                'text': text,
                'confidence': avg_confidence,
                'bboxes': bboxes
            }
        finally:
            # Clean up temporary files
            if self.config.custom_words and 'temp_dict_path' in locals():
                try:
                    os.unlink(temp_dict_path)
                except:
                    pass

    def _google_vision_ocr(self, image: Image.Image) -> Dict[str, Any]:
        """Google Vision OCR"""
        from google.cloud import vision
        from io import BytesIO

        # Convert to bytes
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        content = buffer.getvalue()

        image = vision.Image(content=content)
        response = self.client.text_detection(image=image)
        texts = response.text_annotations

        if texts:
            full_text = texts[0].description
            confidence = 95.0  # Google Vision doesn't provide per-word confidence
            bboxes = []  # Can be parsed from vertices
        else:
            full_text = ""
            confidence = 0.0
            bboxes = []

        return {
            'text': full_text,
            'confidence': confidence,
            'bboxes': bboxes
        }
