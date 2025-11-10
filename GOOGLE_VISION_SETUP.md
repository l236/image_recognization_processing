# 🚀 Google Vision API Setup for Chinese Document Processing

## Why Google Vision API?

**Current Problem:**
- Tesseract OCR: **4.8% accuracy** on Chinese contracts
- Processing time: **18+ seconds** per page
- Poor Chinese character recognition

**Google Vision Solution:**
- **90%+ accuracy** on Chinese text
- **2-5 seconds** processing time
- Superior Chinese character recognition
- Production-ready for business use

## 📋 Step-by-Step Setup Guide

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Note your **Project ID** (e.g., `my-doc-parser-project`)

### Step 2: Enable Vision API

1. In Google Cloud Console, go to **APIs & Services** > **Library**
2. Search for **"Cloud Vision API"**
3. Click **Enable**

### Step 3: Create Service Account

1. Go to **APIs & Services** > **Credentials**
2. Click **+ CREATE CREDENTIALS** > **Service Account**
3. Fill in:
   - **Service account name**: `doc-parser-vision`
   - **Display name**: `Document Parser Vision API`
   - **Description**: `OCR service for document processing`
4. Click **CREATE AND CONTINUE**
5. Skip roles for now, click **DONE**

### Step 4: Generate Credentials Key

1. In the **Credentials** page, find your service account
2. Click the **⋮** menu > **Manage keys**
3. Click **ADD KEY** > **Create new key**
4. Select **JSON** format
5. Click **CREATE**

**Important**: Save the downloaded `credentials.json` file securely!

### Step 5: Grant Permissions

Run this command in your terminal (replace `YOUR_PROJECT_ID`):

```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:doc-parser-vision@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/editor"
```

Or manually in Google Cloud Console:
1. Go to **IAM & Admin** > **IAM**
2. Find your service account
3. Add **Editor** role

### Step 6: Set Up Environment

1. **Move credentials file** to your project directory:
   ```bash
   mv ~/Downloads/credentials.json /path/to/your/project/
   ```

2. **Set environment variable**:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/project/credentials.json"
   ```

3. **Make it permanent** (add to your shell profile):
   ```bash
   echo 'export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/project/credentials.json"' >> ~/.zshrc
   source ~/.zshrc
   ```

### Step 7: Update Configuration

Update your `config.json`:

```json
{
  "ocr": {
    "engine": "google_vision",
    "google_credentials_path": "/path/to/your/project/credentials.json"
  }
}
```

### Step 8: Test Setup

Run the test:

```bash
cd /path/to/your/project
python3 -c "
from doc_parser.core.ocr import OCREngine, OCRConfig
config = OCRConfig(engine='google_vision', google_credentials_path='credentials.json')
ocr = OCREngine(config)
print('✅ Google Vision API setup successful!')
"
```

## 🧪 Testing with Chinese Contract

```python
from doc_parser import DocumentParserClient

# Initialize with Google Vision
client = DocumentParserClient()

# Test Chinese contract
result = client.process_file('test_files/李康佳合同.pdf')
print(f'OCR Confidence: {result[\"overall_confidence\"]:.1f}%')
print(f'Extracted fields: {len(result[\"extracted_fields\"])}')
```

## 📊 Expected Results

**Before (Tesseract):**
- Accuracy: 4.8%
- Time: 18+ seconds
- Quality: Gibberish text

**After (Google Vision):**
- Accuracy: 90%+
- Time: 2-5 seconds
- Quality: Clear Chinese text

## 💰 Pricing

Google Vision API pricing:
- **First 1,000 pages/month**: Free
- **Additional pages**: $1.50 per 1,000 pages
- **Very cost-effective** for business use

## 🔧 Troubleshooting

### "Credentials not found"
```bash
# Check environment variable
echo $GOOGLE_APPLICATION_CREDENTIALS

# Verify file exists
ls -la $GOOGLE_APPLICATION_CREDENTIALS
```

### "Permission denied"
- Ensure service account has **Editor** role
- Check Vision API is enabled for your project

### "API not enabled"
- Go to Google Cloud Console
- Enable **Cloud Vision API** for your project

## 🎯 Next Steps

Once Google Vision is set up:

1. **Test with your Chinese contracts**
2. **Compare results** with Tesseract
3. **Fine-tune extraction patterns** if needed
4. **Deploy to production**

## 📞 Support

If you encounter issues:
1. Check the [Google Cloud Vision documentation](https://cloud.google.com/vision/docs)
2. Verify your service account permissions
3. Test with the provided credentials validation script

---

**🎉 Ready for professional Chinese document processing!**
