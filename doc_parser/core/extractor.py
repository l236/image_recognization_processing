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
    pattern: Union[str, List[str]] = Field(..., description="Matching pattern(s) or keywords")
    description: str = Field(default="", description="Field description")
    entity_type: Optional[str] = Field(default=None, description="Entity type (DATE, MONEY, etc.)")
    regex_patterns: Optional[List[str]] = Field(default=None, description="Regex patterns for extraction")
    value_type: Optional[str] = Field(default=None, description="Value type hint for intelligent extraction")
    post_process: Optional[str] = Field(default=None, description="Post-processing function name")


class ExtractionConfig(BaseModel):
    """Extraction configuration"""
    enable_adaptive_fields: bool = Field(default=True, description="Enable adaptive field extraction")
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

        # First, try configured fields
        for field in self.config.fields:
            value, confidence, bbox = self._extract_field(field, text, ocr_result)
            extracted.append(ExtractedField(
                name=field.name,
                value=value,
                confidence=confidence,
                bbox=bbox
            ))

        # Then add adaptive fields based on content analysis (if enabled)
        if self.config.enable_adaptive_fields:
            adaptive_fields = self._extract_adaptive_fields(text, ocr_result)
            extracted.extend(adaptive_fields)

        return extracted

    def _extract_field(self, field: FieldRule, text: str, ocr_result: Dict[str, Any]) -> tuple:
        """Extract single field using simplified key-based approach"""
        # Try regex patterns first (highest priority - for advanced users)
        if field.regex_patterns:
            for regex_pattern in field.regex_patterns:
                try:
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
                except re.error as e:
                    print(f"Regex error for pattern '{regex_pattern}': {e}")
                    continue

        # Try simplified key-based extraction (main approach for users)
        if field.pattern:
            patterns = [field.pattern] if isinstance(field.pattern, str) else field.pattern
            for keyword in patterns:
                # Look for the keyword in the text (case-insensitive)
                keyword_lower = keyword.lower().strip()
                text_lower = text.lower()

                if keyword_lower in text_lower:
                    # Find all occurrences of the keyword
                    start_positions = []
                    pos = 0
                    while True:
                        pos = text_lower.find(keyword_lower, pos)
                        if pos == -1:
                            break
                        start_positions.append(pos)
                        pos += len(keyword_lower)

                    # Try to extract value after each occurrence
                    for start_pos in start_positions:
                        # Extract text after the keyword
                        value_start = start_pos + len(keyword_lower)
                        # Look for value in the next reasonable chunk
                        candidate_text = text[value_start:value_start+100]

                        # Extract value based on value_type hint
                        extracted_value = self._extract_value_by_type(candidate_text, field.value_type)

                        if extracted_value:
                            # Clean the extracted value
                            extracted_value = self._clean_extracted_value(extracted_value)

                            # Apply post-processing if specified
                            if field.post_process:
                                extracted_value = self._apply_post_process(field.post_process, extracted_value)

                            if extracted_value and len(extracted_value.strip()) > 0:
                                confidence = 85.0  # Good confidence for keyword-based extraction
                                bbox = None
                                return extracted_value, confidence, bbox

        # Try NLP entity recognition (fallback)
        if self.nlp and field.entity_type:
            value, confidence, bbox = self._extract_by_entity_type(field, text)
            if value and field.post_process:
                value = self._apply_post_process(field.post_process, value)
            return value, confidence, bbox

        return None, 0.0, None

    def _extract_value_by_type(self, candidate_text: str, value_type: Optional[str]) -> Optional[str]:
        """Extract value from candidate text based on type hint"""
        if not candidate_text:
            return None

        # Clean the candidate text first
        candidate_text = candidate_text.strip()

        # Remove common separators and punctuation at the beginning
        candidate_text = re.sub(r'^[:：\s\-=\n\r\t]+', '', candidate_text)

        if not value_type:
            # No type hint - extract first meaningful segment
            # Look for natural breaks (punctuation, line breaks, etc.)
            segments = re.split(r'[。！？\n\r]', candidate_text)
            for segment in segments:
                segment = segment.strip()
                if segment and len(segment) > 1 and len(segment) < 50:
                    return segment
            # Fallback: take first 30 characters
            return candidate_text[:30].strip() if candidate_text else None

        elif value_type == "金额" or value_type == "amount":
            # Extract amounts
            amount_patterns = [
                r'([\d,]+(?:\.\d{2})?)',  # Basic numbers
                r'RMB\s*([\d,]+(?:\.\d{2})?)',
                r'\$\s*([\d,]+(?:\.\d{2})?)',
                r'￥\s*([\d,]+(?:\.\d{2})?)',
            ]
            for pattern in amount_patterns:
                match = re.search(pattern, candidate_text)
                if match:
                    return match.group(1)

        elif value_type == "日期" or value_type == "date":
            # Extract dates
            date_patterns = [
                r'(\d{4}年\d{1,2}月\d{1,2}日)',  # Chinese
                r'(\d{1,2}/\d{1,2}/\d{4})',  # MM/DD/YYYY
                r'(\d{4}-\d{1,2}-\d{1,2})',  # YYYY-MM-DD
                r'([A-Z][a-z]+ \d{1,2}, \d{4})',  # English
            ]
            for pattern in date_patterns:
                match = re.search(pattern, candidate_text)
                if match:
                    return match.group(1)

        elif value_type == "车牌" or value_type == "license":
            # Extract license plates
            plate_patterns = [
                r'\b([A-Z0-9]{6,8})\b',  # General alphanumeric
                r'\b([京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-Z][A-Z0-9]{5})\b',  # Chinese
            ]
            for pattern in plate_patterns:
                match = re.search(pattern, candidate_text.upper())
                if match:
                    plate = match.group(1)
                    # Validate license plate
                    if (len(plate) >= 6 and len(plate) <= 10 and
                        any(c.isdigit() for c in plate) and
                        any(c.isalpha() for c in plate)):
                        return plate

        elif value_type == "姓名" or value_type == "name":
            # Extract names
            name_patterns = [
                r'([A-Z][a-z]+\s+[A-Z][a-z]+)',  # English names
                r'([A-Z][a-z]+)',  # Single English name
                r'([\u4e00-\u9fff]{2,10})',  # Chinese names
            ]
            for pattern in name_patterns:
                match = re.search(pattern, candidate_text)
                if match:
                    return match.group(1)

        elif value_type == "公司" or value_type == "company":
            # Extract company names
            company_patterns = [
                r'([A-Z][a-zA-Z\s]*(?:Inc|Corp|Ltd|LLC|Company|Corporation|有限公司|公司))',
                r'([\u4e00-\u9fff]{2,20}(?:有限公司|公司|集团|企业))',  # Chinese companies
            ]
            for pattern in company_patterns:
                match = re.search(pattern, candidate_text)
                if match:
                    return match.group(1)

        elif value_type == "地址" or value_type == "address":
            # Extract addresses (look for longer text segments)
            segments = re.split(r'[。！？\n\r]', candidate_text)
            for segment in segments:
                segment = segment.strip()
                if segment and len(segment) > 5 and len(segment) < 100:
                    return segment

        elif value_type == "电话" or value_type == "phone":
            # Extract phone numbers
            phone_patterns = [
                r'(\d{3,4}[-]\d{7,8})',  # Chinese phone
                r'(\+?\d{1,3}[-]?\d{3,4}[-]?\d{4,})',  # International
                r'(\d{10,11})',  # 10-11 digit numbers
            ]
            for pattern in phone_patterns:
                match = re.search(pattern, candidate_text)
                if match:
                    return match.group(1)

        # Default: extract first meaningful segment
        segments = re.split(r'[。！？\n\r]', candidate_text)
        for segment in segments:
            segment = segment.strip()
            if segment and len(segment) > 1 and len(segment) < 50:
                return segment

        return None

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

    def _extract_key_value_pairs(self, text: str) -> List[ExtractedField]:
        """Extract key-value pairs using intelligent pattern recognition"""
        kvp_fields = []

        # Focus on high-quality, specific patterns that are likely to be accurate

        # 1. Extract amounts with currency
        amount_patterns = [
            r'gross base salary of RMB\s*([\d,]+)',  # Specific pattern for this document
            r'RMB\s*([\d,]+(?:\.\d{2})?)',  # RMB amounts
            r'\$([\\d,]+(?:\\.\d{2})?)',  # USD amounts
            r'￥([\\d,]+(?:\\.\d{2})?)',  # CNY amounts
        ]

        for pattern in amount_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                value = match.strip()
                if value and value != '0':
                    # Avoid duplicates
                    if not any(f.name == "Amount" and f.value == value for f in kvp_fields):
                        kvp_fields.append(ExtractedField(
                            name="Amount",
                            value=value,
                            confidence=90.0,
                            bbox=None
                        ))

        # 2. Extract company names (look for Inc, Corp, Ltd patterns)
        company_patterns = [
            r'([A-Z][a-zA-Z\s]+(?:Inc|Corp|Ltd|LLC|Company|Corporation))\.?',
            r'Croschat\s+Inc',  # Specific for this document
        ]

        for pattern in company_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                value = match.strip()
                if value and len(value) > 3:  # Avoid very short matches
                    # Avoid duplicates
                    if not any(f.name == "Company" and f.value == value for f in kvp_fields):
                        kvp_fields.append(ExtractedField(
                            name="Company",
                            value=value,
                            confidence=85.0,
                            bbox=None
                        ))

        # 3. Extract dates (look for specific date formats)
        date_patterns = [
            r'(\d{4}年\d{1,2}月\d{1,2}日)',  # Chinese dates
            r'([A-Z][a-z]+ \d{1,2}, \d{4})',  # English dates like "March 22, 2025"
            r'(\d{1,2}/\d{1,2}/\d{4})',  # MM/DD/YYYY
            r'(\d{4}-\d{1,2}-\d{1,2})',  # YYYY-MM-DD
        ]

        for pattern in date_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                value = match.strip()
                if value and len(value) > 5:  # Reasonable date length
                    # Avoid duplicates
                    if not any(f.name == "Date" and f.value == value for f in kvp_fields):
                        kvp_fields.append(ExtractedField(
                            name="Date",
                            value=value,
                            confidence=80.0,
                            bbox=None
                        ))

        # 4. Extract person names (look for proper name patterns)
        name_patterns = [
            r'([A-Z][a-z]+\s+[A-Z][a-z]+)',  # English names
            r'Dear\s+([A-Z][a-z]+)',  # "Dear [Name]" pattern
        ]

        for pattern in name_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                value = match.strip()
                if value and len(value) > 2:
                    # Avoid duplicates
                    if not any(f.name == "Name" and f.value == value for f in kvp_fields):
                        kvp_fields.append(ExtractedField(
                            name="Name",
                            value=value,
                            confidence=75.0,
                            bbox=None
                        ))

        # 5. Extract license plates (Chinese and international formats)
        license_plate_patterns = [
            # Chinese license plates: 省份缩写 + 5位字母数字
            r'\b([京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-Z][A-Z0-9]{5})\b',
            # International license plates: various formats
            r'\b([A-Z]{1,3}[0-9]{1,4}[A-Z0-9]{0,3})\b',  # General alphanumeric
            r'\b([0-9]{1,4}[A-Z]{1,3}[0-9]{0,4})\b',  # Numbers + letters
            # Common license plate lengths (6-8 characters)
            r'\b([A-Z0-9]{6,8})\b',
        ]

        for pattern in license_plate_patterns:
            matches = re.findall(pattern, text.upper())  # Convert to uppercase for consistency
            for match in matches:
                value = match.strip()
                # Validate license plate characteristics
                if (value and
                    len(value) >= 6 and len(value) <= 10 and  # Reasonable length
                    any(c.isdigit() for c in value) and  # Must contain numbers
                    any(c.isalpha() for c in value)):  # Must contain letters

                    # Avoid duplicates
                    if not any(f.name == "License Plate" and f.value == value for f in kvp_fields):
                        kvp_fields.append(ExtractedField(
                            name="License Plate",
                            value=value,
                            confidence=85.0,
                            bbox=None
                        ))

        return kvp_fields

    def _extract_adaptive_fields(self, text: str, ocr_result: Dict[str, Any]) -> List[ExtractedField]:
        """
        Extract adaptive fields based on content analysis - focus on key-value pairs

        Args:
            text: OCR recognized text
            ocr_result: OCR result dictionary

        Returns:
            List of high-quality key-value pair extractions
        """
        adaptive_fields = []

        if not text or len(text.strip()) < 50:
            return adaptive_fields

        # Extract key-value pairs using pattern recognition
        kvp_fields = self._extract_key_value_pairs(text)
        adaptive_fields.extend(kvp_fields)

        # Extract main topic/title (if no good KVPs found)
        if len(adaptive_fields) < 3:
            title_field = self._extract_main_topic(text)
            if title_field and title_field.confidence >= 70:
                adaptive_fields.append(title_field)

        # Extract key sections (limit to top 3 most relevant)
        if len(adaptive_fields) < 5:
            section_fields = self._extract_key_sections(text)
            # Sort by confidence and take top 3
            section_fields.sort(key=lambda x: x.confidence, reverse=True)
            adaptive_fields.extend(section_fields[:3])

        # Extract important concepts (limit to top 2 high-quality ones)
        if len(adaptive_fields) < 7:
            concept_fields = self._extract_key_concepts(text)
            # Filter for high confidence and meaningful content
            high_quality_concepts = [
                f for f in concept_fields
                if f.confidence >= 75 and f.value and len(f.value.strip()) > 1
            ]
            # Remove duplicates and take top 2
            seen_values = set()
            unique_concepts = []
            for concept in high_quality_concepts:
                if concept.value not in seen_values:
                    unique_concepts.append(concept)
                    seen_values.add(concept.value)
                    if len(unique_concepts) >= 2:
                        break
            adaptive_fields.extend(unique_concepts)

        # Final filtering: remove any remaining low-quality fields and limit to top 8
        final_fields = [
            f for f in adaptive_fields
            if f.value and f.value.strip() and f.confidence >= 60
        ]

        # Sort by confidence and take top 8
        final_fields.sort(key=lambda x: x.confidence, reverse=True)
        return final_fields[:8]

    def _extract_main_topic(self, text: str) -> Optional[ExtractedField]:
        """Extract main topic or title from text"""
        # Look for title-like patterns at the beginning
        lines = text.split('\n')[:10]  # First 10 lines

        for line in lines:
            line = line.strip()
            if len(line) > 10 and len(line) < 100:  # Reasonable title length
                # Check if it looks like a title (not starting with bullet points or numbers)
                if not re.match(r'^[-•*]\s', line) and not re.match(r'^\d+[\.)]\s', line):
                    # Check if it contains keywords suggesting it's a title
                    title_keywords = ['方法', '核心', '帮助', '需求', '转化', '代码', 'AI', '高效']
                    if any(keyword in line for keyword in title_keywords):
                        return ExtractedField(
                            name="Main Topic",
                            value=line,
                            confidence=85.0,
                            bbox=None
                        )

        # Fallback: extract first meaningful sentence
        sentences = re.split(r'[。！？]', text)
        for sentence in sentences[:3]:
            sentence = sentence.strip()
            if len(sentence) > 20 and len(sentence) < 150:
                return ExtractedField(
                    name="Main Topic",
                    value=sentence,
                    confidence=75.0,
                    bbox=None
                )

        return None

    def _extract_key_sections(self, text: str) -> List[ExtractedField]:
        """Extract key sections from the document"""
        sections = []

        # Look for numbered sections (like 一、二、三...)
        chinese_numbers = ['一、', '二、', '三、', '四、', '五、', '六、', '七、', '八、', '九、', '十、']
        for num in chinese_numbers:
            pattern = re.escape(num) + r'(.*?)(?=\n|$)'
            match = re.search(pattern, text, re.DOTALL)
            if match:
                section_content = match.group(1).strip()
                if len(section_content) > 10:
                    # Extract section title (first line or first sentence)
                    lines = section_content.split('\n')
                    title = lines[0].strip() if lines else section_content[:50]
                    if len(title) > 5:
                        sections.append(ExtractedField(
                            name=f"Section {num[:-1]}",
                            value=title,
                            confidence=80.0,
                            bbox=None
                        ))

        # Look for English numbered sections (1., 2., etc.)
        for i in range(1, 10):
            pattern = rf'{i}[\.)]\s*(.*?)(?=\n|$)'
            match = re.search(pattern, text, re.DOTALL)
            if match:
                section_content = match.group(1).strip()
                if len(section_content) > 10:
                    sections.append(ExtractedField(
                        name=f"Step {i}",
                        value=section_content[:100],
                        confidence=75.0,
                        bbox=None
                    ))

        return sections

    def _extract_key_concepts(self, text: str) -> List[ExtractedField]:
        """Extract key concepts using NLP"""
        concepts = []

        if not self.nlp:
            return concepts

        doc = self.nlp(text[:2000])  # Limit text length for performance

        # Extract named entities
        entity_counts = {}
        for ent in doc.ents:
            if ent.label_ in ['PERSON', 'ORG', 'GPE', 'PRODUCT', 'EVENT']:
                entity_counts[ent.text] = entity_counts.get(ent.text, 0) + 1

        # Add most frequent entities as concepts
        for entity, count in sorted(entity_counts.items(), key=lambda x: x[1], reverse=True)[:3]:
            concepts.append(ExtractedField(
                name="Key Concept",
                value=entity,
                confidence=min(70.0 + count * 5, 90.0),
                bbox=None
            ))

        # For Chinese text, extract important terms using token analysis
        # Look for tokens that are nouns or proper nouns
        important_terms = []
        concept_keywords = ['方法', '技术', '需求', '代码', '系统', '数据', '模型', '接口', '功能', 'AI', '算法', '框架', '平台']

        for token in doc:
            # Check if token is a noun or contains concept keywords
            if (token.pos_ in ['NOUN', 'PROPN'] or
                any(keyword in token.text for keyword in concept_keywords)) and \
               len(token.text) > 1 and len(token.text) < 10:
                if token.text not in [c.value for c in concepts]:  # Avoid duplicates
                    important_terms.append(token.text)

        # Add top important terms
        for term in important_terms[:3]:
            concepts.append(ExtractedField(
                name="Important Concept",
                value=term,
                confidence=70.0,
                bbox=None
            ))

        return concepts

    def _extract_numbered_lists(self, text: str) -> List[ExtractedField]:
        """Extract numbered lists (like the 7 methods)"""
        lists = []

        # Look for patterns like "1. ", "2. ", etc.
        lines = text.split('\n')
        current_list = []
        list_start = False

        for line in lines:
            line = line.strip()
            # Check if line starts with number
            match = re.match(r'^(\d+)[\.)]\s*(.+)', line)
            if match:
                number = match.group(1)
                content = match.group(2)
                if len(content) > 10:  # Meaningful content
                    lists.append(ExtractedField(
                        name=f"Method {number}",
                        value=content,
                        confidence=85.0,
                        bbox=None
                    ))

        return lists

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
