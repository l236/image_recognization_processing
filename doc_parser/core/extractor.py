"""
Structured Extraction Module
Entity extraction based on rules and NLP
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class FieldRule(BaseModel):
    """Field extraction rule"""
    name: str = Field(..., description="Field name")
    pattern: str = Field(..., description="Matching pattern")
    description: str = Field(default="", description="Field description")
    entity_type: Optional[str] = Field(default=None, description="Entity type (DATE, MONEY, etc.)")


class ExtractionConfig(BaseModel):
    """Extraction configuration"""
    fields: List[FieldRule] = Field(default_factory=list, description="Field rule list")


class ExtractedField(BaseModel):
    """Extracted field"""
    name: str
    value: Optional[str]
    confidence: float
    bbox: Optional[List[int]] = None


class StructuredExtractor:
    """Structured extractor"""

    def __init__(self, config: ExtractionConfig):
        self.config = config
        self.nlp = None
        self._init_nlp()

    def _init_nlp(self):
        """Initialize NLP model"""
        try:
            import spacy
            self.nlp = spacy.load("zh_core_web_sm")
        except (ImportError, OSError):
            # If no Chinese model, try English model
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except (ImportError, OSError):
                # If neither, use simple pattern matching
                self.nlp = None

    def extract(self, text: str, ocr_result: Dict[str, Any]) -> List[ExtractedField]:
        """
        Extract structured information from text

        Args:
            text: OCR recognized text
            ocr_result: OCR result dictionary

        Returns:
            List of extracted fields
        """
        extracted = []

        for field in self.config.fields:
            value, confidence, bbox = self._extract_field(field, text, ocr_result)
            extracted.append(ExtractedField(
                name=field.name,
                value=value,
                confidence=confidence,
                bbox=bbox
            ))

        return extracted

    def _extract_field(self, field: FieldRule, text: str, ocr_result: Dict[str, Any]) -> tuple:
        """Extract single field"""
        pattern = field.pattern.lower()
        text_lower = text.lower()

        # Simple pattern matching
        if pattern in text_lower:
            # Find pattern position
            start = text_lower.find(pattern)
            # Extract value after pattern (simplified implementation)
            value_start = start + len(pattern)
            value = text[value_start:value_start+50].strip()  # Take next 50 characters as value

            # Clean value
            value = self._clean_extracted_value(value)

            confidence = 85.0  # Default confidence for pattern matching
            bbox = None  # Simplified implementation, no bounding box provided

            return value, confidence, bbox
        else:
            # Try NLP entity recognition
            if self.nlp and field.entity_type:
                return self._extract_by_entity_type(field, text)

            return None, 0.0, None

    def _extract_by_entity_type(self, field: FieldRule, text: str) -> tuple:
        """Extract based on entity type"""
        doc = self.nlp(text)

        # Search by entity type
        entity_map = {
            "DATE": ["DATE", "TIME"],
            "MONEY": ["MONEY"],
            "PERSON": ["PERSON"],
            "ORG": ["ORG"],
            "GPE": ["GPE", "LOC"]
        }

        target_labels = entity_map.get(field.entity_type, [])

        for ent in doc.ents:
            if ent.label_ in target_labels:
                return ent.text, 80.0, None

        return None, 0.0, None

    def _clean_extracted_value(self, value: str) -> str:
        """Clean extracted value"""
        if not value:
            return ""

        # Remove common end characters
        stop_chars = "。；，,.;:：\n\t"
        for char in stop_chars:
            value = value.split(char)[0]

        return value.strip()
