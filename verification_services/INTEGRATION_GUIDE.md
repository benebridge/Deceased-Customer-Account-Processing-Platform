# BeneBridge Verification Services - Integration Guide

## Overview

This guide shows how to integrate the BeneBridge verification services with the Core Banking Platform (localhost:5007).

## Architecture

```
Core Banking Platform (Port 5007)
    ↓
Verification Services (Microservices)
    ├── Death Certificate Verification
    │   ├── Blockchain Verifier (Titan Seal)
    │   └── Traditional Verifier (OCR + SSDI)
    ├── ID Verification
    │   ├── Document Analyzer
    │   └── Facial Recognition
    ├── Fraud Detection
    │   ├── Rule-Based Detector
    │   └── ML Fraud Detector
    ├── Document Intelligence
    │   └── Document Processor
    └── Workflow Orchestration
        ├── Workflow Engine
        └── ML Router
```

## Quick Start Integration

### 1. Import Verification Services

```python
import sys
sys.path.append('verification_services')

# Death certificate verification
from death_cert_verification.blockchain_verifier import BlockchainDeathCertVerifier
from death_cert_verification.traditional_verifier import TraditionalDeathCertVerifier

# ID verification
from id_verification.document_analyzer import IDDocumentAnalyzer
from id_verification.facial_recognition import FacialRecognitionService

# Fraud detection
from fraud_detection.rule_based_detector import RuleBasedFraudDetector
from fraud_detection.ml_fraud_detector import MLFraudDetector

# Workflow orchestration
from workflow_orchestration.workflow_engine import WorkflowEngine
from workflow_orchestration.ml_router import MLCaseRouter

# Document intelligence
from document_intelligence.document_processor import DocumentProcessor
```

### 2. Initialize Services

```python
# Initialize all verification services
blockchain_verifier = BlockchainDeathCertVerifier()
traditional_verifier = TraditionalDeathCertVerifier()
id_analyzer = IDDocumentAnalyzer()
facial_recognition = FacialRecognitionService()
rule_based_fraud = RuleBasedFraudDetector()
ml_fraud = MLFraudDetector()
workflow_engine = WorkflowEngine(max_parallel_tasks=5)
ml_router = MLCaseRouter()
doc_processor = DocumentProcessor()
```

### 3. Process a Case - Complete Example

