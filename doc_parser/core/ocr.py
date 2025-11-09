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
    page_segmentation_mode: Optional[int] = Field(default=None, description="Tesseract PSM mode (overrides auto-selection)")
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

    def _preprocess_chinese_image(self, image: Image.Image) -> Image.Image:
        """Light preprocessing optimized for Chinese text"""
        # Convert to OpenCV format
        img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        # Convert to grayscale
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img

        # Light denoising to reduce noise without destroying text
        denoised = cv2.medianBlur(gray, 1)  # Very light denoising

        # Simple thresholding - let Tesseract handle the rest
        # Use Otsu's method for automatic threshold selection
        _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        return Image.fromarray(thresh)

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
        """Tesseract OCR with Chinese optimization"""
        import pytesseract

        # Use configured PSM mode if specified, otherwise try multiple modes
        if self.config.page_segmentation_mode is not None:
            psm_modes = [self.config.page_segmentation_mode]
        else:
            psm_modes = [6, 3, 1]  # Try different page segmentation modes for auto-selection

        best_result = None
        best_confidence = 0

        # Try both original image and preprocessed image
        images_to_try = [image, self._preprocess_chinese_image(image)]

        for img in images_to_try:
            for psm in psm_modes:
                # Custom configuration optimized for Chinese
                custom_config = f'--psm {psm} -l {self.config.lang} --oem 3'

                # Add Chinese-specific parameters
                if 'chi' in self.config.lang:
                    custom_config += ' -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz\u4e00-\u9fff'

                if self.config.custom_words:
                    # Create temporary dictionary file
                    import tempfile
                    import os
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                        f.write('\n'.join(self.config.custom_words))
                        temp_dict_path = f.name

                    custom_config += f' --user-words {temp_dict_path}'

                try:
                    # OCR with current configuration
                    data = pytesseract.image_to_data(img,
                                                   config=custom_config,
                                                   output_type=pytesseract.Output.DICT)

                    # Extract text and confidence
                    text = ' '.join([word for word in data['text'] if word.strip()])
                    confidences = [conf for conf in data['conf'] if conf != -1]
                    avg_confidence = sum(confidences) / len(confidences) if confidences else 0

                    # Keep the best result
                    if avg_confidence > best_confidence and text.strip():
                        best_confidence = avg_confidence
                        best_result = {
                            'text': text,
                            'confidence': avg_confidence,
                            'bboxes': [(data['left'][i], data['top'][i], data['width'][i], data['height'][i])
                                     for i in range(len(data['text'])) if data['text'][i].strip()],
                            'psm_used': psm
                        }

                except Exception as e:
                    print(f"OCR failed with PSM {psm}: {e}")
                    continue
                finally:
                    # Clean up temporary files
                    if self.config.custom_words and 'temp_dict_path' in locals():
                        try:
                            os.unlink(temp_dict_path)
                        except:
                            pass

        return best_result or {
            'text': '',
            'confidence': 0.0,
            'bboxes': [],
            'psm_used': None
        }

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
