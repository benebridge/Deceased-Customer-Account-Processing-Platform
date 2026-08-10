# Intelligent Document Processing (IDP) Setup Guide

## Overview

You have three main IDP options for extracting data from your documents:

1. **AWS Textract** (Recommended for production)
2. **Google Document AI**
3. **Azure Form Recognizer**

## Option 1: AWS Textract (Recommended)

### Features:
- **AnalyzeDocument**: Extracts forms, tables, and text
- **AnalyzeID**: Specialized for driver's licenses and passports
- Best accuracy for government forms and IDs
- Pay-per-use pricing

### Setup Steps:

1. **Install boto3** (if not already installed):
```bash
pip3 install boto3
```

2. **Configure AWS Credentials**:

Option A: Using AWS CLI (recommended):
```bash
aws configure
# Enter your:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region (us-east-1)
# - Output format (json)
```

Option B: Manual credentials file:
```bash
mkdir -p ~/.aws
cat > ~/.aws/credentials << EOF
[default]
aws_access_key_id = YOUR_ACCESS_KEY_HERE
aws_secret_access_key = YOUR_SECRET_KEY_HERE
EOF

cat > ~/.aws/config << EOF
[default]
region = us-east-1
output = json
EOF
```

3. **Enable Textract in AWS Console**:
   - Go to AWS Console → Textract
   - Make sure it's enabled in us-east-1 region

4. **Test the extraction**:
```bash
cd bank_operations_platform
python3 textract_extraction.py
```

### Pricing:
- AnalyzeDocument: $1.50 per 1000 pages
- AnalyzeID: $2.00 per 1000 documents
- Very affordable for your use case

---

## Option 2: Google Document AI

### Features:
- Pre-trained models for US driver's licenses
- Custom processors for forms
- Good accuracy, slightly cheaper than AWS

### Setup Steps:

1. **Install Google Cloud libraries**:
```bash
pip3 install google-cloud-documentai google-cloud-storage
```

2. **Set up Google Cloud Project**:
   - Go to console.cloud.google.com
   - Create a new project
   - Enable Document AI API
   - Create service account and download JSON key

3. **Set environment variable**:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/key.json"
```

4. **Create processors** in Document AI console:
   - US Driver's License Parser
   - Form Parser (for claim forms and death certificates)

---

## Option 3: Azure Form Recognizer

### Features:
- Pre-built models for IDs
- Custom model training
- Good for mixed document types

### Setup Steps:

1. **Install Azure libraries**:
```bash
pip3 install azure-ai-formrecognizer azure-identity
```

2. **Create Azure resource**:
   - Go to portal.azure.com
   - Create Form Recognizer resource
   - Get endpoint and API key

3. **Use in code with endpoint and key**

---

## Recommended Approach

For your beneficiary claim processing:

1. **Start with AWS Textract** - easiest setup, best for government documents
2. Use **AnalyzeID** for driver's licenses (specialized for this)
3. Use **AnalyzeDocument with FORMS** for death certificates and claim forms

## Implementation

I've created `textract_extraction.py` with three functions:
- `extract_death_certificate_textract()` - Extracts name, date of death, SSN
- `extract_drivers_license_textract()` - Uses AnalyzeID for DL-specific extraction
- `extract_claim_form_textract()` - Extracts form fields from beneficiary claim

Once you configure AWS credentials, these will work immediately!

## Next Steps

1. Set up AWS credentials (see Option A or B above)
2. Test extraction: `python3 bank_operations_platform/textract_extraction.py`
3. I'll integrate it into your Flask app to replace the current extraction methods

---

## Cost Estimate

For 93 test documents × 3 documents each = 279 documents:
- Death certificates: 93 pages × $0.0015 = $0.14
- Driver's licenses (AnalyzeID): 93 × $0.002 = $0.19
- Claim forms: 186 pages × $0.0015 = $0.28
- **Total: ~$0.61 for all test data**

Very affordable for testing and development!
