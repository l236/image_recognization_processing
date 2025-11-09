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

    # Load configs from file
    with open("config.json", 'r', encoding='utf-8') as f:
        config_data = json.load(f)

    from doc_parser.core.processor import DocumentProcessorConfig, ValidationConfig

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
                data=result.model_dump_json(indent=2),
                file_name="structured_output.json",
                mime="application/json"
            )

if __name__ == "__main__":
    main()
