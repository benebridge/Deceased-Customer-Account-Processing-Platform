# BeneBridge Verification Services - Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   Core Banking Platform (Port 5007)                      │
│                          CRM Interface Layer                             │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      Verification Services API                           │
│                     (Microservices Architecture)                         │
└─────────────────────────────────────────────────────────────────────────┘
                                 │
                 ┌───────────────┼───────────────┐
                 ▼               ▼               ▼
┌─────────────────────┐  ┌─────────────┐  ┌─────────────────┐
│  Workflow           │  │   ML Case   │  │   Document      │
│  Orchestration      │  │   Router    │  │   Intelligence  │
└─────────────────────┘  └─────────────┘  └─────────────────┘
         │
         ├─── Generates Dynamic Workflow
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Parallel Task Execution                       │
├──────────────┬──────────────┬──────────────┬───────────────────┤
│ Death Cert   │ ID Verif     │ Fraud        │ Account-Specific  │
│ Verification │              │ Detection    │ Verifications     │
└──────────────┴──────────────┴──────────────┴───────────────────┘
```

## Layer 1: Workflow Orchestration

### Workflow Engine (`workflow_engine.py`)

**Purpose**: Dynamic workflow generation and parallel task execution

**Key Features**:
- Account-type specific workflow generation
- Dependency management between tasks
- Parallel task execution (up to 5 concurrent)
- SLA tracking and escalation
- Real-time progress monitoring

**Workflow Templates**:
```
1. Fast Track (Blockchain + Low Value)
   └─ Death Cert (Blockchain) → ID Verification → Fraud Check
   └─ Total Time: 5-15 seconds

2. Standard (Traditional Verification)
   └─ Death Cert (Traditional) → ID Verification → Fraud Check
   └─ Total Time: 30-60 seconds

3. High-Value (>$500k)
   └─ Death Cert → ID Verification → Enhanced Background Check
   └─ Multi-angle Facial → Fraud Detection → Compliance
   └─ Total Time: 2-5 minutes

4. Retirement Accounts (IRA, 401k)
   └─ Death Cert → ID Verification → Beneficiary Designation
   └─ Fraud Detection → Compliance
   └─ Total Time: 1-2 minutes

5. Trust/Estate (Complex)
   └─ Death Cert → ID Verification → Trust Document Verification
   └─ Fraud Detection → Legal Compliance → Manual Review
   └─ Total Time: 5-10 minutes
```

### ML Case Router (`ml_router.py`)

**Purpose**: Intelligent case routing using machine learning

**Features**:
- Predicts case complexity (0-100 score)
- Estimates processing time
- Routes to appropriate workflow
- Identifies risk factors
- Capacity planning and resource optimization

**Routing Categories**:
- `FAST_TRACK`: Simple, low-risk cases with blockchain verification
- `STANDARD`: Normal processing flow
- `ENHANCED`: High-value or moderate risk cases
- `MANUAL_REVIEW`: Complex or high-risk cases
- `URGENT`: Time-sensitive processing

**ML Model** (Production):
- Algorithm: XGBoost Classifier
- Features: 13 engineered features
- Training: Historical case outcomes
- Accuracy Target: >95%

## Layer 2: Death Certificate Verification

### Blockchain Verifier (`blockchain_verifier.py`)

**Purpose**: Verify California Titan Seal blockchain certificates

**Verification Steps**:
```
1. Extract blockchain hash from PDF
   ├─ Check PDF metadata
   └─ Scan for QR code

2. Validate hash format
   └─ 0x + 64 hexadecimal characters

3. Ethereum transaction validation
   ├─ Query Ethereum mainnet
   ├─ Verify transaction exists
   └─ Check transaction age (<10 years)

4. Cryptographic validation (5 checks)
   ├─ Certificate data hash matches blockchain
   ├─ PKI digital signature verification
   ├─ Timestamp reasonableness
   ├─ Revocation list checking
   └─ Issuer authority validation

5. Extract certificate data
   └─ Deceased name, DOD, certificate number

6. Verify name match
   └─ Fuzzy matching algorithm (>85% similarity)