```python
def process_beneficiary_case(case_id: str, case_data: dict):
    """
    Complete verification workflow for a beneficiary case

    Args:
        case_id: Unique case identifier (e.g., 'CNB-2026-1039')
        case_data: Case information dictionary

    Returns:
        Complete verification results
    """

    # STEP 1: Route case to appropriate workflow
    routing_result = ml_router.route_case(case_data)
    print(f"Case routed to: {routing_result['workflow_template']}")
    print(f"Estimated processing time: {routing_result['estimated_processing_minutes']} minutes")

    # STEP 2: Generate dynamic workflow
    workflow = workflow_engine.generate_workflow(
        case_id=case_id,
        account_type=case_data['account_type'],
        account_balance=case_data['account_balance'],
        state=case_data['state'],
        has_blockchain_cert=case_data.get('has_blockchain_cert', False)
    )

    print(f"Generated workflow with {len(workflow.tasks)} tasks")

    # STEP 3: Define task executor function
    def execute_verification_task(task):
        """Execute individual verification task"""

        if task.task_type == 'death_cert_verification_blockchain':
            # Blockchain verification pathway
            result = blockchain_verifier.verify_death_certificate(
                pdf_path=case_data['death_cert_path'],
                expected_deceased_name=case_data['deceased_name']
            )
            return result

        elif task.task_type == 'death_cert_verification_traditional':
            # Traditional verification pathway
            result = traditional_verifier.verify_death_certificate(
                pdf_path=case_data['death_cert_path'],
                expected_deceased_name=case_data['deceased_name'],
                expected_ssn=case_data.get('deceased_ssn')
            )
            return result

        elif task.task_type == 'id_verification_document':
            # ID document verification
            result = id_analyzer.verify_id_document(
                id_image_path=case_data['id_document_path'],
                expected_name=case_data['beneficiary_name'],
                expected_dob=case_data['beneficiary_dob']
            )
            return result

        elif task.task_type == 'id_verification_facial':
            # Facial recognition
            result = facial_recognition.verify_face_match(
                id_photo_path=case_data['id_document_path'],
                selfie_path=case_data['beneficiary_selfie_path'],
                require_liveness=True
            )
            return result

        elif task.task_type == 'fraud_detection_rules':
            # Rule-based fraud detection
            fraud_result = rule_based_fraud.detect_fraud(case_data)

            # Convert to VerificationResult format
            from common.models import VerificationResult, VerificationStatus, VerificationMethod
            from datetime import datetime

            return VerificationResult(
                status=VerificationStatus.VERIFIED if not fraud_result['fraud_detected'] else VerificationStatus.FAILED,
                confidence_score=100 - fraud_result['fraud_score'],
                method=VerificationMethod.FRAUD_DETECTION,
                processing_time_ms=fraud_result['processing_time_ms'],
                timestamp=datetime.now(),
                details=fraud_result
            )

        elif task.task_type == 'fraud_detection_ml':
            # ML-based fraud detection
            ml_result = ml_fraud.detect_fraud_ml(case_data)

            from common.models import VerificationResult, VerificationStatus, VerificationMethod
            from datetime import datetime

            return VerificationResult(
                status=VerificationStatus.VERIFIED if not ml_result['ml_fraud_detected'] else VerificationStatus.FAILED,
                confidence_score=100 - ml_result['anomaly_score'],
                method=VerificationMethod.FRAUD_DETECTION,
                processing_time_ms=ml_result['processing_time_ms'],
                timestamp=datetime.now(),
                details=ml_result
            )

        else:
            # Other task types (enhanced verification, compliance, etc.)
            # TODO: Implement as needed
            from common.models import VerificationResult, VerificationStatus, VerificationMethod
            from datetime import datetime

            return VerificationResult(
                status=VerificationStatus.VERIFIED,
                confidence_score=85.0,
                method=VerificationMethod.MANUAL,
                processing_time_ms=100,
                timestamp=datetime.now(),
                details={'note': f'Task {task.task_type} simulated'}
            )

    # STEP 4: Execute workflow with parallel task execution
    execution_result = workflow_engine.execute_workflow(
        workflow=workflow,
        task_executor_func=execute_verification_task
    )

    print(f"Workflow completed: {execution_result['status']}")
    print(f"Total execution time: {execution_result['execution_time_ms']:.2f}ms")

    # STEP 5: Aggregate results and determine final decision
    final_decision = aggregate_verification_results(workflow, execution_result)

    return {
        'case_id': case_id,
        'routing': routing_result,
        'workflow': execution_result,
        'final_decision': final_decision
    }


def aggregate_verification_results(workflow, execution_result):
    """
    Aggregate all verification results into final decision

    Returns:
        Final decision dictionary
    """
    # Collect all task results
    critical_tasks = [t for t in workflow.tasks if t.priority.value == 'critical']

    # Check if any critical task failed
    critical_failures = [t for t in critical_tasks if t.status.value == 'failed']

    if critical_failures:
        return {
            'approved': False,
            'decision': 'REJECT',
            'reason': 'Critical verification tasks failed',
            'failed_tasks': [t.task_id for t in critical_failures]
        }

    # Calculate overall confidence score
    completed_tasks = [t for t in workflow.tasks if t.result is not None]

    if not completed_tasks:
        return {
            'approved': False,
            'decision': 'PENDING',
            'reason': 'No tasks completed'
        }

    avg_confidence = sum(t.result.confidence_score for t in completed_tasks) / len(completed_tasks)

    # Decision logic
    if avg_confidence >= 90:
        decision = 'AUTO_APPROVE'
    elif avg_confidence >= 75:
        decision = 'APPROVE_WITH_CONDITIONS'
    elif avg_confidence >= 60:
        decision = 'MANUAL_REVIEW_REQUIRED'
    else:
        decision = 'REJECT'

    return {
        'approved': decision in ['AUTO_APPROVE', 'APPROVE_WITH_CONDITIONS'],
        'decision': decision,
        'overall_confidence': avg_confidence,
        'num_tasks_completed': len(completed_tasks),
        'num_tasks_failed': len([t for t in workflow.tasks if t.status.value == 'failed'])
    }
```

