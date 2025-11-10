"""
OCR Engine Module
Supports multiple OCR engines and image preprocessing
"""

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    cv2 = None
    np = None
    CV2_AVAILABLE = False
    print("⚠️  OpenCV not available. Image preprocessing features will be limited.")

from PIL import Image
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class OCRConfig(BaseModel):
    """OCR Configuration"""
    engine: str = Field(default="paddle", description="OCR engine: pytesseract, paddle, or google_vision")
    custom_words: List[str] = Field(default_factory=list, description="Custom dictionary words")
    lang: str = Field(default="chi_sim+eng", description="Language setting")
    page_segmentation_mode: Optional[int] = Field(default=None, description="Tesseract PSM mode (overrides auto-selection)")
    google_credentials_path: Optional[str] = Field(default=None, description="Google Vision credentials path")
    baidu_app_id: Optional[str] = Field(default=None, description="Baidu OCR App ID")
    baidu_api_key: Optional[str] = Field(default=None, description="Baidu OCR API Key")
    baidu_secret_key: Optional[str] = Field(default=None, description="Baidu OCR Secret Key")


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
                raise ImportError("google-cloud-vision not installed. Install with: pip install google-cloud-vision")
        elif self.config.engine == "baidu_cloud":
            try:
                from aip import AipOcr
                if not all([self.config.baidu_app_id, self.config.baidu_api_key, self.config.baidu_secret_key]):
                    raise ValueError("Baidu OCR requires APP_ID, API_KEY, and SECRET_KEY")
                self.client = AipOcr(self.config.baidu_app_id, self.config.baidu_api_key, self.config.baidu_secret_key)
            except ImportError:
                raise ImportError("baidu-aip not installed. Install with: pip install baidu-aip")
        elif self.config.engine == "paddle":
            try:
                from paddleocr import PaddleOCR
                # Initialize PaddleOCR with Chinese support
                self.client = PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)
            except ImportError:
                raise ImportError("paddleocr not installed. Install with: pip install paddleocr")
        else:
            try:
                import pytesseract
                # Set tesseract path (adjust according to system)
                pytesseract.pytesseract.tesseract_cmd = self._find_tesseract()
            except ImportError:
                raise ImportError("pytesseract not installed. Install with: pip install pytesseract")

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

    def preprocess_image(self, image: Image.Image, is_png: bool = False) -> Image.Image:
        """Enhanced image preprocessing with PNG-specific optimizations"""
        if not CV2_AVAILABLE:
            print("⚠️  OpenCV not available, skipping advanced preprocessing")
            return image

        # Convert to OpenCV format
        img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        if is_png:
            # Enhanced preprocessing for PNG images
            img = self._preprocess_png_image(img)
        else:
            # Standard preprocessing for PDFs/other formats
            img = self._preprocess_standard_image(img)

        return Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

    def _preprocess_png_image(self, img):
        """Enhanced preprocessing specifically for PNG images"""
        # Convert to grayscale if needed
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img

        # Adaptive thresholding for better text extraction
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        # Morphological operations to improve character separation
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
        processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        # Light denoising
        processed = cv2.medianBlur(processed, 1)

        return processed

    def _preprocess_standard_image(self, img):
        """Standard preprocessing for PDFs and other formats"""
        # Noise reduction
        img = cv2.medianBlur(img, 3)

        # Deskew
        img = self._deskew(img)

        return img

    def _deskew(self, img):
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
        if not CV2_AVAILABLE:
            # Return original image if OpenCV not available
            return image

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

    def recognize(self, image_path: str, is_png: bool = False) -> Dict[str, Any]:
        """
        Recognize text in image

        Args:
            image_path: Image file path
            is_png: Whether this is a PNG file (affects preprocessing)

        Returns:
            Dictionary containing text, confidence, and bounding boxes
        """
        image = Image.open(image_path)

        # For cloud OCR services (Google Vision, Baidu), skip local preprocessing
        # as they have their own sophisticated preprocessing pipelines
        if self.config.engine == "google_vision":
            return self._google_vision_ocr(image)
        elif self.config.engine == "baidu_cloud":
            return self._baidu_ocr(image_path)  # Baidu needs file path, not PIL image
        elif self.config.engine == "paddle":
            return self._paddle_ocr(image_path)  # PaddleOCR works with file paths
        else:
            # For local OCR (Tesseract), apply preprocessing
            if is_png:
                image = self.preprocess_image(image, is_png=True)
            return self._tesseract_ocr(image, is_png=is_png)

    def _tesseract_ocr(self, image: Image.Image, is_png: bool = False) -> Dict[str, Any]:
        """Tesseract OCR with Chinese optimization"""
        import pytesseract

        # Use configured PSM mode if specified, otherwise try multiple modes
        if self.config.page_segmentation_mode is not None:
            psm_modes = [self.config.page_segmentation_mode]
        else:
            psm_modes = [6, 3, 1]  # Try different page segmentation modes for auto-selection

        best_result = None
        best_confidence = 0

        # Try both original image and preprocessed image (if OpenCV available)
        images_to_try = [image]
        if CV2_AVAILABLE:
            images_to_try.append(self._preprocess_chinese_image(image))

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

    def _baidu_ocr(self, image_path: str) -> Dict[str, Any]:
        """Baidu Cloud OCR"""
        try:
            # Read image file
            with open(image_path, 'rb') as f:
                image_data = f.read()

            # Call Baidu OCR API
            result = self.client.basicGeneral(image_data)

            if 'words_result' in result and result['words_result']:
                # Extract text from results
                text_lines = []
                total_confidence = 0
                word_count = 0

                for item in result['words_result']:
                    text_lines.append(item['words'])
                    # Baidu provides probability for each word
                    if 'probability' in item:
                        avg_prob = item['probability'].get('average', 0)
                        total_confidence += avg_prob
                        word_count += 1

                # Join text lines with spaces to create continuous readable text
                full_text = ' '.join(text_lines)

                # Calculate average confidence
                avg_confidence = (total_confidence / word_count * 100) if word_count > 0 else 85.0

                # Note: Baidu doesn't provide bounding boxes in basicGeneral API
                # For bounding boxes, we'd need to use basicAccurateGeneral API
                bboxes = []

                return {
                    'text': full_text,
                    'confidence': avg_confidence,
                    'bboxes': bboxes,
                    'engine': 'baidu_cloud'
                }
            else:
                # No text detected
                return {
                    'text': '',
                    'confidence': 0.0,
                    'bboxes': []
                }

        except Exception as e:
            print(f"Baidu OCR error: {e}")
            return {
                'text': '',
                'confidence': 0.0,
                'bboxes': []
            }

    def _paddle_ocr(self, image_path: str) -> Dict[str, Any]:
        """PaddleOCR"""
        try:
            # Run PaddleOCR
            results = self.client.ocr(image_path, cls=True)

            if results and results[0]:
                # Extract text and confidence from results
                text_lines = []
                total_confidence = 0
                word_count = 0
                bboxes = []

                for line in results[0]:
                    if len(line) >= 2:
                        bbox = line[0]  # Bounding box coordinates
                        text_info = line[1]  # Text and confidence

                        if len(text_info) >= 2:
                            text = text_info[0]
                            confidence = text_info[1]

                            text_lines.append(text)
                            total_confidence += confidence
                            word_count += 1

                            # Convert bbox to our format (x, y, width, height)
                            if bbox and len(bbox) >= 4:
                                x_coords = [point[0] for point in bbox]
                                y_coords = [point[1] for point in bbox]
                                x_min, x_max = min(x_coords), max(x_coords)
                                y_min, y_max = min(y_coords), max(y_coords)
                                bboxes.append((x_min, y_min, x_max - x_min, y_max - y_min))

                # Join text lines with spaces to create continuous readable text
                full_text = ' '.join(text_lines)

                # Calculate average confidence (PaddleOCR confidence is 0-1, convert to 0-100)
                avg_confidence = (total_confidence / word_count * 100) if word_count > 0 else 85.0

                return {
                    'text': full_text,
                    'confidence': avg_confidence,
                    'bboxes': bboxes,
                    'engine': 'paddle'
                }
            else:
                # No text detected
                return {
                    'text': '',
                    'confidence': 0.0,
                    'bboxes': []
                }

        except Exception as e:
            print(f"PaddleOCR error: {e}")
            return {
                'text': '',
                'confidence': 0.0,
                'bboxes': []
            }