Result: 100% confidence if all checks pass (<5 seconds)
```

**Dependencies**:
- Web3.py for Ethereum interaction
- PyPDF2 for PDF processing
- pyzbar for QR code scanning

### Traditional Verifier (`traditional_verifier.py`)

**Purpose**: Verify physical death certificates (non-blockchain)

**Verification Steps**:
```
1. Convert PDF to images (300+ DPI)

2. Computer Vision Assessment
   ├─ Resolution check (300 DPI minimum)
   ├─ Clarity (Laplacian blur detection)
   ├─ Completeness (4 corners visible)
   ├─ Security features (watermarks, seals)
   └─ Tampering detection (JPEG artifacts)

3. OCR Data Extraction
   ├─ Tesseract OCR
   ├─ Name extraction
   ├─ Date of death extraction
   └─ Certificate number extraction

4. Rule-Based Validation
   ├─ Name format validation
   ├─ Date reasonableness check
   ├─ Certificate number format
   └─ State-specific patterns

5. SSDI Cross-Reference
   ├─ Query Social Security Death Index
   ├─ Match SSN → Death Record
   └─ Verify date of death

6. Composite Confidence Scoring
   ├─ Document Quality: 30%
   ├─ Rule Validation: 40%
   └─ SSDI Verification: 30%

Result: 0-100% confidence (30-120 seconds)
```

**Dependencies**:
- PyPDF2, pdf2image for PDF processing
- pytesseract for OCR
- OpenCV for computer vision
- SSDI API access

## Layer 3: ID Verification

### Document Analyzer (`document_analyzer.py`)

**Purpose**: Verify government-issued ID documents

**State-Specific Patterns**:
```
California:
  ├─ DL Format: 1 letter + 7 digits
  └─ Security: Hologram, UV, Microprint

New York:
  ├─ DL Format: 9 digits
  └─ Security: Hologram, Laser perforation

Texas:
  ├─ DL Format: 8 digits
  └─ Security: Hologram, UV

Florida:
  ├─ DL Format: 1 letter + 12 digits
  └─ Security: Hologram, UV, Microprint
```

**Verification Steps**:
```
1. Image Quality Assessment
   └─ Resolution, clarity, completeness

2. OCR Data Extraction
   ├─ Full name
   ├─ Date of birth
   ├─ License number
   ├─ Address
   └─ Expiration date

3. Format Validation (State-specific)
   └─ Regex pattern matching

4. Expiration Check
   └─ Not expired

5. Name/DOB Matching
   └─ Fuzzy matching with expected values (>90%)

6. AAMVA Verification (Optional)
   └─ Query American Association of Motor Vehicle Administrators

Result: VERIFIED/NEEDS_REVIEW/FAILED
```

### Facial Recognition (`facial_recognition.py`)

**Purpose**: Biometric identity verification

**Verification Pipeline**:
```
1. Load Images
   ├─ ID photo
   └─ Beneficiary selfie

2. Face Detection
   ├─ Detect faces with landmarks
   └─ Extract: eyes, nose, mouth positions

3. Quality Checks
   ├─ Face size (>100x100 pixels)
   ├─ Alignment (eyes level, frontal pose)
   ├─ Brightness/contrast
   └─ Occlusion detection

4. Liveness Detection (Anti-Spoofing)
   ├─ Texture analysis (print vs real)
   ├─ 3D depth analysis
   ├─ Motion detection
   └─ Challenge-response (blink, smile)

5. Extract Facial Embeddings
   ├─ 128-dimensional feature vector
   ├─ FaceNet/ArcFace model
   └─ Normalize vectors

6. Compute Similarity
   ├─ Cosine similarity
   └─ Threshold: 75% match required

Result: VERIFIED (>75%), NEEDS_REVIEW (60-75%), FAILED (<60%)
```

**Multi-Angle Verification**:
- Front view + Left profile + Right profile
- All angles must match
- Confidence bonus: +3% per additional angle

## Layer 4: Fraud Detection

### Rule-Based Detector (`rule_based_detector.py`)

**8 Fraud Detection Rules**:

```
1. Relationship Fraud
   ├─ Non-relative beneficiary for >$100k account
   ├─ Beneficiary added <90 days before death
   └─ Confidence: 40-60%

2. Velocity Patterns
   ├─ Same beneficiary, multiple claims in 180 days
   └─ Confidence: 70%

3. Geographic Anomalies
   ├─ Beneficiary in different state than deceased
   ├─ For accounts >$50k
   └─ Confidence: 25%

