# BeneBridge Verification Services

Production-ready implementation of Chapter 5 verification microservices architecture.

## Architecture Overview

This folder contains the verification layer microservices that implement the core processing logic described in Chapter 5, Section 4.2 of the dissertation.

```
verification_services/
├── common/                    # Shared models and utilities
│   ├── models.py             # Data classes for verification results
│   └── __init__.py
│
├── death_cert_verification/   # Death Certificate Verification Service
│   ├── blockchain_verifier.py    # Blockchain pathway (Titan Seal)
│   ├── traditional_verifier.py   # Traditional pathway (OCR + CV)
│   └── __init__.py
│
├── id_verification/           # ID Document Verification Service
│   ├── document_analyzer.py      # Document authenticity checking
│   ├── facial_recognition.py    # Biometric matching
│   └── __init__.py
│
├── fraud_detection/           # Fraud Detection Service
│   ├── ml_fraud_detector.py     # Machine learning fraud models
│   ├── rule_based_detector.py   # Rule-based fraud signals
│   └── __init__.py
│
├── document_intelligence/     # Document Intelligence Service
│   ├── pdf_processor.py          # PDF parsing and extraction
│   ├── image_processor.py        # Image quality and analysis
│   └── __init__.py
│
└── workflow_orchestration/    # Workflow Orchestration Service
    ├── workflow_engine.py        # Dynamic workflow generation
    ├── task_router.py            # Intelligent case routing
    └── __init__.py
```

## Services Implemented

### 1. Death Certificate Verification (`death_cert_verification/`)

Implements Chapter 5, Section 4.5.2-4.5.3 with dual verification pathways:

#### Blockchain Pathway (`blockchain_verifier.py`)
- **Purpose**: Verify California Titan Seal certificates anchored on Ethereum blockchain
- **Processing Time**: <5 seconds
- **Confidence**: 100% (cryptographic certainty)
- **Key Features**:
  - Hash extraction from PDF metadata or QR code
  - Ethereum mainnet transaction validation
  - Certificate data hash verification
  - PKI digital signature validation
  - Timestamp reasonableness checking
  - Revocation list verification

**Example Usage**:
```python
from death_cert_verification.blockchain_verifier import BlockchainVerifier

verifier = BlockchainVerifier(ethereum_endpoint="https://mainnet.infura.io/v3/YOUR-KEY")
result = verifier.verify_death_certificate(
    pdf_path="path/to/death_cert.pdf",
    expected_deceased_name="John Smith"
)

print(f"Status: {result.status}")
print(f"Confidence: {result.confidence_score}%")
print(f"Method: {result.method}")
print(f"Time: {result.processing_time_ms}ms")
```

#### Traditional Pathway (`traditional_verifier.py`)
- **Purpose**: Verify physical death certificates using multi-layer analysis
- **Processing Time**: 2-10 seconds
- **Confidence**: 0-100% (composite score)
- **Key Features**:
  - Computer vision quality assessment (resolution, clarity, completeness)
  - Security feature detection (watermarks, seals, holograms)
  - Tampering detection (JPEG artifacts, font inconsistencies, lighting analysis)
  - OCR data extraction (Tesseract)
  - Rule-based validation (certificate format, field completeness, cross-field consistency)
  - SSDI cross-reference integration
  - Fuzzy name matching (Levenshtein, Soundex, nickname database)

**Example Usage**:
```python
from death_cert_verification.traditional_verifier import TraditionalVerifier

verifier = TraditionalVerifier()
result = verifier.verify_death_certificate(
    pdf_path="path/to/death_cert.pdf",
    expected_deceased_name="John Smith",
    expected_ssn="123-45-6789"
)

print(f"Quality Score: {result.details['quality_metrics']['overall_quality_score']}")
print(f"Confidence: {result.confidence_score}%")
print(f"Status: {result.status}")
```

### 2. ID Verification (`id_verification/`)

**Status**: Folder created, implementation pending

Implements Chapter 5 identity verification:
- Driver's license/state ID document analysis
- Biometric facial matching
- AAMVA database integration
- Liveness detection (anti-spoofing)

### 3. Fraud Detection (`fraud_detection/`)

**Status**: Folder created, implementation pending

Implements Chapter 5 fraud detection:
- Multi-layer fraud signal detection
- Machine learning anomaly detection
- Relationship fraud detection (e.g., suspicious beneficiaries)
- Velocity checks (multiple claims)
- Sanctions list screening (OFAC, PEP)

### 4. Document Intelligence (`document_intelligence/`)

**Status**: Folder created, implementation pending

Implements Chapter 5 document processing:
- PDF parsing and text extraction
- Image quality enhancement
- Multi-page document handling
- Document classification

### 5. Workflow Orchestration (`workflow_orchestration/`)

**Status**: Folder created, implementation pending

Implements Chapter 5 workflow management:
- Dynamic workflow generation (account-type specific)
- Parallel task execution
- ML-based case routing (XGBoost)
- SLA tracking and escalation

## Common Models (`common/models.py`)

Shared data structures used across all services:

### `VerificationResult`
Standard verification output structure:
```python
@dataclass
class VerificationResult:
    status: VerificationStatus          # VERIFIED, NEEDS_REVIEW, FAILED, PENDING
    confidence_score: float             # 0-100
    method: VerificationMethod          # BLOCKCHAIN, TRADITIONAL, etc.
    processing_time_ms: float
    timestamp: datetime
    details: Dict                       # Service-specific details
    error_message: Optional[str]
```

