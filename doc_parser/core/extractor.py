"""
Structured Extraction Module
Entity extraction based on rules and NLP
"""

from typing import Dict, Any, List, Optional, Union
import re
from pydantic import BaseModel, Field


class FieldRule(BaseModel):
    """Field extraction rule"""
    name: str = Field(..., description="Field name")
    pattern: Union[str, List[str]] = Field(..., description="Matching pattern(s)")
    description: str = Field(default="", description="Field description")
    entity_type: Optional[str] = Field(default=None, description="Entity type (DATE, MONEY, etc.)")
    regex_patterns: Optional[List[str]] = Field(default=None, description="Regex patterns for extraction")
    post_process: Optional[str] = Field(default=None, description="Post-processing function name")


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
        """Initialize NLP model - spaCy models are required"""
        try:
            import spacy
        except ImportError:
            raise ImportError(
                "spaCy is required for this application. "
                "Install with: pip install spacy\n"
                "Then download models with:\n"
                "  python -m spacy download zh_core_web_sm  # Chinese model\n"
                "  python -m spacy download en_core_web_sm  # English fallback"
            )

        # Try Chinese model first (required for Chinese document processing)
        try:
            self.nlp = spacy.load("zh_core_web_sm")
            print("✅ Loaded Chinese spaCy model (zh_core_web_sm)")
        except (ImportError, OSError) as e:
            print(f"❌ Chinese spaCy model not found: {e}")
            print("Please install with: python -m spacy download zh_core_web_sm")
            try:
                # Fallback to English model
                self.nlp = spacy.load("en_core_web_sm")
                print("⚠️  Using English spaCy model (en_core_web_sm) as fallback")
                print("For better Chinese processing, install: python -m spacy download zh_core_web_sm")
            except (ImportError, OSError) as e2:
                raise ImportError(
                    f"No spaCy models available. Please install models:\n"
                    f"  python -m spacy download zh_core_web_sm  # Primary (Chinese)\n"
                    f"  python -m spacy download en_core_web_sm  # Fallback (English)\n"
                    f"Error: {e2}"
                )

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
        # Try regex patterns first (highest priority)
        if field.regex_patterns:
            for regex_pattern in field.regex_patterns:
                match = re.search(regex_pattern, text, re.IGNORECASE)
                if match:
                    value = match.group(1) if match.groups() else match.group(0)
                    value = self._clean_extracted_value(value)

                    # Apply post-processing if specified
                    if field.post_process:
                        value = self._apply_post_process(field.post_process, value)

                    confidence = 90.0  # Higher confidence for regex matches
                    bbox = None
                    return value, confidence, bbox

        # Try pattern matching (support both string and list)
        patterns = [field.pattern] if isinstance(field.pattern, str) else field.pattern
        for pattern in patterns:
            pattern_lower = pattern.lower()
            text_lower = text.lower()

            if pattern_lower in text_lower:
                # Find pattern position
                start = text_lower.find(pattern_lower)
                # Extract value after pattern
                value_start = start + len(pattern_lower)
                value = text[value_start:value_start+50].strip()  # Take next 50 characters as value

                # Clean value
                value = self._clean_extracted_value(value)

                # Apply post-processing if specified
                if field.post_process:
                    value = self._apply_post_process(field.post_process, value)

                confidence = 85.0  # Default confidence for pattern matching
                bbox = None
                return value, confidence, bbox

        # Try NLP entity recognition
        if self.nlp and field.entity_type:
            value, confidence, bbox = self._extract_by_entity_type(field, text)
            if value and field.post_process:
                value = self._apply_post_process(field.post_process, value)
            return value, confidence, bbox

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
        """Clean extracted value - improved for Chinese text"""
        if not value:
            return ""

        # For numeric values, be more careful about what we remove
        # Only remove trailing punctuation, not internal separators
        value = value.strip()

        # Check if this looks like a number (contains digits)
        if re.search(r'\d', value):
            # For numeric strings, only remove trailing non-numeric chars
            # But keep internal punctuation that might be part of numbers
            # Include Chinese punctuation marks
            trailing_chars = "。；，:：\n\t"
            for char in trailing_chars:
                if value.endswith(char):
                    value = value.rstrip(char)
                    break
        else:
            # For text strings (including Chinese), remove common end characters
            # Be more careful with Chinese text - don't split on common Chinese punctuation
            stop_chars = "。；，,.;:：\n\t"
            for char in stop_chars:
                if char in value:
                    value = value.split(char)[0]
                    break

        return value.strip()

    def _apply_post_process(self, post_process_func: str, value: str) -> str:
        """Apply post-processing function to extracted value"""
        if not value:
            return value

        func_map = {
            "amount_normalize": self._normalize_amount,
            "date_normalize": self._normalize_date,
        }

        func = func_map.get(post_process_func)
        if func:
            return func(value)
        else:
            # Unknown post-process function, return as-is
            return value

    def _normalize_amount(self, value: str) -> str:
        """Normalize amount values"""
        if not value:
            return value

        # Remove currency symbols and extra spaces
        value = re.sub(r'[￥$€£¥]', '', value)
        value = re.sub(r'[,\s]', '', value)

        # Try to convert to float and format
        try:
            # Handle decimal separators
            if ',' in value and '.' in value:
                # European format like 1.234,56
                if value.rfind(',') > value.rfind('.'):
                    value = value.replace('.', '').replace(',', '.')
                else:
                    value = value.replace(',', '')
            elif ',' in value:
                # Could be thousand separator or decimal
                if len(value.split(',')[-1]) <= 2:
                    value = value.replace(',', '.')
                else:
                    value = value.replace(',', '')

            amount = float(value)
            return f"{amount:.2f}"
        except ValueError:
            return value

    def _normalize_date(self, value: str) -> str:
        """Normalize date values"""
        if not value:
            return value

        # Common date patterns
        patterns = [
            (r'(\d{4})[-年](\d{1,2})[-月](\d{1,2})日?', r'\1-\2-\3'),  # YYYY-MM-DD or YYYY年MM月DD日
            (r'(\d{1,2})/(\d{1,2})/(\d{4})', r'\3-\1-\2'),  # MM/DD/YYYY -> YYYY-MM-DD
            (r'(\d{4})/(\d{1,2})/(\d{1,2})', r'\1-\2-\3'),  # YYYY/MM/DD
        ]

        for pattern, replacement in patterns:
            match = re.search(pattern, value)
            if match:
                try:
                    year, month, day = match.groups()
                    # Ensure valid date format
                    year = year.zfill(4)
                    month = month.zfill(2)
                    day = day.zfill(2)
                    return f"{year}-{month}-{day}"
                except:
                    continue

        return value