4. Amount Anomalies
   ├─ Account balance >$500k (high scrutiny)
   ├─ Suspicious round numbers
   └─ Confidence: 30-45%

5. Document Inconsistencies
   ├─ Name mismatch (account vs death cert)
   ├─ SSN mismatch
   ├─ Account activity after death
   └─ Confidence: 50-80%

6. Beneficiary Patterns
   ├─ Same beneficiary, multiple unrelated deaths
   ├─ Professional beneficiary (>3 claims)
   └─ Confidence: 65%

7. Timing Anomalies
   ├─ Claim filed <3 days after death (too fast)
   ├─ Claim filed >2 years after death (delay)
   └─ Confidence: 35-45%

8. Sanctions/PEP Screening
   ├─ OFAC sanctions list
   ├─ Politically Exposed Persons
   └─ Confidence: 40-100%
```

**Risk Levels**:
- Fraud Score ≥80: **HIGH** → REJECT
- Fraud Score ≥50: **MEDIUM** → MANUAL_REVIEW
- Fraud Score ≥20: **LOW** → ENHANCED_VERIFICATION
- Fraud Score <20: **MINIMAL** → PROCEED

### ML Fraud Detector (`ml_fraud_detector.py`)

**Purpose**: ML-based anomaly detection

**Feature Engineering** (13 Features):
```
1. account_balance (log scale)
2. account_age_days
3. beneficiary_age
4. deceased_age_at_death
5. days_since_death
6. num_beneficiaries
7. relationship_score (0.1-1.0)
8. account_activity_score
9. document_quality_score
10. verification_confidence
11. geographic_distance (km)
12. submission_hour (0-23)
13. submission_day_of_week (0-6)
```

**Anomaly Detection**:
```
Method: Isolation Forest / One-Class SVM
Expected Ranges (learned from historical data):
  ├─ Account balance: log(22k) - log(1.2M)
  ├─ Account age: 1-20 years
  ├─ Beneficiary age: 18-80 years
  ├─ Days since death: 7-180 days
  └─ Document quality: 70-100%

Anomaly Score: 0.0-1.0
  ├─ >0.8: High risk
  ├─ >0.6: Medium risk
  └─ <0.6: Low risk
```

**Ensemble Models** (Production):
- XGBoost Classifier
- Random Forest Classifier
- Neural Network
- Voting/Averaging predictions

**Score Combination**:
- If ML model available: 60% ML + 40% Anomaly
- If ML unavailable: 100% Anomaly

## Layer 5: Document Intelligence

### Document Processor (`document_processor.py`)

**Purpose**: Advanced document processing and analysis

**Processing Pipeline**:
```
1. Document Loading & Validation
   ├─ Support: PDF, PNG, JPG, TIFF
   └─ Multi-page handling

2. Document Classification
   ├─ Death Certificate
   ├─ Driver's License / State ID
   ├─ Passport
   ├─ Bank Statement
   ├─ Trust Document
   └─ Court Order

3. Quality Assessment
   ├─ Resolution (DPI)
   ├─ Clarity (blur detection)
   ├─ Brightness
   ├─ Contrast
   └─ Completeness

4. Image Enhancement (if needed)
   ├─ Brightness/contrast adjustment
   ├─ Sharpening
   ├─ Noise reduction
   ├─ Deskewing
   └─ Binarization

5. Layout Analysis
   ├─ Detect regions (header, body, footer)
   ├─ Detect tables
   ├─ Detect images/logos
   └─ Determine reading order

6. Text Extraction (OCR)
   ├─ Tesseract / EasyOCR
   ├─ By region
   └─ Confidence scoring

7. Structured Data Extraction
   └─ Document-specific field extraction

8. Security Feature Detection
   ├─ Watermarks
   ├─ Holograms
   ├─ UV elements
   └─ Microprinting
```

## Data Models

### VerificationResult
```python
@dataclass
class VerificationResult:
    status: VerificationStatus  # VERIFIED, NEEDS_REVIEW, FAILED, PENDING
    confidence_score: float  # 0-100
    method: VerificationMethod  # BLOCKCHAIN, TRADITIONAL, BIOMETRIC, etc.
    processing_time_ms: float
    timestamp: datetime
    details: Dict  # Method-specific details
    error_message: Optional[str]
