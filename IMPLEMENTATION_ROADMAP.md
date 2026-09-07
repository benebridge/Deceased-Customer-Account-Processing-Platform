# BeneBridge Platform - Dissertation Alignment Implementation Roadmap

## Overview
This document outlines the remaining changes needed to fully align the BeneBridge platform with the dissertation specifications.

## ✅ COMPLETED (Priority 1)
1. ✅ Approval tier thresholds updated to match Table 4.2
2. ✅ Composite confidence scoring formula implemented (Page 18)
3. ✅ Comprehensive fraud scoring framework added (Table 5.7)
4. ✅ Tier 1 critical failure override system implemented

---

## 🔨 IN PROGRESS - Implementation Tasks

### Task 1: Blockchain Death Certificate QR Code/Hash Extraction
**File**: `bank_operations_platform/textract_extraction.py`
**Status**: Ready to implement

**Changes Needed**:
```python
def extract_blockchain_identifiers(response_blocks):
    """
    Extract blockchain ID and verification URLs from Titan Seal death certificates.
    Looks for:
    - Blockchain ID pattern: 0x[40 hex characters]
    - Verification URLs: https://titanseal.com/verify, https://etherscan.io, etc.
    - QR code data (if Textract can detect it)
    """
    blockchain_data = {
        'has_blockchain_seal': False,
        'blockchain_id': None,
        'verification_urls': [],
        'seal_issuer': None
    }

    # Search all text blocks for blockchain ID pattern
    for block in response_blocks:
        if block['BlockType'] == 'LINE':
            text = block.get('Text', '')

            # Look for Ethereum address pattern (0x + 40 hex chars)
            if re.search(r'0x[0-9a-fA-F]{40}', text):
                blockchain_id = re.findall(r'0x[0-9a-fA-F]{40}', text)[0]
                blockchain_data['blockchain_id'] = blockchain_id
                blockchain_data['has_blockchain_seal'] = True

            # Look for verification URLs
            if 'titanseal.com' in text.lower():
                blockchain_data['verification_urls'].append(text)
            if 'etherscan.io' in text.lower() or 'etherchain.org' in text.lower():
                blockchain_data['verification_urls'].append(text)

    return blockchain_data
```

**Integration Point**: Add to `extract_death_certificate_textract()` return value as `blockchain_verification` field.

**Security Score Impact**: If blockchain seal detected and valid → Security Score = 95, otherwise Security Score = 75

---

### Task 2: LexisNexis Batch Processing Framework
**New File**: `crm_platform/lexisnexis_batch_processor.py`
**Status**: To be created

**Purpose**: Overnight batch processing of death notifications to enable proactive case creation (NOTIFIED state)

**Implementation**:
```python
#!/usr/bin/env python3
"""
LexisNexis Deceased Batch Processing
Simulates overnight batch import of death notifications
Per dissertation: Reduces fraud window from 3 days to 0-1 day (67% reduction)
"""

import sqlite3
import random
from datetime import datetime, timedelta

class LexisNexisBatchProcessor:
    def __init__(self, crm_db_path, jackhenry_db_path):
        self.crm_db = crm_db_path
        self.jackhenry_db = jackhenry_db_path

    def run_overnight_batch(self):
        """
        Simulate overnight LexisNexis death notification batch.
        Cross-references against Jack Henry customer list.
        Creates cases in NOTIFIED state for matching customers.
        """
        # 1. Query Jack Henry mock DB for all customers with death notifications
        # 2. For each deceased customer, check if case already exists in CRM
        # 3. If no case exists, create new case in NOTIFIED state
        # 4. Log batch processing metrics
        pass

    def match_death_notification_to_customer(self, death_record):
        """Match LexisNexis death record to Jack Henry customer by SSN"""
        pass

    def create_proactive_case(self, customer_data):
        """Create case in NOTIFIED state before beneficiary contact"""
        pass
```

**CRM Integration**: Add endpoint `/api/batch/lexisnexis` to trigger batch import

---

### Task 3: Post-Death Activity Monitoring
**File**: `crm_platform/verification_engine.py` (fraud scoring function)
**Status**: Framework exists, needs activation

**Changes to `calculate_fraud_risk_score()`**:
```python
# =============================================================================
# FRAUD CHECK 5: Post-Death Activity (25 points) - ACTIVATE THIS
# =============================================================================
if accounts_data and date_of_death:
    post_death_transactions = check_post_death_activity(
        accounts_data,
        date_of_death
    )

    if post_death_transactions['suspicious_count'] > 0:
        fraud_indicators.append({
            'type': 'POST_DEATH_ACTIVITY',
            'severity': 'CRITICAL',
            'description': f'{post_death_transactions["suspicious_count"]} transactions after death',
            'points': 25
        })
        risk_points += 25

def check_post_death_activity(accounts_data, date_of_death):
    """
    Query Jack Henry for account activity after date of death.
    Flags: withdrawals, transfers, beneficiary changes
    """
    # Parse date_of_death
    # Query transaction history from Jack Henry
    # Count transactions after death date
    # Return suspicious activity summary
    pass
```

**Jack Henry Integration**: Add `get_account_transactions()` method to `mock_jackhenry_client.py`

---

### Task 4: Duplicate Claim Detection
**File**: `crm_platform/verification_engine.py` (fraud scoring function)
**Status**: Framework exists, needs activation