### `DeathCertificateData`
Extracted death certificate information:
```python
@dataclass
class DeathCertificateData:
    deceased_name: str
    deceased_ssn: Optional[str]
    date_of_birth: Optional[str]
    date_of_death: str
    place_of_death: str
    certificate_number: str
    issuing_state: str
    blockchain_hash: Optional[str]
```

### `DocumentQualityMetrics`
Image quality assessment:
```python
@dataclass
class DocumentQualityMetrics:
    resolution_dpi: int
    clarity_score: float                 # 0-100
    completeness_score: float            # 0-100
    has_security_features: bool
    detected_tampering: bool
    overall_quality_score: float         # 0-100
```

## Dependencies

### Required Python Packages

```bash
# PDF Processing
PyPDF2>=3.0.0
pdf2image>=1.16.0
pdfplumber>=0.9.0

# OCR
pytesseract>=0.3.10
Pillow>=9.0.0

# Computer Vision
opencv-python>=4.7.0
numpy>=1.24.0

# Blockchain (for production)
web3>=6.0.0

# Machine Learning (future)
scikit-learn>=1.2.0
xgboost>=1.7.0

# Fuzzy Matching (future)
jellyfish>=0.11.0
```

### System Dependencies

```bash
# Tesseract OCR
brew install tesseract        # macOS
apt-get install tesseract-ocr # Linux

# Poppler (for pdf2image)
brew install poppler          # macOS
apt-get install poppler-utils # Linux
```

## Integration with Core Banking Platform

The core banking platform (`core_banking_platform/app_core_banking.py`) currently uses simulated verification. To integrate real verification:

```python
# Replace simulate_document_verification() with:
from verification_services.death_cert_verification.blockchain_verifier import BlockchainVerifier
from verification_services.death_cert_verification.traditional_verifier import TraditionalVerifier

def verify_document(document_path, document_type, case_data):
    """Real document verification"""

    if document_type == 'death_certificate':
        # Try blockchain first
        blockchain_verifier = BlockchainVerifier()
        result = blockchain_verifier.verify_death_certificate(
            document_path,
            case_data['deceased_name']
        )

        # If not blockchain certificate, use traditional
        if result.status == VerificationStatus.PENDING:
            traditional_verifier = TraditionalVerifier()
            result = traditional_verifier.verify_death_certificate(
                document_path,
                case_data['deceased_name'],
                case_data.get('deceased_ssn')
            )

        return result.to_dict()

    # Add other document types (ID, beneficiary form, etc.)
```

## Performance Targets (per Chapter 5)

| Service | Target Response Time | Throughput |
|---------|---------------------|------------|
| Blockchain Verification | < 5 seconds | 1000+ concurrent |
| Traditional Verification | < 10 seconds | 500+ concurrent |
| ID Verification | < 3 seconds | 1000+ concurrent |
| Fraud Detection | < 200ms | 5000+ concurrent |

## Testing with Synthetic Data

The synthetic data in `synthetic_cases/` contains PDFs that can be tested with these services. Note that since the PDFs are synthetically generated, certain features (blockchain hashes, security features) are simulated.

To test:

```python
# Test blockchain verifier
from verification_services.death_cert_verification.blockchain_verifier import BlockchainVerifier

verifier = BlockchainVerifier()
result = verifier.verify_death_certificate(
    "synthetic_cases/CNB-2026-1039/death_certificate.pdf",
    "Kendra Dawson"
)
print(result.to_dict())

# Test traditional verifier
from verification_services.death_cert_verification.traditional_verifier import TraditionalVerifier

verifier = TraditionalVerifier()
result = verifier.verify_death_certificate(
    "synthetic_cases/CNB-2026-1039/death_certificate.pdf",
    "Kendra Dawson",
    "933-24-1623"
)
print(result.to_dict())
```

## Production Deployment Notes

### Blockchain Verification
- Requires Ethereum node access (Infura, Alchemy, or self-hosted)
- Need API key for blockchain provider
- Consider caching blockchain lookups to reduce API costs
- Implement circuit breaker for blockchain service outages

### Traditional Verification
- Tesseract OCR requires significant CPU resources
- Consider GPU acceleration for computer vision
- Implement result caching for frequently verified documents
- Use async processing for multiple documents

### SSDI Integration
- Requires commercial SSDI API subscription or government access
- Implement rate limiting per API tier
- Cache SSDI lookups (with TTL for updates)

### Scalability
- Deploy as independent microservices (Docker containers)
- Use message queue (RabbitMQ, Kafka) for async processing
- Implement horizontal scaling with load balancer
- Use Redis for distributed caching

## Future Enhancements

1. **ML-Based Quality Assessment**
   - Train CNN on 10K+ authentic certificates (per Chapter 5)
   - Implement authenticity score model
   - Active learning to improve over time

2. **Advanced OCR**
   - Upgrade to commercial OCR (ABBYY, Amazon Textract)
   - Layout analysis for complex documents
   - Handwriting recognition

3. **Multi-Language Support**
   - Support for non-English certificates
   - International date format handling

4. **Audit Trail**
   - Detailed logging of all verification steps
   - Compliance reporting
   - Performance monitoring

## License

Internal use only. Part of BeneBridge dissertation research project.
