# BeneBridge POC - Intelligent Document Processing for Beneficiary Claims

A proof-of-concept system demonstrating automated beneficiary claim processing using Intelligent Document Processing (IDP) with AWS Textract, Flask web applications, and comprehensive document verification.

## Overview

BeneBridge automates the verification and processing of beneficiary claims for financial institutions. The system uses AWS Textract for document extraction, cross-document verification, and database validation to streamline what is traditionally a manual, time-consuming process.

### Key Features

- **Intelligent Document Processing (IDP)** using AWS Textract
  - Death Certificate extraction (name, date of death, SSN)
  - Driver's License verification using AnalyzeID API
  - Beneficiary Claim Form parsing

- **Automated Cross-Document Verification**
  - Validates consistency across all submitted documents
  - Checks beneficiary identity against driver's license
  - Verifies deceased information matches death certificate

- **Database Integration**
  - Checks against DMF (Death Master File) mock database
  - Validates financial account information
  - Confirms beneficiary relationships and percentages

- **Professional Banking UI**
  - Clean, modern interface for bank operations
  - Real-time processing status updates
  - Automated approval document generation (PDF)

## Project Structure

```
BeneBridgePOC/
├── bank_operations_platform/     # Main application
│   ├── app.py                    # Flask backend with Textract integration
│   ├── textract_extraction.py   # AWS Textract extraction functions
│   ├── templates/
│   │   └── index.html           # Professional banking UI
│   └── uploads/                 # Temporary upload directory
│
├── Cases/                        # Test cases (93 realistic scenarios)
│   └── Case_IRA-001-1_*/        # Each case contains:
│       ├── Death_Cert_*.pdf     # Death certificate
│       ├── CA_DL_*.png          # Driver's license
│       └── Claim_Form_*.pdf     # Beneficiary claim form
│
├── mock_databases/               # Mock database generators and scripts
│   ├── create_person_lists.py   # Generate mock person data
│   ├── generate_ca_driver_licenses.py  # Generate test documents
│   └── *.csv, *.json            # Reference data files
│
├── requirements.txt              # Python dependencies
├── .gitignore                    # Git ignore rules
├── .env.example                  # Environment configuration template
├── AWS_CREDENTIAL_SETUP.md       # AWS Textract setup guide
└── IDP_SETUP_GUIDE.md           # IDP configuration options
```

## Prerequisites

### System Requirements
- **Python 3.8+**
- **pip** (Python package manager)
- **Homebrew** (macOS) or appropriate package manager for your OS
- **poppler** (for PDF to image conversion)

### AWS Account
- AWS account with Textract enabled
- IAM user with `AmazonTextractFullAccess` policy
- AWS credentials configured (Access Key ID and Secret Access Key)

## Installation

### 1. Clone the Repository

```bash
git clone <your-github-repo-url>
cd BeneBridgePOC
```

### 2. Install System Dependencies

#### macOS:
```bash
brew install poppler
```

#### Ubuntu/Debian:
```bash
sudo apt-get install poppler-utils
```

#### Windows:
Download poppler from: http://blog.alivate.com.au/poppler-windows/

### 3. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 4. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure AWS Credentials

#### Option A: Using AWS CLI (Recommended)

```bash
# Install AWS CLI if not already installed
brew install awscli  # macOS
# or: pip install awscli

# Configure credentials
aws configure
```

You'll be prompted for:
- **AWS Access Key ID**: Your access key from IAM
- **AWS Secret Access Key**: Your secret key from IAM
- **Default region name**: `us-east-1`
- **Default output format**: `json`

#### Option B: Manual Configuration

Create credentials file:
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

**See [AWS_CREDENTIAL_SETUP.md](AWS_CREDENTIAL_SETUP.md) for detailed step-by-step instructions.**

### 6. Initialize Databases

```bash
# Generate mock databases
cd mock_databases
python3 create_person_lists.py
python3 generate_ca_driver_licenses.py
cd ..
```

### 7. Verify Installation

Test AWS Textract connection:
```bash
cd bank_operations_platform
python3 textract_extraction.py
```

You should see extraction results from test documents.

## Running the Application

### Bank Operations Platform (Main Application)

```bash
cd bank_operations_platform
python3 app.py
```

The application will start on **http://localhost:5009**

### Using the Application

1. **Open your browser** to http://localhost:5009
2. **Upload three documents**:
   - Death Certificate (PDF)
   - Driver's License (PDF/PNG/JPG)
   - Beneficiary Claim Form (PDF)
3. **Click "Process Claim"**
4. **Review automated verification results**:
   - Document extraction results
   - Cross-document verification
   - Database validation
   - Fraud checks
   - Final approval status
5. **Download approval document** (if approved)

### Test with Sample Cases

Use the pre-generated test cases in the `Cases/` directory:

```bash
# Example: Case IRA-001-1_018_Thompson_Karen
Cases/Case_IRA-001-1_018_Thompson_Karen/
├── Death_Cert_Thompson_Jennifer.pdf
├── CA_DL_018_Thompson_Karen.png
└── Claim_Form_IRA-001-1_018_Thompson_Karen.pdf
```

## AWS Textract Pricing

Textract uses pay-per-use pricing:
- **AnalyzeDocument**: $1.50 per 1,000 pages
- **AnalyzeID** (for driver's licenses): $2.00 per 1,000 documents

**Free Tier**: 1,000 pages/month for the first 3 months

### Cost Estimate for Testing
For 93 test cases (279 documents total):
- Death certificates: 93 pages × $0.0015 = **$0.14**
- Driver's licenses: 93 documents × $0.002 = **$0.19**
- Claim forms: 186 pages × $0.0015 = **$0.28**
- **Total: ~$0.61**

## Project Components

### Bank Operations Platform (`bank_operations_platform/`)
The single, focused application for automated beneficiary claim processing:

**Main Files:**
- **app.py**: Flask backend with AWS Textract integration, cross-document verification, and database validation
- **textract_extraction.py**: Document extraction functions for death certificates, driver's licenses, and claim forms
- **templates/index.html**: Professional banking operations UI with real-time status updates

**Key Features:**
- Automated document upload and processing
- Real-time extraction using AWS Textract
- Cross-document verification
- Database validation (DMF, financial accounts)
- Automated approval document generation (PDF)
- Professional banking operations interface

### Mock Databases (`mock_databases/`)
Scripts and data for simulating external verification sources:
- Person reference data (deceased individuals and beneficiaries)
- Document generation scripts
- Test data in CSV/JSON format

### Test Cases (`Cases/`)
93 realistic test scenarios, each containing:
- Death certificate (PDF)
- Driver's license (PNG)
- Beneficiary claim form (PDF)

## Key Technologies

- **Flask**: Web framework
- **AWS Textract**: Intelligent Document Processing
  - AnalyzeDocument API for forms
  - AnalyzeID API for driver's licenses
- **ReportLab**: PDF generation for approval documents
- **pdf2image**: PDF to image conversion
- **SQLite**: Database storage
- **Boto3**: AWS SDK for Python

## Development

### Running in Debug Mode

```bash
cd bank_operations_platform
python3 app.py
```

Flask runs with debug mode enabled by default, showing detailed error messages.

### Testing

```bash
# Run all tests
pytest

# Run specific test
pytest tests/test_extraction.py
```

### Code Quality

```bash
# Format code
black .

# Lint code
flake8 .
```

## Security Considerations

### Credentials
- **Never commit AWS credentials** to Git
- Use environment variables or AWS credentials file
- The `.gitignore` file excludes `.aws/` and `.env` files

### Data Privacy
- All test data is synthetic (no real PII)
- Documents are processed in memory when possible
- Uploaded files are stored temporarily and can be deleted after processing

### Production Deployment
For production use, consider:
- Using AWS Secrets Manager for credentials
- Implementing proper authentication/authorization
- Using HTTPS/TLS encryption
- Setting up proper logging and monitoring
- Using a production WSGI server (gunicorn included in requirements.txt)

## Documentation

- **[AWS_CREDENTIAL_SETUP.md](AWS_CREDENTIAL_SETUP.md)**: Step-by-step AWS configuration
- **[IDP_SETUP_GUIDE.md](IDP_SETUP_GUIDE.md)**: IDP options (Textract, Document AI, Form Recognizer)
- **[TECHNOLOGY_IMPROVEMENTS.md](TECHNOLOGY_IMPROVEMENTS.md)**: Future enhancements
- **[SYNTHETIC_VS_REAL.md](SYNTHETIC_VS_REAL.md)**: Data generation methodology

## Troubleshooting

### AWS Textract Issues

**Error: "Unable to locate credentials"**
```bash
# Verify credentials are configured
aws sts get-caller-identity

# If not working, reconfigure
aws configure
```

**Error: "SubscriptionRequiredException"**
- Go to AWS Console → Textract
- Enable the service in us-east-1 region

**Error: HTTP 413 (Request too large)**
- The code automatically converts PDFs to images to handle this
- If issues persist, reduce image DPI in `textract_extraction.py` (currently 200)

### PDF Conversion Issues

**Error: "poppler not found"**
```bash
# macOS
brew install poppler

# Ubuntu
sudo apt-get install poppler-utils
```

### Port Already in Use

```bash
# Find process using port 5009
lsof -ti:5009

# Kill the process
lsof -ti:5009 | xargs kill -9

# Restart the application
python3 app.py
```

## Contributing

This is a proof-of-concept for research purposes. If you'd like to contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is for research and educational purposes.

## Acknowledgments

- AWS Textract documentation and examples
- Flask documentation
- ReportLab PDF library
- The open-source community

## Contact

For questions or issues, please open an issue on GitHub.

---

**Built with** Python, Flask, AWS Textract, and modern web technologies.
