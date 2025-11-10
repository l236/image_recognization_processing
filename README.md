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

### Method 3: Using Conda (Recommended)

For better dependency management and reproducibility, especially with the computer vision libraries used in this project:

1. Install Miniconda or Anaconda if not already installed:
```bash
# macOS
brew install --cask miniconda

# Or download from https://docs.conda.io/en/latest/miniconda.html
```

2. Create and activate the conda environment:
```bash
# Create environment from the provided environment.yml
conda env create -f environment.yml

# Activate the environment
conda activate image_recognization_processing
```

3. Install the package in development mode:
```bash
pip install -e .
```

4. **Required**: Download spaCy models using the setup script:
```bash
python setup_spacy.py
```
This script will automatically download and verify the required Chinese and English spaCy models.

### System Dependencies

#### 1. Install spaCy Models (Required)
```bash
# Install spaCy first
pip install spacy==3.7.2

# Download Chinese model (primary, required for Chinese document processing)
python -m spacy download zh_core_web_sm

# Download English model (fallback, recommended)
python -m spacy download en_core_web_sm

# Verify installation
python -c "import spacy; nlp = spacy.load('zh_core_web_sm'); print('✅ Chinese model loaded successfully')"
```

#### 2. Install Tesseract OCR (Optional - for fallback)
```bash
# macOS
brew install tesseract tesseract-lang

# Ubuntu
sudo apt-get install tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-eng

# Windows
# Download installer: https://github.com/UB-Mannheim/tesseract/wiki
```

#### 3. Google Vision API (Recommended for Chinese documents)
For superior Chinese OCR performance, set up Google Cloud Vision API:

1. **Follow the setup guide**: See `GOOGLE_VISION_SETUP.md`
2. **Test the setup**: Run `python test_google_vision.py`
3. **Update config.json** to use Google Vision

**Benefits:**
- ✅ **90%+ accuracy** on Chinese contracts (vs 4.8% with Tesseract)
- ✅ **2-5 second** processing (vs 18+ seconds)
- ✅ **Production-ready** for business use

#### 4. Baidu Cloud OCR (Excellent for Chinese)
For superior Chinese OCR performance with competitive pricing, use Baidu Cloud OCR:

1. **Install Baidu SDK**: `pip install baidu-aip`
2. **Run setup script**: `python setup_baidu_ocr.py`
3. **Follow the prompts** to enter your Baidu AI credentials
4. **Update config.json** to use Baidu OCR: `"engine": "baidu_cloud"`

**Benefits:**
- ✅ **95%+ accuracy** on Chinese documents
- ✅ **Free quota**: 5,000 calls/day
- ✅ **Low cost**: ¥0.005/call (~$0.0007)
- ✅ **Fast processing**: < 1 second per image
- ✅ **Enterprise-grade** reliability

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
# Start FastAPI service
python -m doc_parser.api.service
# Service will start on http://localhost:8000
```

### Web Interface

```bash
# Start Streamlit web interface
streamlit run main.py
# Interface will open in browser at http://localhost:8501
```

#### Features:
- **🎯 Custom Field Configuration**: Define extraction fields directly in the web interface
- **⚙️ OCR Engine Selection**: Switch between Tesseract and Google Vision
- **📤 Drag-and-Drop Upload**: Process documents with a simple upload
- **🔧 Manual Correction**: Edit extracted values and regenerate JSON
- **💾 Configuration Management**: Save and load field configurations

#### Custom Field Setup:
1. **Open the sidebar** in the web interface
2. **Expand "➕ Add Custom Field"**
3. **Choose your approach**:

   **简单模式 (Recommended)**:
   - Field Name (e.g., "公司名称")
   - Search Keywords (每行一个): `公司`, `Company`, `甲方`
   - Value Type Hint (optional): `公司`, `金额`, `日期`, `车牌`, etc.

   **高级模式 (Advanced)**:
   - Use regex patterns for precise control
   - Entity recognition for NLP-based extraction

4. **Save your configuration** for reuse

#### Example Configurations:

**公司名称**:
- 关键词: `公司`, `Company`, `甲方`, `vendor`
- 类型提示: `公司`

**金额**:
- 关键词: `金额`, `salary`, `工资`, `total`
- 类型提示: `金额`

**车牌**:
- 关键词: `车牌`, `license`, `plate`
- 类型提示: `车牌`

**Note**: The web interface currently uses Tesseract OCR. For superior Chinese text recognition, enable Google Vision API billing and change `"engine": "pytesseract"` to `"engine": "google_vision"` in `config.json`.

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
    "enable_adaptive_fields": true,
    "fields": []
  }
}
```

**Note**: Set `fields` to an empty array `[]` to enable fully adaptive field extraction. The system will automatically generate high-quality, relevant fields based on document content analysis, including:

- **Main Topic**: Primary subject of the document
- **Key Sections**: Important structural elements
- **Important Concepts**: Technical terms and entities
- **Methods/Steps**: Numbered lists and procedures

The system intelligently limits output to the most relevant fields (typically 10-15 high-quality fields per document).

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

- **OCR**: pytesseract, google-cloud-vision, baidu-aip
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