```

### WorkflowTask
```python
@dataclass
class WorkflowTask:
    task_id: str
    task_type: str
    description: str
    priority: TaskPriority  # CRITICAL, HIGH, MEDIUM, LOW
    dependencies: List[str]  # Task IDs
    parallel_group: Optional[str]
    timeout_seconds: int
    status: TaskStatus  # PENDING, IN_PROGRESS, COMPLETED, FAILED
    result: Optional[VerificationResult]
```

### FraudIndicator
```python
@dataclass
class FraudIndicator:
    indicator_type: str  # relationship_fraud, velocity_pattern, etc.
    severity: str  # high, medium, low
    description: str
    confidence: float  # 0-100
```

## Performance Metrics

### Processing Times (Target)

| Workflow Type | Average Time | P95 Time |
|--------------|--------------|----------|
| Fast Track (Blockchain) | 10s | 15s |
| Standard | 45s | 90s |
| High-Value | 3min | 5min |
| Trust/Estate | 7min | 10min |

### Accuracy Targets

| Service | Accuracy | False Positive Rate |
|---------|----------|-------------------|
| Blockchain Verification | 99.9% | <0.1% |
| Traditional Death Cert | 95% | <5% |
| Facial Recognition | 97% | <3% |
| Fraud Detection (Rule-based) | 85% | <10% |
| Fraud Detection (ML) | 92% | <5% |

## Security & Compliance

### Data Protection
- All PII encrypted at rest (AES-256)
- TLS 1.3 for data in transit
- Access logging and audit trails
- RBAC (Role-Based Access Control)

### Regulatory Compliance
- **GLBA** (Gramm-Leach-Bliley Act)
- **FCRA** (Fair Credit Reporting Act)
- **State Unclaimed Property Laws**
- **BSA/AML** (Bank Secrecy Act / Anti-Money Laundering)

### Privacy
- **GDPR** compliance for EU residents
- **CCPA** compliance for California residents
- Data retention policies
- Right to erasure

## Deployment Architecture

### Recommended Production Setup

```
┌─────────────────────────────────────────────────┐
│         Load Balancer (NGINX/AWS ALB)           │
└────────────────┬────────────────────────────────┘
                 │
    ┌────────────┼────────────┐
    ▼            ▼            ▼
┌─────────┐  ┌─────────┐  ┌─────────┐
│  Web    │  │  Web    │  │  Web    │  (Core Banking)
│ Server  │  │ Server  │  │ Server  │
│ (5007)  │  │ (5007)  │  │ (5007)  │
└─────────┘  └─────────┘  └─────────┘
    │            │            │
    └────────────┼────────────┘
                 ▼
┌─────────────────────────────────────────────────┐
│         Verification Services (Microservices)    │
├─────────────┬─────────────┬────────────────────┤
│  Death Cert │ ID Verif    │ Fraud Detection    │
│  Service    │ Service     │ Service            │
│  (Docker)   │ (Docker)    │ (Docker)           │
└─────────────┴─────────────┴────────────────────┘
                 │
    ┌────────────┼────────────┐
    ▼            ▼            ▼
┌─────────┐  ┌─────────┐  ┌─────────┐
│ Redis   │  │ Postgres│  │ S3      │  (Storage)
│ (Cache) │  │ (DB)    │  │ (Docs)  │
└─────────┘  └─────────┘  └─────────┘
```

### Infrastructure
- **Container Orchestration**: Kubernetes
- **Service Mesh**: Istio
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack (Elasticsearch, Logstash, Kibana)
- **Tracing**: Jaeger

## Future Enhancements

1. **Real-time Fraud Network Analysis**
   - Graph database (Neo4j) for relationship mapping
   - Network analysis algorithms
   - Social network fraud detection

2. **Advanced Biometrics**
   - Voice recognition
   - Gait analysis
   - Behavioral biometrics

3. **Blockchain Expansion**
   - Support for multiple blockchains
   - Cross-chain verification
   - Smart contract integration

4. **AI-Powered Document Understanding**
   - GPT-4 Vision for document analysis
   - Automated form filling
   - Intelligent document classification

5. **Predictive Analytics**
   - Predict fraud before it occurs
   - Risk scoring for new beneficiaries
   - Anomaly forecasting
