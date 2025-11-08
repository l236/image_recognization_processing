# OCR and Structured Extraction Integrated Tool

Intelligent document recognition and structured extraction tool that supports text recognition in images/PDFs, combining rules and NLP to convert unstructured text into standardized JSON.

## Features

- **Multi-format Input Support**: Single images (JPG/PNG), image-based PDFs, mixed text-image PDFs
- **OCR Recognition Optimization**:
  - Custom dictionary support to improve professional terminology recognition accuracy
  - Automatic tilt correction for images (≤30° tilt can be corrected)
  - Watermark/noise interference removal
- **Structured Extraction**:
  - Extract key information according to JSON configuration field rules
  - Entity recognition using spaCy (dates, amounts, phone numbers)
- **Confidence Level Grading**:
  - Each extracted field is marked with confidence (0-100)
  - Fields ≤80% are included in "manual verification list"
- **Visualization Interface**: Streamlit interface supports manual modification and regeneration of structured results
- **Batch Processing**: Automatic recognition + structuring of all files in folders

## Installation

### Method 1: Install from Source

1. Clone the project:
```bash
git clone https://github.com/l236/image_recognization_processing.git
cd image_recognization_processing
```

2. Install the package:
```bash
pip install -e .
```

### Method 2: Direct Installation

```bash
pip install git+https://github.com/l236/image_recognization_processing.git
```

### System Dependencies

1. Install spaCy Chinese model:
```bash
python -m spacy download zh_core_web_sm
```

2. Install Tesseract OCR:
```bash
# macOS
brew install tesseract tesseract-lang

# Ubuntu
sudo apt-get install tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-eng

# Windows
# Download installer: https://github.com/UB-Mannheim/tesseract/wiki
```

## Usage

### Python API Usage

```python
from doc_parser import DocumentParserClient

# Initialize client
client = DocumentParserClient()

# Process single file
result = client.process_file("document.pdf")
print(result)

# Batch process directory
results = client.process_directory("input_dir", "output_dir")
```

### Command Line Tools

#### Batch Processing
```bash
# Use default configuration
doc-parser-batch input_folder output_folder

# Use custom configuration
doc-parser-batch input_folder output_folder --config custom_config.json
```

#### API Service
```bash
# Start HTTP API service
doc-parser-api

# Service will start on http://localhost:8000
```

### Web Interface

```bash
# Start Streamlit interface
pip install streamlit
streamlit run main.py
```

### HTTP API

After starting the API service, you can use it through HTTP requests:

```bash
# Process file
curl -X POST "http://localhost:8000/process/file" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@document.pdf"

# Health check
curl http://localhost:8000/health
```

## Configuration

### Configuration File Format

Create a `config.json` file:

```json
{
  "ocr": {
    "engine": "pytesseract",
    "custom_words": ["invoice", "contract", "amount", "date"],
    "lang": "chi_sim+eng",
    "google_credentials_path": null
  },
  "extraction": {
    "fields": [
      {
        "name": "Invoice Number",
        "pattern": "invoice number",
        "description": "Invoice number field"
      },
      {
        "name": "Amount",
        "pattern": "total",
        "description": "Amount field"
      },
      {
        "name": "Date",
        "pattern": "date",
        "description": "Date field",
        "entity_type": "DATE"
      }
    ]
  }
}
```

### Environment Variable Configuration

```bash
# OCR engine selection
export DOC_PARSER_OCR_ENGINE=pytesseract

# Google Vision credentials
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# Custom dictionary
export DOC_PARSER_CUSTOM_WORDS="invoice,contract,amount,date"
```

## Output Format

- **Structured JSON**: `filename_structured.json`
  ```json
  {
    "filename": "document.pdf",
    "raw_text": "Complete OCR text...",
    "extracted_fields": [
      {
        "name": "Invoice Number",
        "value": "123456789",
        "confidence": 95.0,
        "bbox": [10, 20, 100, 30]
      }
    ],
    "low_confidence_fields": [],
    "overall_confidence": 92.5
  }
  ```

- **OCR Raw Text**: `filename_raw.txt`
- **Validation List**: `validation_list.csv`

## API Reference

### DocumentParserClient

#### Methods

- `process_file(file_path)` - Process single file
- `process_files(file_paths)` - Batch process files
- `process_directory(input_dir, output_dir)` - Process directory
- `extract_text(file_path)` - Extract text only
- `update_config(ocr_config, extraction_config)` - Update configuration

### HTTP API Endpoints

- `POST /process/file` - Process single file
- `POST /process/files` - Batch process files
- `POST /extract/text` - Extract text only
- `GET /config` - Get configuration
- `PUT /config` - Update configuration
- `GET /health` - Health check

## Integration Examples

### Django Project Integration

```python
# settings.py
DOC_PARSER_CONFIG = {
    "ocr": {"engine": "pytesseract"},
    "extraction": {
        "fields": [
            {"name": "Invoice Number", "pattern": "invoice number"}
        ]
    }
}

# views.py
from doc_parser import DocumentParserClient

def process_document(request):
    client = DocumentParserClient(config_dict=DOC_PARSER_CONFIG)
    result = client.process_file(request.FILES['document'])
    return JsonResponse(result)
```

### FastAPI Integration

```python
from fastapi import FastAPI, File, UploadFile
from doc_parser import DocumentParserClient

app = FastAPI()
client = DocumentParserClient()

@app.post("/process")
async def process_document(file: UploadFile = File(...)):
    # Save temporary file
    with open(f"/tmp/{file.filename}", "wb") as f:
        f.write(await file.read())

    result = client.process_file(f"/tmp/{file.filename}")
    return result
```

## Technology Stack

- **OCR**: pytesseract, google-cloud-vision
- **Structured**: pydantic, spaCy
- **Image Processing**: OpenCV, Pillow
- **PDF Processing**: pdf2image, pdfplumber
- **Web Frameworks**: FastAPI, Streamlit
- **Data Processing**: pandas, numpy

## Performance Metrics

- Recognition accuracy: Clear documents ≥98%, blurry documents ≥85%
- Structured completeness: Configured field extraction coverage ≥90%
- Processing speed: Single page PDF < 3 seconds (hardware dependent)

## License

MIT License

## Contributing

Welcome to submit Issues and Pull Requests!

## Contact

Project maintainer: Document Parser Team