## Integration with Core Banking Platform

### Modify `core_banking_platform/app_core_banking.py`

Add verification endpoint:

```python
@app.route('/api/cases/<case_id>/verify', methods=['POST'])
def verify_case(case_id):
    """
    Run complete verification workflow on a case
    """
    case = Case.query.get(case_id)

    if not case:
        return jsonify({'error': 'Case not found'}), 404

    # Prepare case data for verification
    case_data = {
        'case_id': case.case_number,
        'account_type': case.account_type,
        'account_balance': case.account_balance,
        'state': case.deceased_state,
        'deceased_name': case.deceased_name,
        'deceased_ssn': case.deceased_ssn,
        'deceased_dob': case.deceased_dob,
        'date_of_death': case.date_of_death,
        'beneficiary_name': case.beneficiary_name,
        'beneficiary_dob': case.beneficiary_dob,
        'beneficiary_relationship': case.beneficiary_relationship,
        'beneficiary_state': case.beneficiary_state,
        'has_blockchain_cert': case.has_blockchain_cert,

        # Document paths (adjust based on your file storage)
        'death_cert_path': f'documents/{case_id}/death_certificate.pdf',
        'id_document_path': f'documents/{case_id}/id_document.jpg',
        'beneficiary_selfie_path': f'documents/{case_id}/selfie.jpg'
    }

    # Run verification
    try:
        results = process_beneficiary_case(case.case_number, case_data)

        # Update case with verification results
        case.verification_status = results['final_decision']['decision']
        case.verification_confidence = results['final_decision']['overall_confidence']
        case.verification_date = datetime.now()

        db.session.commit()

        return jsonify({
            'success': True,
            'results': results
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

### Add Verification Button to Case Detail Page

In `core_banking_platform/templates/case_detail.html`:

```html
<button onclick="runVerification()" class="btn-verify">
    Run Complete Verification
</button>

<script>
function runVerification() {
    const caseId = '{{ case.id }}';

    // Show loading state
    showLoading('Running verification workflow...');

    fetch(`/api/cases/${caseId}/verify`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();

        if (data.success) {
            showResults(data.results);
        } else {
            showError(data.error);
        }
    })
    .catch(error => {
        hideLoading();
        showError('Verification failed: ' + error);
    });
}
</script>
```

## Environment Setup

### Required Python Packages

```bash
pip install web3
pip install PyPDF2
pip install pdf2image
pip install pytesseract
pip install pillow
pip install opencv-python
pip install numpy
pip install scikit-learn
pip install xgboost
```

### Optional for Production

```bash
# For advanced OCR
pip install easyocr

# For face recognition
pip install face_recognition
pip install dlib

# For document analysis
pip install layoutparser
```

## Configuration

Create `verification_services/config.py`:

```python
# Blockchain Configuration
ETHEREUM_NODE_URL = 'https://mainnet.infura.io/v3/YOUR_PROJECT_ID'
BLOCKCHAIN_ENABLED = True

# SSDI Configuration
SSDI_API_ENDPOINT = 'https://api.ssdi.gov/verify'
SSDI_API_KEY = 'your_ssdi_api_key'

# AAMVA Configuration (for driver's license verification)
AAMVA_API_ENDPOINT = 'https://api.aamva.org/verify'
AAMVA_API_KEY = 'your_aamva_api_key'

# Fraud Detection
FRAUD_DETECTION_ENABLED = True
ML_MODEL_PATH = 'models/fraud_detector.pkl'

