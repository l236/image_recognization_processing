import json
import streamlit as st
from pathlib import Path
import tempfile
import os
import pandas as pd

# Import from the core modules
from doc_parser.core.processor import DocumentProcessor
from doc_parser.core.ocr import OCRConfig
from doc_parser.core.extractor import ExtractionConfig

# Batch Processing
def process_batch(folder_path: str, output_dir: str, ocr_config: OCRConfig, extraction_config: ExtractionConfig):
    from doc_parser.core.processor import DocumentProcessorConfig, ValidationConfig

    # Create processor with default validation config
    validation_config = ValidationConfig()
    processor_config = DocumentProcessorConfig(ocr=ocr_config, extraction=extraction_config, validation=validation_config)
    processor = DocumentProcessor(processor_config)

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
    threshold = 80  # Default threshold for batch processing
    for res in results:
        for field in res['extracted_fields']:
            if field['confidence'] < threshold:
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

    # Sidebar for configuration
    st.sidebar.header("⚙️ Configuration")

    # OCR Engine Selection
    ocr_engine = st.sidebar.selectbox(
        "OCR Engine",
        ["paddle", "pytesseract", "google_vision"],
        index=0,
        help="Choose OCR engine. PaddleOCR is the default with excellent quality. Tesseract is fast. Google Vision requires API setup."
    )

    # Load existing config
    try:
        with open("config.json", 'r', encoding='utf-8') as f:
            config_data = json.load(f)
    except FileNotFoundError:
        config_data = {
            "ocr": {"engine": "paddle"},
            "extraction": {"enable_adaptive_fields": True, "fields": []},
            "validation": {"confidence_threshold": 0.7}
        }

    # Create processor with current configuration
    from doc_parser.core.processor import DocumentProcessorConfig, ValidationConfig

    # Update config with current settings
    config_data['ocr']['engine'] = ocr_engine

    ocr_config = OCRConfig(**config_data['ocr'])
    extraction_config = ExtractionConfig(**config_data['extraction'])
    validation_config = ValidationConfig(**config_data.get('validation', {}))

    processor_config = DocumentProcessorConfig(ocr=ocr_config, extraction=extraction_config, validation=validation_config)
    processor = DocumentProcessor(processor_config)

    uploaded_file = st.file_uploader("Upload file", type=['jpg', 'png', 'pdf'])

    if uploaded_file:
        # Save uploaded file temporarily
        temp_path = f"/tmp/{uploaded_file.name}"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        result = processor.process_file(temp_path)

        st.subheader("Raw Text")
        st.text_area("OCR Result", result.raw_text, height=200)

        st.subheader("Extracted Fields & Manual Correction")

        # Create editable table for all fields
        corrected_fields = {}

        # Group fields by name to handle duplicates
        field_groups = {}
        for i, field in enumerate(result.extracted_fields):
            if field.value and field.value.strip():  # Only show fields with values
                field_key = f"{field.name}_{i}"  # Make key unique
                if field.name not in field_groups:
                    field_groups[field.name] = []
                field_groups[field.name].append((i, field))

        # Display fields grouped by name
        for field_name, field_list in field_groups.items():
            # Show the best (highest confidence) field for each name
            best_field = max(field_list, key=lambda x: x[1].confidence)[1]

            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1, 2])

            with col1:
                count = len(field_list)
                display_name = f"**{field_name}**"
                if count > 1:
                    display_name += f" ({count} variants)"
                st.write(display_name)

            with col2:
                # Editable text input for field name/key
                corrected_name = st.text_input(
                    f"Key for {field_name}",
                    value=field_name,
                    key=f"name_{field_name}",
                    label_visibility="collapsed"
                )

            with col3:
                # Editable text input for field value
                corrected_value = st.text_input(
                    f"Value for {field_name}",
                    value=best_field.value,
                    key=f"value_{field_name}",
                    label_visibility="collapsed"
                )

            with col4:
                confidence_color = "🟢" if best_field.confidence >= 80 else "🟡" if best_field.confidence >= 60 else "🔴"
                st.write(f"{confidence_color} {best_field.confidence:.0f}%")

            with col5:
                if best_field.confidence < 70:
                    st.write("⚠️ Needs review")
                else:
                    st.write("✅ Good")

            # Store both name and value corrections
            if field_name not in corrected_fields:
                corrected_fields[field_name] = {}
            corrected_fields[field_name]['name'] = corrected_name
            corrected_fields[field_name]['value'] = corrected_value

        # Action buttons
        col1, col2 = st.columns(2)

        with col1:
            if st.button("🔄 Regenerate with Corrections", type="primary"):
                # Update fields with corrections (both names and values)
                for field in result.extracted_fields:
                    if field.name in corrected_fields:
                        corrections = corrected_fields[field.name]
                        field.name = corrections['name']  # Update field name/key
                        field.value = corrections['value']  # Update field value
                        field.confidence = 100.0  # Manual corrections get 100% confidence

                result.low_confidence_fields = []
                st.success("✅ Fields updated with corrections!")

                # Show updated JSON
                st.subheader("Updated JSON Output")
                st.json(result.model_dump())

        with col2:
            if st.button("� Download JSON"):
                st.download_button(
                    "Download structured JSON",
                    data=result.model_dump_json(indent=2),
                    file_name="structured_output.json",
                    mime="application/json"
                )

if __name__ == "__main__":
    main()
