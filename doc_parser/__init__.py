"""
OCR and Structured Extraction Integrated Tool

Supports text recognition in images/PDFs, combining rules and NLP to convert unstructured text into standardized JSON.
"""

__version__ = "1.0.0"
__author__ = "Document Parser Team"

from .core.ocr import OCREngine
from .core.extractor import StructuredExtractor
from .core.processor import DocumentProcessor
from .api.client import DocumentParserClient

__all__ = [
    "OCREngine",
    "StructuredExtractor", 
    "DocumentProcessor",
    "DocumentParserClient"
]
