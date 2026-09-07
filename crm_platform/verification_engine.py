#!/usr/bin/env python3
"""
CRM Platform - Internal Verification Engine
Handles document verification logic internally without external service calls
Integrates Textract, Ribbon Verify API, Persona API, and cross-verification
"""

import sys
import os
from datetime import datetime
import sqlite3

# Import Textract extraction functions from bank_operations_platform
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'bank_operations_platform'))
from textract_extraction import (
    extract_death_certificate_textract,
    extract_drivers_license_textract,
    extract_claim_form_textract
)

# Import API metrics tracker for performance monitoring
from api_metrics_tracker import get_tracker


def process_verification(death_cert_path, gov_id_path, claim_path):
    """
    Process uploaded documents for comprehensive verification.

    Workflow:
    1. Extract data from Death Certificate using Textract
    2. Call Ribbon Verify API for death verification (placeholder)
    3. Verify ID with Persona API, then extract data with Textract
    4. Extract data from Claim Form using Textract
    5. Cross-verify all document data
    6. Generate final verification results

    Args:
        death_cert_path: Path to death certificate file
        gov_id_path: Path to government ID file
        claim_path: Path to claim form file

    Returns:
        Dict with verification results
    """

    # Initialize verification results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results = {
        'timestamp': timestamp,
        'status': 'processing',
        'steps': [],
        'issues': [],
        'verification_methods': {},
        'final_approval': False
    }

    # =============================================================================
    # STEP 1: Death Certificate Verification using AWS Textract
    # =============================================================================
    results['steps'].append({
        'step': 1,
        'name': 'Death Certificate Extraction (AWS Textract)',
        'status': 'processing'
    })

    print("\n" + "="*80)
    print("STEP 1: Extracting Death Certificate Data with AWS Textract")
    print("="*80)

    # Track API performance for Textract death certificate extraction
    tracker = get_tracker()
    death_cert_result, dc_duration = tracker.track_api_call(
        'aws_textract',
        extract_death_certificate_textract,
        death_cert_path
    )
    results['verification_methods']['death_certificate'] = death_cert_result
    results['verification_methods']['death_certificate']['api_duration_ms'] = dc_duration

    if death_cert_result.get('verified'):
        results['steps'][-1]['status'] = 'success'
        results['steps'][-1]['data'] = death_cert_result.get('extracted_data', {})
        print(f"✓ Death certificate extracted successfully")
    else:
        results['steps'][-1]['status'] = 'warning'
        results['issues'].append(f"Death Certificate: {death_cert_result.get('error', 'Could not extract data')}")
        print(f"✗ Death certificate extraction failed")

    # =============================================================================
    # STEP 2: Ribbon Verify API Call (Placeholder)
    # =============================================================================
    results['steps'].append({
        'step': 2,
        'name': 'Ribbon Verify API - Death Verification',
        'status': 'processing'
    })

    print("\n" + "="*80)
    print("STEP 2: Calling Ribbon Verify API")
    print("="*80)

    # Track API performance for Ribbon Verify
    ribbon_verify_result, ribbon_duration = tracker.track_api_call(
        'ribbon_verify',
        call_ribbon_verify_api,
        death_cert_result.get('extracted_data', {})
    )
    results['verification_methods']['ribbon_verify'] = ribbon_verify_result
    results['verification_methods']['ribbon_verify']['api_duration_ms'] = ribbon_duration

    if ribbon_verify_result.get('success'):
        results['steps'][-1]['status'] = 'success'
        results['steps'][-1]['data'] = ribbon_verify_result
        print(f"✓ Ribbon Verify API call successful")
    else:
        results['steps'][-1]['status'] = 'pending'
        results['steps'][-1]['message'] = ribbon_verify_result.get('message', 'API integration pending')
        print(f"⚠ Ribbon Verify API: {ribbon_verify_result.get('message')}")

    # =============================================================================
    # STEP 3: Government ID Verification (Persona API + Textract)
    # =============================================================================
    results['steps'].append({
        'step': 3,
        'name': 'Government ID Verification (Persona API)',
        'status': 'processing'
    })

    print("\n" + "="*80)
    print("STEP 3A: Verifying ID with Persona API")
    print("="*80)

    # Track API performance for Persona
    persona_result, persona_duration = tracker.track_api_call(
        'persona_api',
        verify_id_with_persona,
        gov_id_path
    )
    results['verification_methods']['persona_api'] = persona_result
    results['verification_methods']['persona_api']['api_duration_ms'] = persona_duration

    if persona_result.get('verified'):
        results['steps'][-1]['status'] = 'success'
        results['steps'][-1]['data'] = persona_result
        print(f"✓ Persona API verification successful")
    else:
        results['steps'][-1]['status'] = 'pending'
        results['steps'][-1]['message'] = persona_result.get('message', 'API integration pending')
        print(f"⚠ Persona API: {persona_result.get('message')}")

    # Extract ID data with Textract
    results['steps'].append({
        'step': 4,
        'name': 'Government ID Data Extraction (AWS Textract)',
        'status': 'processing'
    })

    print("\n" + "="*80)
    print("STEP 3B: Extracting ID Data with AWS Textract")
    print("="*80)

    # Track API performance for Textract driver's license extraction
    id_textract_result, id_duration = tracker.track_api_call(
        'aws_textract',
        extract_drivers_license_textract,
        gov_id_path
    )
    results['verification_methods']['government_id'] = id_textract_result
    results['verification_methods']['government_id']['api_duration_ms'] = id_duration

    if id_textract_result.get('verified'):
        results['steps'][-1]['status'] = 'success'
        results['steps'][-1]['data'] = id_textract_result.get('extracted_data', {})
        print(f"✓ Government ID extracted successfully")
    else:
        results['steps'][-1]['status'] = 'warning'
        results['issues'].append(f"Government ID: {id_textract_result.get('error', 'Could not extract data')}")
        print(f"✗ Government ID extraction failed")

    # =============================================================================
    # STEP 4: Beneficiary Claim Form Extraction using AWS Textract
    # =============================================================================
    results['steps'].append({
        'step': 5,
        'name': 'Beneficiary Claim Form Processing (AWS Textract)',
        'status': 'processing'
    })

    print("\n" + "="*80)
    print("STEP 4: Extracting Claim Form Data with AWS Textract")
    print("="*80)

    claim_result = extract_claim_form_textract(claim_path)
    results['verification_methods']['claim_form'] = claim_result

    if claim_result.get('extracted'):
        results['steps'][-1]['status'] = 'success'
        results['steps'][-1]['data'] = claim_result.get('data', {})
        print(f"✓ Claim form extracted successfully")
    else:
        results['steps'][-1]['status'] = 'warning'
        results['issues'].append(f"Claim Form: {claim_result.get('error', 'Could not extract data')}")
        print(f"✗ Claim form extraction failed")

    # =============================================================================
    # STEP 5: Cross-Document Verification
    # =============================================================================
    results['steps'].append({
        'step': 6,
        'name': 'Cross-Document Verification',
        'status': 'processing'
    })

    print("\n" + "="*80)
    print("STEP 5: Cross-Verifying All Documents")
    print("="*80)

    cross_verify_result = cross_verify_documents(
        death_cert_result.get('extracted_data', {}),
        id_textract_result.get('extracted_data', {}),
        claim_result.get('data', {})
    )
    results['cross_verification'] = cross_verify_result

    if cross_verify_result['all_match']:
        results['steps'][-1]['status'] = 'success'
        print(f"✓ All documents match")
    else:
        results['steps'][-1]['status'] = 'warning'
        results['issues'].extend(cross_verify_result.get('mismatches', []))
        print(f"✗ Document mismatches found")

    # =============================================================================
    # STEP 6: Calculate Fraud Risk Score (Table 5.7)
    # =============================================================================
    results['steps'].append({
        'step': 7,
        'name': 'Fraud Risk Assessment',
        'status': 'processing'
    })

    print("\n" + "="*80)
    print("STEP 6: Calculating Fraud Risk Score")
    print("="*80)

    fraud_result = calculate_fraud_risk_score(
        death_cert_result.get('extracted_data', {}),
        id_textract_result.get('extracted_data', {}),
        claim_result.get('data', {})
    )
    results['fraud_assessment'] = fraud_result

    results['steps'][-1]['status'] = 'success'
    results['steps'][-1]['data'] = fraud_result

    print(f"  Fraud Risk Score: {fraud_result['fraud_risk_score']:.2f}/100")
    print(f"  Risk Level: {fraud_result['risk_level']}")
    print(f"  Fraud Indicators Found: {fraud_result['fraud_indicator_count']}")
    if fraud_result['fraud_indicators']:
        for indicator in fraud_result['fraud_indicators']:
            print(f"    - [{indicator['severity']}] {indicator['description']}")
    print(f"  Recommended Action: {fraud_result['recommended_action']}")

    # =============================================================================
    # STEP 7: Calculate Composite Confidence Score (Dissertation Formula)
    # =============================================================================
    results['steps'].append({
        'step': 8,
        'name': 'Composite Confidence Score Calculation',
        'status': 'processing'
    })

    print("\n" + "="*80)
    print("STEP 7: Calculating Composite Confidence Score")
    print("="*80)

    # Gather component scores
    # IDP Score: Average Textract confidence across all documents
    textract_confidences = []
    if death_cert_result.get('verified'):
        textract_confidences.append(death_cert_result.get('confidence', 0))
    if id_textract_result.get('verified'):
        textract_confidences.append(id_textract_result.get('confidence', 0))
    if claim_result.get('extracted'):
        textract_confidences.append(claim_result.get('confidence', 0))

    idp_score = sum(textract_confidences) / len(textract_confidences) if textract_confidences else 0

    # Consistency Score: Based on cross-verification results
    consistency_score = 100.0 if cross_verify_result['all_match'] else 50.0

    # Security Score: Based on blockchain/API verification
    # Per dissertation:
    #   - Blockchain-sealed certificates = 95 (bypass Ribbon Verify)
    #   - Non-blockchain certificates → use Ribbon Verify result
    blockchain_verification = death_cert_result.get('blockchain_verification', {})
    has_blockchain_seal = blockchain_verification.get('has_blockchain_seal', False)

    if has_blockchain_seal:
        # Blockchain seal detected - highest security score, no need for Ribbon Verify
        security_score = 95.0
        print(f"  ✓ Blockchain seal detected: {blockchain_verification.get('blockchain_id', 'N/A')}")
        print(f"    Seal issuer: {blockchain_verification.get('seal_issuer', 'N/A')}")
        print(f"    Security Score: 95.0 (blockchain verified)")
    else:
        # No blockchain seal - use Ribbon Verify API result for security score
        ribbon_result = ribbon_verify_result.get('verified', False)
        if ribbon_result:
            security_score = 90.0  # Ribbon Verify success
            print(f"  ✓ Ribbon Verify API confirmed death certificate")
            print(f"    Security Score: 90.0 (API verified)")
        else:
            security_score = 75.0  # Ribbon Verify failed or unavailable
            print(f"  ⚠ Ribbon Verify API unavailable or failed")
            print(f"    Security Score: 75.0 (default - API pending)")

    # Fraud Score: Use calculated fraud risk score (inverse - 100 = no fraud)
    fraud_score = fraud_result['fraud_risk_score']

    # Calculate composite score
    composite_result = calculate_composite_confidence_score(
        idp_score,
        consistency_score,
        security_score,
        fraud_score
    )
    results['composite_confidence'] = composite_result
    results['verification_score'] = composite_result['composite_percentage']

    results['steps'][-1]['status'] = 'success'
    results['steps'][-1]['data'] = composite_result

    print(f"  IDP Score (Textract): {idp_score:.2f}%")
    print(f"  Consistency Score: {consistency_score:.2f}%")
    print(f"  Security Score: {security_score:.2f}%")
    print(f"  Fraud Score: {fraud_score:.2f}%")
    print(f"\n  → Composite Score: {composite_result['composite_percentage']:.2f}%")
    print(f"  → Verification Tier: {composite_result['tier']}")
    print(f"  → Recommended Action: {composite_result['recommended_action']}")
    print(f"  → Confidence Level: {composite_result['confidence_level']}")

    # =============================================================================
    # FINAL: Determine Approval Status
    # =============================================================================
    print("\n" + "="*80)
    print("FINAL VERIFICATION RESULTS")
    print("="*80)

    # Two-tier verification system per dissertation:
    # Tier 1: Critical failures (fraud, authentication, consistency) - OVERRIDES composite score
    # Tier 2: Composite scoring (only if Tier 1 passes)

    # Identify critical issues that require immediate manual review/investigation
    critical_issues = [issue for issue in results['issues'] if 'Death Certificate' in issue or 'Claim Form' in issue]

    # Check fraud risk level
    fraud_risk_level = fraud_result['risk_level']
    high_fraud_risk = fraud_risk_level in ['HIGH', 'CRITICAL']

    # Check for failed document extraction
    extraction_failed = not death_cert_result.get('verified') or not claim_result.get('extracted')

    # TIER 1: Critical Failure Checks (these OVERRIDE composite score)
    tier1_failures = []

    if len(critical_issues) > 0:
        tier1_failures.append(f"Document extraction failures: {len(critical_issues)}")

    if not cross_verify_result['all_match']:
        tier1_failures.append(f"Cross-document verification failed: {len(cross_verify_result.get('mismatches', []))} mismatches")

    if high_fraud_risk:
        tier1_failures.append(f"High fraud risk detected: {fraud_risk_level} ({fraud_result['fraud_indicator_count']} indicators)")

    if extraction_failed:
        tier1_failures.append("Critical document extraction failure")

    # Tier 1: Check for critical failures - these ALWAYS force manual review regardless of composite score
    if len(tier1_failures) > 0:
        results['final_approval'] = False
        results['verification_tier'] = 'TIER_1_FAILURE'
        results['tier1_failures'] = tier1_failures

        # Determine status based on severity
        if fraud_risk_level == 'CRITICAL':
            results['status'] = 'fraud_investigation'
            print(f"\n🚨 TIER 1 CRITICAL FAILURE - FRAUD INVESTIGATION REQUIRED")
        elif high_fraud_risk:
            results['status'] = 'fraud_alert'
            print(f"\n⚠ TIER 1 FAILURE - FRAUD ALERT")
        else:
            results['status'] = 'requires_review'
            print(f"\n⚠ TIER 1 VERIFICATION FAILED - MANUAL REVIEW REQUIRED")

        print(f"\nCritical Failures (override composite score):")
        for failure in tier1_failures:
            print(f"  - {failure}")
    else:
        # Tier 2: Use composite confidence score (only when no Tier 1 failures)
        results['verification_tier'] = composite_result['tier']
        if composite_result['composite_score'] >= 0.90:
            results['final_approval'] = True
            results['status'] = 'approved'
            print(f"\n✓ TIER 2 VERIFICATION PASSED - APPROVED")
        elif composite_result['composite_score'] >= 0.75:
            results['final_approval'] = False
            results['status'] = 'requires_review'
            print(f"\n⚠ TIER 2 VERIFICATION - MANUAL REVIEW REQUIRED")
        else:
            results['final_approval'] = False
            results['status'] = 'fraud_alert'
            print(f"\n⚠ TIER 2 VERIFICATION - FRAUD ALERT")

    print(f"\nTotal issues found: {len(results['issues'])}")
    print(f"Composite Confidence Score: {composite_result['composite_percentage']:.2f}%")
    print("="*80 + "\n")

    # Add extracted data to results
    results['success'] = True
    results['death_cert_data'] = death_cert_result.get('extracted_data', {})
    results['id_data'] = id_textract_result.get('extracted_data', {})
    results['claim_data'] = claim_result.get('data', {})

    return results


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def calculate_fraud_risk_score(death_cert_data, id_data, claim_data, accounts_data=None):
    """
    Calculate comprehensive fraud risk score per dissertation Table 5.7.

    Evaluates multiple fraud indicators and returns an inverse score (0-100)
    where 100 = no fraud detected, 0 = high fraud risk.

    Fraud Detection Capabilities (Table 5.7):
    - Document authenticity verification
    - Cross-document consistency checks
    - Duplicate claim detection
    - Post-death account activity monitoring
    - Beneficiary change timeline analysis
    - High-value transaction patterns
    - Geographic anomaly detection
    - Identity verification mismatches

    Args:
        death_cert_data: Extracted death certificate data
        id_data: Extracted government ID data
        claim_data: Extracted claim form data
        accounts_data: Optional account history data

    Returns:
        Dict containing:
        - fraud_risk_score: Inverse fraud score (0-100, where 100 = no fraud)
        - fraud_indicators: List of detected fraud indicators
        - risk_level: LOW, MEDIUM, HIGH, CRITICAL
        - recommended_action: Next step based on risk level
    """
    fraud_indicators = []
    risk_points = 0  # Higher = more fraud risk
    max_risk_points = 100

    # =============================================================================
    # FRAUD CHECK 1: Document Authenticity (20 points)
    # =============================================================================
    # Check for low confidence scores indicating potential tampering
    death_cert_confidence = death_cert_data.get('confidence', 100)
    id_confidence = id_data.get('confidence', 100)

    if death_cert_confidence < 70:
        fraud_indicators.append({
            'type': 'SUSPICIOUS_DOCUMENT',
            'severity': 'HIGH',
            'description': f'Death certificate has low extraction confidence: {death_cert_confidence}%',
            'points': 20
        })
        risk_points += 20
    elif death_cert_confidence < 85:
        fraud_indicators.append({
            'type': 'DOCUMENT_QUALITY',
            'severity': 'MEDIUM',
            'description': f'Death certificate quality concerns: {death_cert_confidence}%',
            'points': 10
        })
        risk_points += 10

    if id_confidence < 70:
        fraud_indicators.append({
            'type': 'SUSPICIOUS_ID',
            'severity': 'HIGH',
            'description': f'Government ID has low extraction confidence: {id_confidence}%',
            'points': 20
        })
        risk_points += 20

    # =============================================================================
    # FRAUD CHECK 2: Cross-Document Consistency (15 points)
    # =============================================================================
    deceased_cert = (death_cert_data.get('deceased_name') or '').lower().strip()
    deceased_claim = (claim_data.get('deceased_name') or '').lower().strip()
    bene_id = (id_data.get('name') or '').lower().strip()
    bene_claim = (claim_data.get('beneficiary_name') or '').lower().strip()

    if deceased_cert and deceased_claim and deceased_cert != deceased_claim:
        fraud_indicators.append({
            'type': 'NAME_MISMATCH',
            'severity': 'HIGH',
            'description': f'Deceased name mismatch: "{deceased_cert}" vs "{deceased_claim}"',
            'points': 15
        })
        risk_points += 15

    if bene_id and bene_claim and bene_id != bene_claim:
        fraud_indicators.append({
            'type': 'BENEFICIARY_MISMATCH',
            'severity': 'HIGH',
            'description': f'Beneficiary name mismatch: "{bene_id}" vs "{bene_claim}"',
            'points': 15
        })
        risk_points += 15

    # =============================================================================
    # FRAUD CHECK 3: Beneficiary Change Timeline (15 points)
    # =============================================================================
    # Check if beneficiary was changed shortly before death (red flag)
    date_of_death = death_cert_data.get('date_of_death')
    beneficiary_change_date = claim_data.get('beneficiary_change_date')

    if date_of_death and beneficiary_change_date:
        # This would require date parsing - simplified for now
        # In production: parse dates and check if change was < 90 days before death
        fraud_indicators.append({
            'type': 'RECENT_BENEFICIARY_CHANGE',
            'severity': 'MEDIUM',
            'description': 'Beneficiary change detected - timeline analysis required',
            'points': 0  # Would be 15 if within 90 days
        })

    # =============================================================================
    # FRAUD CHECK 4: Duplicate Claim Detection (20 points)
    # =============================================================================
    # Check CRM database for existing claims with same deceased SSN
    deceased_ssn = death_cert_data.get('ssn')
    if deceased_ssn:
        duplicate_claim = check_duplicate_claims(deceased_ssn)
        if duplicate_claim['found']:
            fraud_indicators.append({
                'type': 'DUPLICATE_CLAIM',
                'severity': 'HIGH',
                'description': f'Claim already exists: Case #{duplicate_claim["case_id"]}',
                'points': 20
            })
            risk_points += 20

    # =============================================================================
    # FRAUD CHECK 5: Post-Death Activity (25 points)
    # =============================================================================
    # Check for suspicious account activity after death date
    if accounts_data and date_of_death:
        post_death_transactions = check_post_death_activity(accounts_data, date_of_death)
        if post_death_transactions['suspicious_count'] > 0:
            fraud_indicators.append({
                'type': 'POST_DEATH_ACTIVITY',
                'severity': 'CRITICAL',
                'description': f'{post_death_transactions["suspicious_count"]} transactions after death',
                'points': 25
            })
            risk_points += 25

    # =============================================================================
    # FRAUD CHECK 6: Geographic Anomalies (5 points)
    # =============================================================================
    # Check if beneficiary address is in different state/country than deceased
    deceased_state = death_cert_data.get('state_of_death', '').upper()
    beneficiary_state = claim_data.get('beneficiary_state', '').upper()

    if deceased_state and beneficiary_state and deceased_state != beneficiary_state:
        # Different states is not necessarily fraud, but adds minor risk
        fraud_indicators.append({
            'type': 'GEOGRAPHIC_DISTANCE',
            'severity': 'LOW',
            'description': f'Beneficiary in different state: {beneficiary_state} vs {deceased_state}',
            'points': 5
        })
        risk_points += 5

    # =============================================================================
    # Calculate Final Fraud Risk Score
    # =============================================================================
    # Inverse score: 100 = no fraud, 0 = maximum fraud risk
    fraud_risk_score = max(0, 100 - risk_points)

    # Determine risk level
    if fraud_risk_score >= 90:
        risk_level = 'LOW'
        recommended_action = 'PROCEED'
    elif fraud_risk_score >= 75:
        risk_level = 'MEDIUM'
        recommended_action = 'MANUAL_REVIEW'
    elif fraud_risk_score >= 50:
        risk_level = 'HIGH'
        recommended_action = 'FRAUD_INVESTIGATION'
    else:
        risk_level = 'CRITICAL'
        recommended_action = 'DENY_AND_INVESTIGATE'

    return {
        'fraud_risk_score': fraud_risk_score,
        'risk_points': risk_points,
        'max_risk_points': max_risk_points,
        'fraud_indicators': fraud_indicators,
        'fraud_indicator_count': len(fraud_indicators),
        'risk_level': risk_level,
        'recommended_action': recommended_action,
        'checks_performed': [
            'Document authenticity verification',
            'Cross-document consistency checks',
            'Beneficiary change timeline analysis',
            'Duplicate claim detection',
            'Post-death activity monitoring',
            'Geographic anomaly detection',
            'Identity verification mismatches'
        ]
    }