**Changes to `calculate_fraud_risk_score()`**:
```python
# =============================================================================
# FRAUD CHECK 4: Duplicate Claim Detection (20 points) - ACTIVATE THIS
# =============================================================================
duplicate_claim = check_duplicate_claims(
    death_cert_data.get('ssn'),
    claim_data.get('deceased_ssn')
)

if duplicate_claim['found']:
    fraud_indicators.append({
        'type': 'DUPLICATE_CLAIM',
        'severity': 'HIGH',
        'description': f'Claim already exists: Case #{duplicate_claim["case_id"]}',
        'points': 20
    })
    risk_points += 20

def check_duplicate_claims(deceased_ssn):
    """Query CRM database for existing claims with same deceased SSN"""
    # Connect to workflow_cases database
    # Search for cases with matching deceased_ssn
    # Return case_id if found
    pass
```

**Database Query**: Search `workflow_cases` table by `deceased_ssn` field (may need to add this column)

---

### Task 5: API Performance Metrics Tracking
**Files**: All API integration points
**Status**: Add timing wrappers

**Implementation**:
```python
import time

def track_api_call(api_name, func, *args, **kwargs):
    """Wrapper to track API call performance"""
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()

    duration_ms = (end_time - start_time) * 1000

    # Log to database or metrics store
    log_api_metrics(api_name, duration_ms, result.get('success', False))

    return result, duration_ms
```

**Target Metrics** (from Table 5.3):
- AWS Textract: 1,847ms average
- Ribbon Verify: 2,134ms average
- Persona API: 1,523ms average
- DocuSign: 892ms average

---

### Task 6: Persona API - Leave as Placeholder
**File**: `crm_platform/verification_engine.py:261-278`
**Status**: Keep as placeholder (per your instruction #6)
**Reason**: Synthetic accounts cannot pass real ID verification

**No changes needed** - function already documents it's a placeholder.

---

### Task 7: 14-State Workflow Transition Updates
**File**: `crm_platform/app_crm.py`
**Status**: States defined, verify all transitions implemented

**Verification Checklist**:
- [ ] NOTIFIED → TRIAGED (from LexisNexis batch)
- [ ] TRIAGED → AWAITING_DOCUMENTS (employee creates case)
- [ ] AWAITING_DOCUMENTS → IN_VERIFICATION (documents uploaded)
- [ ] IN_VERIFICATION → VERIFIED (verification passes)
- [ ] IN_VERIFICATION → NEEDS_REVIEW (verification concerns)
- [ ] IN_VERIFICATION → FRAUD_ALERT (fraud detected)
- [ ] VERIFIED → PAYMENT_APPROVED (approval granted)
- [ ] PAYMENT_APPROVED → PAYMENT_PROCESSING (payment initiated)
- [ ] PAYMENT_PROCESSING → PAYMENT_COMPLETED (success)
- [ ] PAYMENT_PROCESSING → PAYMENT_FAILED (failure)
- [ ] FRAUD_ALERT → FRAUD_INVESTIGATION (escalated)
- [ ] Any state → CLOSED (completed)
- [ ] Any state → ABANDONED (abandoned by beneficiary)

**Missing Transitions to Add**:
1. NOTIFIED state entry from batch processing
2. PAYMENT_APPROVED → PAYMENT_PROCESSING transition
3. PAYMENT_PROCESSING → PAYMENT_COMPLETED/PAYMENT_FAILED transitions

---

## Implementation Priority

### Phase 1 (Quick Wins)
1. ✅ Task 4: Duplicate claim detection (database query only)
2. ✅ Task 3: Post-death activity monitoring (with synthetic data)
3. Task 5: API performance tracking (logging wrapper)

### Phase 2 (Moderate Complexity)
4. Task 1: Blockchain hash extraction (Textract enhancement)
5. Task 7: Workflow state transitions (routing logic)

### Phase 3 (Complex Architecture)
6. Task 2: LexisNexis batch processing (new subsystem)

---

## Testing Strategy

### Unit Tests Needed
- Blockchain ID extraction regex
- Duplicate claim detection query
- Post-death activity date comparison
- Fraud scoring point calculations

### Integration Tests Needed
- End-to-end verification flow with blockchain certificates
- Batch processing → NOTIFIED state creation
- Fraud detection → Tier 1 override

### Test Data Requirements
- Blockchain death certificate samples
- Transaction history test data
- Duplicate claim scenarios

---

## Database Schema Updates

### May Be Needed
```sql
-- Add deceased_ssn to workflow_cases for duplicate detection
ALTER TABLE workflow_cases ADD COLUMN deceased_ssn TEXT;

-- Add batch_processing_runs table for LexisNexis tracking
CREATE TABLE IF NOT EXISTS batch_processing_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date DATE,
    records_processed INTEGER,
    cases_created INTEGER,
    processing_time_seconds REAL
);

-- Add api_performance_metrics table
CREATE TABLE IF NOT EXISTS api_performance_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    api_name TEXT,
    duration_ms REAL,
    success BOOLEAN
);
```

---

## Next Steps

1. Review this roadmap
2. Decide which phase to implement first
3. Implement tasks one at a time
4. Test each implementation
5. Update dissertation results if metrics change