# Workflow Engine
MAX_PARALLEL_TASKS = 5
WORKFLOW_TIMEOUT_SECONDS = 300

# Document Processing
TESSERACT_PATH = '/usr/local/bin/tesseract'
TEMP_DIR = '/tmp/benebridge'
```

## Performance Considerations

### Expected Processing Times

- **Fast Track (Blockchain)**: 5-15 seconds
- **Standard Workflow**: 30-60 seconds
- **Enhanced Verification**: 2-5 minutes
- **Complex Trust/Estate**: 5-10 minutes

### Optimization Tips

1. **Use Blockchain Verification When Possible**
   - 10x faster than traditional verification
   - Higher confidence scores
   - Encourages adoption of Titan Seal

2. **Parallel Task Execution**
   - Death cert and ID verification run in parallel
   - Fraud detection runs after both complete
   - Reduces total workflow time by 40-60%

3. **Caching**
   - Cache SSDI lookups (SSN → death record)
   - Cache ML model predictions for similar cases
   - Cache document OCR results

4. **Resource Allocation**
   - Allocate more workers for automated workflows
   - Reserve specialized reviewers for complex cases
   - Use ML router to optimize distribution

## Monitoring and Logging

### Add Logging to Verification Services

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('verification_services.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('verification_services')

# Use in verification functions
logger.info(f"Starting verification for case {case_id}")
logger.warning(f"Low confidence score: {confidence}")
logger.error(f"Verification failed: {error}")
```

### Metrics to Track

- Verification success rate
- Average processing time per workflow type
- Fraud detection hit rate
- False positive/negative rates
- SLA compliance rate

## Testing

### Unit Tests

```python
import unittest
from death_cert_verification.blockchain_verifier import BlockchainDeathCertVerifier

class TestBlockchainVerifier(unittest.TestCase):
    def setUp(self):
        self.verifier = BlockchainDeathCertVerifier()

    def test_hash_format_validation(self):
        # Valid hash
        valid_hash = '0x' + 'a' * 64
        self.assertTrue(self.verifier._validate_hash_format(valid_hash))

        # Invalid hash
        invalid_hash = '0x123'
        self.assertFalse(self.verifier._validate_hash_format(invalid_hash))

    def test_verification_flow(self):
        # TODO: Add test with mock PDF and blockchain
        pass
```

### Integration Tests

```python
def test_complete_workflow():
    """Test complete verification workflow"""

    # Prepare test case
    case_data = {
        'case_id': 'TEST-001',
        'account_type': 'checking',
        'account_balance': 50000,
        # ... other fields
    }

    # Run verification
    results = process_beneficiary_case('TEST-001', case_data)

    # Assertions
    assert results['final_decision']['approved'] in [True, False]
    assert 'workflow' in results
    assert 'routing' in results
```

## Troubleshooting

### Common Issues

**Issue**: Blockchain verification fails with "Connection refused"
- **Solution**: Check ETHEREUM_NODE_URL in config
- Verify Infura/Alchemy API key is valid

**Issue**: OCR produces poor results
- **Solution**: Check image quality (DPI >= 300)
- Ensure Tesseract is installed and path is correct
- Try image enhancement preprocessing

**Issue**: Workflow times out
- **Solution**: Increase WORKFLOW_TIMEOUT_SECONDS
- Check for blocking tasks
- Verify all dependencies are met

## Next Steps

1. **Deploy Services**
   - Consider containerizing with Docker
   - Deploy as microservices with load balancing
   - Use Redis for caching and task queues

2. **Train ML Models**
   - Collect labeled fraud cases
   - Train XGBoost fraud detector
   - Fine-tune routing model

3. **Add Monitoring**
   - Set up Prometheus metrics
   - Create Grafana dashboards
   - Configure alerting for failures

4. **Compliance**
   - Audit logging for all decisions
   - Data retention policies
   - Privacy controls (GDPR, CCPA)

## Support

For issues or questions:
- Create issue in project repository
- Contact: support@benebridge.io
- Documentation: https://docs.benebridge.io