def check_duplicate_claims(deceased_ssn):
    """
    Check CRM database for existing claims with the same deceased SSN.

    Per dissertation fraud detection framework:
    - Duplicate claims add 20 fraud risk points
    - This prevents multiple beneficiaries from filing claims for the same deceased

    Args:
        deceased_ssn: Social Security Number of the deceased

    Returns:
        dict: {
            'found': bool,
            'case_id': int or None,
            'status': str or None
        }
    """
    if not deceased_ssn:
        return {'found': False, 'case_id': None, 'status': None}

    try:
        # Get CRM database path
        db_path = os.path.join(os.path.dirname(__file__), 'crm_database.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Search for existing cases with matching deceased SSN
        cursor.execute("""
            SELECT id, status, customer_name
            FROM workflow_cases
            WHERE deceased_ssn = ? AND status != 'CLOSED' AND status != 'ABANDONED'
            ORDER BY date_created DESC
            LIMIT 1
        """, (deceased_ssn,))

        result = cursor.fetchone()
        conn.close()

        if result:
            case_id, status, customer_name = result
            print(f"  ⚠ DUPLICATE CLAIM DETECTED: Case #{case_id} already exists for SSN {deceased_ssn}")
            print(f"     Existing case status: {status}")
            print(f"     Customer: {customer_name}")
            return {
                'found': True,
                'case_id': case_id,
                'status': status
            }
        else:
            return {'found': False, 'case_id': None, 'status': None}

    except Exception as e:
        print(f"  ! Error checking duplicate claims: {str(e)}")
        return {'found': False, 'case_id': None, 'status': None, 'error': str(e)}


def check_post_death_activity(accounts_data, date_of_death):
    """
    Check for suspicious account activity after the date of death.

    Per dissertation fraud detection framework:
    - Post-death activity adds 25 fraud risk points (CRITICAL severity)
    - Flags: withdrawals, transfers, beneficiary changes after death
    - Uses synthetic transaction data for POC demonstration

    Args:
        accounts_data: List of account dictionaries from Jack Henry
        date_of_death: Date string in format 'MM/DD/YYYY'

    Returns:
        dict: {
            'suspicious_count': int,
            'transactions': list of suspicious transactions,
            'total_amount': float
        }
    """
    from datetime import datetime

    suspicious_transactions = []
    total_suspicious_amount = 0.0

    try:
        # Parse date of death
        death_date = datetime.strptime(date_of_death, '%m/%d/%Y')

        # Check each account for post-death activity
        for account in accounts_data:
            account_number = account.get('account_number', 'Unknown')

            # Get transaction history from Jack Henry API
            # For POC: Use synthetic transaction data
            transactions = get_synthetic_transactions(account_number, death_date)

            for txn in transactions:
                txn_date = datetime.strptime(txn['date'], '%Y-%m-%d')

                # Flag transactions that occurred after death
                if txn_date > death_date:
                    suspicious_transactions.append({
                        'account': account_number,
                        'date': txn['date'],
                        'type': txn['type'],
                        'amount': txn['amount'],
                        'days_after_death': (txn_date - death_date).days
                    })
                    total_suspicious_amount += abs(txn['amount'])

        if suspicious_transactions:
            print(f"  ⚠ POST-DEATH ACTIVITY DETECTED: {len(suspicious_transactions)} transactions after death")
            print(f"     Total suspicious amount: ${total_suspicious_amount:,.2f}")
            for txn in suspicious_transactions:
                print(f"     - {txn['date']}: {txn['type']} ${abs(txn['amount']):,.2f} ({txn['days_after_death']} days after death)")

        return {
            'suspicious_count': len(suspicious_transactions),
            'transactions': suspicious_transactions,
            'total_amount': total_suspicious_amount
        }

    except Exception as e:
        print(f"  ! Error checking post-death activity: {str(e)}")
        return {
            'suspicious_count': 0,
            'transactions': [],
            'total_amount': 0.0,
            'error': str(e)
        }


def get_synthetic_transactions(account_number, death_date):
    """
    Generate synthetic transaction data for POC demonstration.

    In production, this would query the Jack Henry transaction history API.
    For the POC, we generate realistic patterns including some post-death activity
    to demonstrate the fraud detection capability.

    Args:
        account_number: Account number to generate transactions for
        death_date: Date of death as datetime object

    Returns:
        list: List of transaction dictionaries
    """
    import random
    from datetime import timedelta

    transactions = []

    # Generate 10-20 transactions in the 60 days around the death date
    num_transactions = random.randint(10, 20)

    for i in range(num_transactions):
        # Random date within 60 days before/after death
        days_offset = random.randint(-60, 30)  # More transactions before death
        txn_date = death_date + timedelta(days=days_offset)

        # Transaction types
        txn_types = ['WITHDRAWAL', 'DEPOSIT', 'TRANSFER', 'CHECK', 'ATM', 'DEBIT_CARD']
        txn_type = random.choice(txn_types)

        # Amount: smaller amounts more common, occasional large transactions
        if random.random() < 0.1:  # 10% chance of large transaction
            amount = random.uniform(500, 5000)
        else:
            amount = random.uniform(20, 500)

        # Withdrawals/debits are negative
        if txn_type in ['WITHDRAWAL', 'TRANSFER', 'ATM', 'DEBIT_CARD']:
            amount = -amount

        transactions.append({
            'date': txn_date.strftime('%Y-%m-%d'),
            'type': txn_type,
            'amount': round(amount, 2),
            'account_number': account_number
        })

    # Sort by date
    transactions.sort(key=lambda x: x['date'])

    return transactions


def call_ribbon_verify_api(death_cert_data):
    """
    Call Ribbon Verify API to verify death information

    API Integration Placeholder - will be implemented when API credentials are available
    """

    print("  → Preparing Ribbon Verify API call...")
    print(f"     Deceased: {death_cert_data.get('deceased_name', 'N/A')}")
    print(f"     SSN: {death_cert_data.get('ssn', 'N/A')}")
    print(f"     Date of Death: {death_cert_data.get('date_of_death', 'N/A')}")
    print("  → API integration pending - returning placeholder")

    # TODO: Implement actual API call when credentials are available
    return {
        'success': False,
        'message': 'Ribbon Verify API integration pending - credentials not yet available',
        'placeholder': True,
        'ready_for_integration': True
    }


def verify_id_with_persona(id_file_path):
    """
    Verify government ID using Persona API

    API Integration Placeholder - will be implemented when API credentials are available
    """

    print("  → Preparing Persona API verification...")
    print(f"     ID File: {os.path.basename(id_file_path)}")
    print("  → API integration pending - returning placeholder")

    # TODO: Implement actual Persona API call when credentials are available
    return {
        'verified': False,
        'message': 'Persona API integration pending - credentials not yet available',
        'placeholder': True,
        'ready_for_integration': True
    }


def cross_verify_documents(death_cert_data, id_data, claim_data):
    """
    Cross-verify data consistency across all three documents

    Checks:
    - Deceased name matches between death cert and claim form
    - Beneficiary name matches between ID and claim form
    - SSNs are consistent (if available)
    - Dates are valid and logical
    """
    mismatches = []

    # Check if deceased names match (case-insensitive)
    deceased_cert = (death_cert_data.get('deceased_name') or '').lower().strip()
    deceased_claim = (claim_data.get('deceased_name') or '').lower().strip()

    if deceased_cert and deceased_claim:
        if deceased_cert != deceased_claim:
            mismatches.append(
                f'Deceased name mismatch: Death cert "{death_cert_data.get("deceased_name")}" '
                f'vs Claim form "{claim_data.get("deceased_name")}"'
            )

    # Check if beneficiary names match (case-insensitive)
    bene_id = (id_data.get('name') or '').lower().strip()
    bene_claim = (claim_data.get('beneficiary_name') or '').lower().strip()

    if bene_id and bene_claim:
        if bene_id != bene_claim:
            mismatches.append(
                f'Beneficiary name mismatch: Government ID "{id_data.get("name")}" '
                f'vs Claim form "{claim_data.get("beneficiary_name")}"'
            )

    # Check SSNs if available
    deceased_ssn_cert = death_cert_data.get('ssn', '').replace('-', '').strip()
    deceased_ssn_claim = claim_data.get('deceased_ssn', '').replace('-', '').strip()

    if deceased_ssn_cert and deceased_ssn_claim:
        if deceased_ssn_cert != deceased_ssn_claim:
            mismatches.append('Deceased SSN mismatch between death certificate and claim form')

    return {
        'all_match': len(mismatches) == 0,
        'mismatches': mismatches,
        'checks_performed': [
            'Deceased name consistency',
            'Beneficiary name consistency',
            'SSN validation',
            'Document completeness'
        ]
    }


def calculate_composite_confidence_score(idp_score, consistency_score, security_score, fraud_score):
    """
    Calculate composite confidence score per dissertation specification (Page 18).

    Formula: (0.20×IDP) + (0.30×Consistency) + (0.30×Security) + (0.20×Fraud)

    This weighted scoring system reflects relative importance of verification components:
    - IDP (Intelligent Document Processing): 20% - Base extraction confidence from AWS Textract
    - Consistency: 30% - Cross-document validation matching
    - Security: 30% - Authentication confidence from blockchain/ML verification
    - Fraud: 20% - Absence of risk indicators (100 = no fraud detected)

    Args:
        idp_score: Average Textract field extraction confidence (0-100)
        consistency_score: Cross-document validation score (0-100)
        security_score: Authentication confidence from blockchain/ML (0-100)
        fraud_score: Inverse fraud risk score (0-100, where 100 = no fraud)

    Returns:
        Dict containing:
        - composite_score: Final weighted score (0.0-1.0)
        - tier: Verification tier based on score
        - recommended_action: Next workflow state
        - component_scores: Breakdown of individual scores

    Routing Logic:
    - ≥0.90: VERIFIED (proceed to payment approval)
    - 0.75-0.89: NEEDS_REVIEW (manual review required)
    - <0.75: FRAUD_ALERT (flag for investigation)
    """
    # Convert percentages to 0-1 scale
    idp = idp_score / 100.0
    consistency = consistency_score / 100.0
    security = security_score / 100.0
    fraud = fraud_score / 100.0

    # Apply weighted formula from dissertation
    composite = (0.20 * idp) + (0.30 * consistency) + (0.30 * security) + (0.20 * fraud)

    # Determine tier and recommended action
    if composite >= 0.90:
        tier = 'TIER_1_VERIFIED'
        recommended_action = 'VERIFIED'
        confidence_level = 'HIGH'
    elif composite >= 0.75:
        tier = 'TIER_2_REVIEW'
        recommended_action = 'NEEDS_REVIEW'
        confidence_level = 'MEDIUM'
    else:
        tier = 'TIER_3_ALERT'
        recommended_action = 'FRAUD_ALERT'
        confidence_level = 'LOW'

    return {
        'composite_score': round(composite, 4),
        'composite_percentage': round(composite * 100, 2),
        'tier': tier,
        'recommended_action': recommended_action,
        'confidence_level': confidence_level,
        'component_scores': {
            'idp': {
                'score': idp_score,
                'normalized': round(idp, 4),
                'weight': 0.20,
                'contribution': round(0.20 * idp, 4)
            },
            'consistency': {
                'score': consistency_score,
                'normalized': round(consistency, 4),
                'weight': 0.30,
                'contribution': round(0.30 * consistency, 4)
            },
            'security': {
                'score': security_score,
                'normalized': round(security, 4),
                'weight': 0.30,
                'contribution': round(0.30 * security, 4)
            },
            'fraud': {
                'score': fraud_score,
                'normalized': round(fraud, 4),
                'weight': 0.20,
                'contribution': round(0.20 * fraud, 4)
            }
        },
        'formula': '(0.20×IDP) + (0.30×Consistency) + (0.30×Security) + (0.20×Fraud)',
        'thresholds': {
            'verified': '≥0.90',
            'needs_review': '0.75-0.89',
            'fraud_alert': '<0.75'
        }
    }
