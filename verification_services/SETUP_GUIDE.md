# API Setup Guide for BeneBridge Verification Services

## 1. Persona (ID Verification)

### What is Persona?
Persona provides identity verification with:
- Government ID verification (driver's licenses, passports, state IDs)
- Liveness detection (selfie verification)
- Database verification (AAMVA for driver's licenses)
- Fraud detection

### Setup Steps:

1. **Create Persona Account**
   - Go to https://withpersona.com
   - Click "Get Started" or "Request Demo"
   - Sign up for a sandbox/test account (free for development)

2. **Get API Keys**
   - Log into Persona Dashboard
   - Navigate to "Developers" → "API Keys"
   - Create a new API key (you'll get both Sandbox and Production keys)
   - Copy your API key - format: `persona_sandbox_...` or `persona_production_...`

3. **Configure Environment**
   ```bash
   # Add to your .env file:
   PERSONA_API_KEY=persona_sandbox_XXXXXXXXXXXXX
   PERSONA_TEMPLATE_ID=itmpl_XXXXXXXXXXXXX  # (optional - for specific verification flows)
   ```

4. **Installation**
   ```bash
   pip install persona-python
   # or
   pip install requests  # if using REST API directly
   ```

### Persona Pricing (as of 2024):
- **Sandbox**: Free for testing
- **Production**: ~$1-3 per verification (volume discounts available)
- **Government ID Verification**: ~$1.50 per check
- **Selfie + Liveness**: Additional ~$0.50

---

## 2. AWS Textract (Death Certificate OCR)

### What is AWS Textract?
AWS Textract is an ML-powered OCR service that:
- Extracts text from documents (printed and handwritten)
- Identifies form fields and tables
- Processes structured documents (forms, certificates, etc.)
- Supports PDF and image formats

### Setup Steps:

1. **Create AWS Account**
   - Go to https://aws.amazon.com
   - Click "Create an AWS Account"
   - Follow signup process (requires credit card, but has free tier)

2. **Create IAM User with Textract Access**
   ```
   a. Log into AWS Console
   b. Go to IAM → Users → Add User
   c. User name: "benebridge-textract-user"
   d. Access type: "Programmatic access" (this gives you API keys)
   e. Permissions: Attach "AmazonTextractFullAccess" policy
   f. Create user and SAVE the credentials:
      - Access Key ID: AKIA...
      - Secret Access Key: (only shown once - download CSV!)
   ```

3. **Configure AWS Credentials**

   **Option A: Environment Variables** (recommended for development)
   ```bash
   # Add to your .env file:
   AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
   AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
   AWS_REGION=us-west-2  # Choose closest region
   ```

   **Option B: AWS Credentials File**
   ```bash
   # Create ~/.aws/credentials file:
   [default]
   aws_access_key_id = AKIAIOSFODNN7EXAMPLE
   aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
   ```

4. **Installation**
   ```bash
   pip install boto3  # AWS SDK for Python
   ```

### AWS Textract Pricing:
- **Free Tier**: 1,000 pages/month for first 3 months
- **After Free Tier**:
  - Detect Document Text: $1.50 per 1,000 pages
  - Analyze Document (forms/tables): $50 per 1,000 pages
- **Estimated cost for BeneBridge**: ~$0.05 per death certificate

---

## 3. Testing Your Setup

### Test Persona Connection:
```python
import os
from persona import Client

client = Client(api_key=os.getenv('PERSONA_API_KEY'))

# Test API connection
inquiry = client.inquiries.create(
    inquiry_template_id=os.getenv('PERSONA_TEMPLATE_ID'),
    reference_id='test-inquiry-001'
)
print(f"Persona connection successful! Inquiry ID: {inquiry.id}")
```

### Test AWS Textract Connection:
```python
import boto3
import os

# Initialize Textract client
textract = boto3.client(
    'textract',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION', 'us-west-2')
)

# Test with a simple text detection
with open('test_image.png', 'rb') as document:
    response = textract.detect_document_text(
        Document={'Bytes': document.read()}
    )

print(f"AWS Textract connection successful!")
print(f"Detected {len(response['Blocks'])} text blocks")
```

---

## 4. Security Best Practices

### API Key Management:
- ✅ **DO**: Store keys in `.env` file (add to `.gitignore`)
- ✅ **DO**: Use environment variables
- ✅ **DO**: Rotate keys regularly (every 90 days)
- ❌ **DON'T**: Commit keys to Git
- ❌ **DON'T**: Share keys in screenshots or chat
- ❌ **DON'T**: Use production keys in development

### Create `.env` file:
```bash
# .env (add this file to .gitignore!)

# Persona
PERSONA_API_KEY=persona_sandbox_XXXXXXXXXXXXX
PERSONA_TEMPLATE_ID=itmpl_XXXXXXXXXXXXX

# AWS Textract
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-west-2

# Database
DATABASE_URL=sqlite:///benebridge.db
```

### Load environment variables in Python:
```python
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Access variables
persona_key = os.getenv('PERSONA_API_KEY')
aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
```

---

## 5. Next Steps After Setup

Once you have your API keys:

1. **Update verification code** to use real APIs instead of mock data
2. **Test with sandbox/test data** first
3. **Process your Washington death certificate** with Textract locally
4. **Verify your ID** with Persona
5. **Monitor costs** in AWS/Persona dashboards

---

## Questions?

- **Persona Support**: https://docs.withpersona.com
- **AWS Textract Docs**: https://docs.aws.amazon.com/textract/
- **Cost Calculator**: https://calculator.aws/

---

## Estimated Monthly Costs (Low Volume):

| Service | Volume | Cost |
|---------|--------|------|
| Persona ID Verification | 10-50 verifications | $15-75/month |
| AWS Textract | 10-50 certificates | $0.50-2.50/month |
| **Total** | | **~$15-80/month** |

For higher volumes (1000+ verifications/month), negotiate enterprise pricing with Persona.
