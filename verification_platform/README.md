# BeneBridge Document Verification Platform

Simple, secure document verification platform running on localhost:5008

## Features

- ✅ **Death Certificate Verification**
  - OCR extraction (pytesseract or AWS Textract)
  - Washington State-specific validation rules
  - Blockchain hash verification (Titan Seal)
  - Rule-based confidence scoring

- ✅ **ID Verification**
  - Persona API integration
  - Government ID verification for all 50 states
  - Liveness detection
  - Fraud detection

- ✅ **100% Private**
  - All processing on localhost
  - No data leaves your machine (except API calls you configure)
  - Documents stored locally only

## Quick Start

### 1. Install Dependencies

```bash
cd verification_platform
pip install flask flask-cors pillow pytesseract pdf2image requests boto3
```

### 2. Install Tesseract OCR (for local death cert verification)

**macOS:**
```bash
brew install tesseract
```

**Linux:**
```bash
sudo apt-get install tesseract-ocr
```

### 3. Set Up API Keys (Optional)

#### Persona (ID Verification) - **RECOMMENDED**
```bash
export PERSONA_API_KEY='your_persona_api_key'
export PERSONA_TEMPLATE_ID='itmpl_...'  # From Persona dashboard
```

Sign up: https://withpersona.com/
Cost: ~$1-3 per verification

#### AWS Textract (Death Certificate OCR) - Optional
```bash
export AWS_ACCESS_KEY_ID='your_access_key'
export AWS_SECRET_ACCESS_KEY='your_secret_key'
export AWS_REGION='us-east-1'
```

Cost: $0.015 per page

### 4. Run the Platform

```bash
python3 app_verification.py
```

Open: http://localhost:5008

## Washington State Death Certificate Rules

The system validates WA death certificates against these rules:

### Required Fields
- Deceased name
- Date of death
- County of death
- Certificate number (Format: `YYYY-COUNTY-#####`)
- State file number (8 digits)
- Registrar signature

### Validation Rules
1. ✅ Certificate number matches pattern: `^\d{4}-[A-Z]+-\d+$`
2. ✅ State file number is 8 digits
3. ✅ County is valid WA county (39 counties recognized)
4. ✅ Date of death not in future
5. ✅ All required fields present
6. ✅ Proper form number: DOH 422-006

## API Options Comparison

### ID Verification

| API | Cost | Features | Recommendation |
|-----|------|----------|----------------|
| **Persona** | $1-3/verification | Best UX, liveness detection, fraud detection | ✅ Recommended |
| Onfido | $2-4/verification | Enterprise-grade, 195+ countries | Good for international |
| Stripe Identity | $1.50/verification | Simple, good if using Stripe | Good alternative |

### Death Certificate OCR

| API | Cost | Features | Recommendation |
|-----|------|----------|----------------|
| **AWS Textract** | $0.015/page | Excellent form recognition, key-value pairs | ✅ Recommended |
| Azure Form Recognizer | $0.01/page | Good for structured documents | Good alternative |
| Google Document AI | $0.015/page | Custom training available | Advanced use cases |
| **pytesseract (local)** | FREE | Runs locally, no API calls | ✅ Privacy-focused |

## Blockchain Verification

### Titan Seal Integration

1. Upload death certificate to Titan Seal: https://titanseal.io
2. Get blockchain hash
3. Enter hash in verification form
4. System verifies document authenticity via blockchain

## Workflow

1. **Upload Documents**
   - Death certificate (PDF or image)
   - Government-issued ID (PDF or image)
   - Optional: Blockchain hash from Titan Seal

2. **Click "Verify Documents"**

3. **View Results**
   - Confidence score (0-100)
   - Status (verified/needs_review/failed)
   - Detailed validation breakdown
   - Extracted data

## File Structure

```
verification_platform/
├── app_verification.py          # Main Flask app
├── death_cert_verifier.py       # WA death cert verification logic
├── id_verifier_persona.py       # Persona API integration
├── templates/
│   ├── verification_upload.html # Upload interface
│   └── verification_results.html # Results dashboard
├── uploads/                     # Uploaded files (local only)
│   ├── death_certs/
│   └── ids/
└── verification_platform.db     # SQLite database
```

## Security & Privacy

- ✅ All files stored locally in `uploads/` directory
- ✅ Database is local SQLite
- ✅ No external API calls without your explicit configuration
- ✅ You control all API keys
- ✅ Can run completely offline with local OCR
- ✅ Files hashed for integrity verification

## Development Mode

The platform runs in debug mode by default for easy testing:
- Auto-reloads on code changes
- Detailed error messages
- Runs on `0.0.0.0:5008` (accessible from network)

## Production Considerations

Before deploying:
1. Set `debug=False` in `app_verification.py`
2. Use production WSGI server (gunicorn, uwsgi)
3. Add authentication
4. Use HTTPS
5. Set strong SECRET_KEY
6. Configure proper file size limits

## Troubleshooting

**"No OCR method available"**
- Install pytesseract: `brew install tesseract`
- Or configure AWS Textract

**"PERSONA_API_KEY not set"**
- Sign up at https://withpersona.com/
- Export API key: `export PERSONA_API_KEY='your_key'`

**"Upload failed"**
- Check file format (PDF, PNG, JPG only)
- Check file size (max 16MB)

## Next Steps

1. Test with synthetic documents first
2. Configure Persona API for real ID verification
3. Optionally configure AWS Textract for better OCR
4. Set up Titan Seal for blockchain verification
5. Test with your real documents (100% private on localhost)
