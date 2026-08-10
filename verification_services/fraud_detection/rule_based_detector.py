"""
Rule-Based Fraud Detection
Implements Chapter 5 rule-based fraud signals and pattern detection

Detects suspicious patterns using business rules and heuristics
"""

import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.models import FraudIndicator, VerificationResult, VerificationStatus, VerificationMethod


class RuleBasedFraudDetector:
    """
    Rule-based fraud detection system

    Per Chapter 5, detects:
    - Relationship fraud (beneficiary-deceased relationship)
    - Velocity patterns (multiple claims in short period)
    - Geographic anomalies (unusual locations)
    - Amount anomalies (unusually high claims)
    - Document inconsistencies
    - Beneficiary patterns (same beneficiary, multiple deaths)
    - Timing anomalies (claim filed too quickly/slowly after death)
    """

    def __init__(self, historical_claims_db: Optional[Dict] = None):
        """
        Initialize rule-based detector

        Args:
            historical_claims_db: Database of historical claims for pattern analysis
        """
        self.historical_claims = historical_claims_db or {}
        self.fraud_rules = self._initialize_rules()

    def detect_fraud(self, case_data: Dict) -> Dict:
        """
        Run all fraud detection rules on a case

        Args:
            case_data: Dictionary containing case information

        Returns:
            Dictionary with fraud assessment results
        """
        start_time = time.time()

        indicators = []
        fraud_score = 0.0

        # Rule 1: Relationship Fraud
        relationship_check = self._check_relationship_fraud(case_data)
        if relationship_check['suspicious']:
            indicators.append(relationship_check['indicator'])
            fraud_score += relationship_check['indicator'].confidence

        # Rule 2: Velocity Patterns
        velocity_check = self._check_velocity_patterns(case_data)
        if velocity_check['suspicious']:
            indicators.append(velocity_check['indicator'])
            fraud_score += velocity_check['indicator'].confidence

        # Rule 3: Geographic Anomalies
        geo_check = self._check_geographic_anomalies(case_data)
        if geo_check['suspicious']:
            indicators.append(geo_check['indicator'])
            fraud_score += geo_check['indicator'].confidence

        # Rule 4: Amount Anomalies
        amount_check = self._check_amount_anomalies(case_data)
        if amount_check['suspicious']:
            indicators.append(amount_check['indicator'])
            fraud_score += amount_check['indicator'].confidence

        # Rule 5: Document Inconsistencies
        doc_check = self._check_document_inconsistencies(case_data)
        if doc_check['suspicious']:
            indicators.append(doc_check['indicator'])
            fraud_score += doc_check['indicator'].confidence

        # Rule 6: Beneficiary Patterns
        beneficiary_check = self._check_beneficiary_patterns(case_data)
        if beneficiary_check['suspicious']:
            indicators.append(beneficiary_check['indicator'])
            fraud_score += beneficiary_check['indicator'].confidence

        # Rule 7: Timing Anomalies
        timing_check = self._check_timing_anomalies(case_data)
        if timing_check['suspicious']:
            indicators.append(timing_check['indicator'])
            fraud_score += timing_check['indicator'].confidence

        # Rule 8: Sanctions/PEP Screening
        sanctions_check = self._check_sanctions_lists(case_data)
        if sanctions_check['suspicious']:
            indicators.append(sanctions_check['indicator'])
            fraud_score += sanctions_check['indicator'].confidence

        # Normalize fraud score (0-100)
        # Cap at 100 even if multiple high-confidence indicators
        normalized_score = min(100, fraud_score)

        # Determine risk level
        if normalized_score >= 80:
            risk_level = 'high'
            recommendation = 'REJECT'
        elif normalized_score >= 50:
            risk_level = 'medium'
            recommendation = 'MANUAL_REVIEW'
        elif normalized_score >= 20:
            risk_level = 'low'
            recommendation = 'ENHANCED_VERIFICATION'
        else:
            risk_level = 'minimal'
            recommendation = 'PROCEED'

        processing_time = (time.time() - start_time) * 1000

        return {
            'fraud_detected': len(indicators) > 0,
            'fraud_score': normalized_score,
            'risk_level': risk_level,
            'recommendation': recommendation,
            'indicators': [ind.__dict__ for ind in indicators],
            'num_indicators': len(indicators),
            'processing_time_ms': processing_time,
            'timestamp': datetime.now().isoformat()
        }

    def _check_relationship_fraud(self, case_data: Dict) -> Dict:
        """
        Check for suspicious beneficiary-deceased relationships

        Red flags:
        - Non-relative beneficiary for large account
        - Estranged family member suddenly appearing
        - Beneficiary added/changed recently before death
        - No documented relationship
        """
        suspicious = False
        confidence = 0.0
        description = ""

        relationship = case_data.get('beneficiary_relationship', '').lower()
        account_balance = case_data.get('account_balance', 0)
        beneficiary_designation_date = case_data.get('beneficiary_designation_date')

        # High-value account with non-relative beneficiary
        if account_balance > 100000 and relationship in ['friend', 'other', 'unrelated']:
            suspicious = True
            confidence = 40.0
            description = f"Non-relative beneficiary for ${account_balance:,.0f} account"

        # Check if beneficiary was added/changed recently before death
        if beneficiary_designation_date:
            try:
                designation_date = datetime.fromisoformat(beneficiary_designation_date)
                death_date = datetime.fromisoformat(case_data.get('date_of_death', ''))
                days_before_death = (death_date - designation_date).days

                # Beneficiary changed within 90 days of death - suspicious
                if 0 < days_before_death < 90:
                    suspicious = True
                    confidence = 60.0
                    description = f"Beneficiary designated {days_before_death} days before death"
            except:
                pass

        indicator = FraudIndicator(
            indicator_type='relationship_fraud',
            severity='high' if confidence >= 60 else 'medium' if confidence >= 30 else 'low',
            description=description,
            confidence=confidence
        )

        return {
            'suspicious': suspicious,
            'indicator': indicator
        }

    def _check_velocity_patterns(self, case_data: Dict) -> Dict:
        """
        Check for velocity anomalies (multiple claims in short period)

        Red flags:
        - Same beneficiary, multiple death claims in short period
        - Same address, multiple unrelated claims
        - Same IP address, multiple claim submissions
        """
        suspicious = False
        confidence = 0.0
        description = ""

        beneficiary_ssn = case_data.get('beneficiary_ssn')
        submission_date = case_data.get('submission_date')

        if beneficiary_ssn and beneficiary_ssn in self.historical_claims:
            recent_claims = [
                claim for claim in self.historical_claims[beneficiary_ssn]
                if self._is_recent(claim['submission_date'], days=180)
            ]

            if len(recent_claims) >= 2:
                suspicious = True
                confidence = 70.0
                description = f"Beneficiary has {len(recent_claims)} claims in past 180 days"

        indicator = FraudIndicator(
            indicator_type='velocity_pattern',
            severity='high' if confidence >= 60 else 'medium' if confidence >= 30 else 'low',
            description=description,
            confidence=confidence
        )

        return {
            'suspicious': suspicious,
            'indicator': indicator
        }

    def _check_geographic_anomalies(self, case_data: Dict) -> Dict:
        """
        Check for geographic inconsistencies

        Red flags:
        - Death location far from account holder's address
        - Beneficiary in different country than deceased
        - Claim submitted from unusual location (VPN, foreign IP)
        """
        suspicious = False
        confidence = 0.0
        description = ""

        deceased_state = case_data.get('deceased_state', '')
        place_of_death = case_data.get('place_of_death', '')
        beneficiary_state = case_data.get('beneficiary_state', '')

        # Cross-country beneficiary (potential flag for large accounts)
        if deceased_state and beneficiary_state:
            if deceased_state != beneficiary_state:
                account_balance = case_data.get('account_balance', 0)
                if account_balance > 50000:
                    suspicious = True
                    confidence = 25.0
                    description = f"Beneficiary in {beneficiary_state}, deceased in {deceased_state}"

        indicator = FraudIndicator(
            indicator_type='geographic_anomaly',
            severity='medium' if confidence >= 30 else 'low',
            description=description,
            confidence=confidence
        )

        return {
            'suspicious': suspicious,
            'indicator': indicator
        }

    def _check_amount_anomalies(self, case_data: Dict) -> Dict:
        """
        Check for unusual account amounts

        Red flags:
        - Amount much higher than typical for deceased's age/occupation
        - Round numbers (possible fabrication)
        - Account value changed significantly before death
        """
        suspicious = False
        confidence = 0.0
        description = ""

        account_balance = case_data.get('account_balance', 0)
        account_type = case_data.get('account_type', '')

        # Very high amounts warrant scrutiny
        if account_balance > 500000:
            suspicious = True
            confidence = 30.0
            description = f"High-value claim: ${account_balance:,.0f}"

        # Suspicious round numbers
        if account_balance > 0 and account_balance % 10000 == 0:
            confidence += 15.0
            description += f" (round number)"

        indicator = FraudIndicator(
            indicator_type='amount_anomaly',
            severity='medium' if confidence >= 30 else 'low',
            description=description,
            confidence=confidence
        )

        return {
            'suspicious': suspicious,
            'indicator': indicator
        }

    def _check_document_inconsistencies(self, case_data: Dict) -> Dict:
        """
        Check for document-level inconsistencies

        Red flags:
        - Name mismatch between death cert and account
        - SSN mismatch
        - Date inconsistencies
        - Missing required documents
        """
        suspicious = False
        confidence = 0.0
        description = ""

        # Check for name mismatches
        deceased_name_account = case_data.get('deceased_name', '').lower()
        deceased_name_cert = case_data.get('death_cert_name', '').lower()

        if deceased_name_account and deceased_name_cert:
            if deceased_name_account != deceased_name_cert:
                suspicious = True
                confidence = 50.0
                description = "Name mismatch between account and death certificate"

        # Check date consistency
        date_of_death = case_data.get('date_of_death')
        account_last_activity = case_data.get('account_last_activity')

        if date_of_death and account_last_activity:
            try:
                dod = datetime.fromisoformat(date_of_death)
                last_activity = datetime.fromisoformat(account_last_activity)

                # Activity after death is highly suspicious
                if last_activity > dod:
                    suspicious = True
                    confidence = 80.0
                    description = "Account activity after reported death date"
            except:
                pass

        indicator = FraudIndicator(
            indicator_type='document_inconsistency',
            severity='high' if confidence >= 60 else 'medium' if confidence >= 30 else 'low',
            description=description,
            confidence=confidence
        )

        return {
            'suspicious': suspicious,
            'indicator': indicator
        }

    def _check_beneficiary_patterns(self, case_data: Dict) -> Dict:
        """
        Check for suspicious beneficiary patterns

        Red flags:
        - Same beneficiary for multiple unrelated deceased persons
        - Professional beneficiary (appears in many claims)
        - Beneficiary is caregiver/power of attorney
        """
        suspicious = False
        confidence = 0.0
        description = ""

        beneficiary_name = case_data.get('beneficiary_name', '')

        # Check if beneficiary appears in multiple unrelated claims
        if beneficiary_name:
            # In production, query historical claims database
            # For now, simulate check
            num_claims_as_beneficiary = 0  # Would be queried from DB

            if num_claims_as_beneficiary >= 3:
                suspicious = True
                confidence = 65.0
                description = f"Beneficiary appears in {num_claims_as_beneficiary} unrelated claims"

        indicator = FraudIndicator(
            indicator_type='beneficiary_pattern',
            severity='high' if confidence >= 60 else 'medium' if confidence >= 30 else 'low',
            description=description,
            confidence=confidence
        )

        return {
            'suspicious': suspicious,
            'indicator': indicator
        }

    def _check_timing_anomalies(self, case_data: Dict) -> Dict:
        """
        Check for suspicious timing patterns

        Red flags:
        - Claim filed within days of death (unusually fast)
        - Claim filed years after death (why the delay?)
        - Multiple claims on same day
        """
        suspicious = False
        confidence = 0.0
        description = ""

        date_of_death = case_data.get('date_of_death')
        submission_date = case_data.get('submission_date')

        if date_of_death and submission_date:
            try:
                dod = datetime.fromisoformat(date_of_death)
                sub = datetime.fromisoformat(submission_date)
                days_between = (sub - dod).days

                # Claim filed suspiciously fast (< 3 days)
                if 0 <= days_between < 3:
                    suspicious = True
                    confidence = 45.0
                    description = f"Claim filed {days_between} days after death (unusually fast)"

                # Claim filed very late (> 2 years)
                elif days_between > 730:
                    suspicious = True
                    confidence = 35.0
                    description = f"Claim filed {days_between} days after death (unusual delay)"
            except:
                pass

        indicator = FraudIndicator(
            indicator_type='timing_anomaly',
            severity='medium' if confidence >= 30 else 'low',
            description=description,
            confidence=confidence
        )

        return {
            'suspicious': suspicious,
            'indicator': indicator
        }

    def _check_sanctions_lists(self, case_data: Dict) -> Dict:
        """
        Check beneficiary against sanctions and watchlists

        Lists to check:
        - OFAC (Office of Foreign Assets Control)
        - PEP (Politically Exposed Persons)
        - Interpol wanted lists
        - Fraud databases
        """
        suspicious = False
        confidence = 0.0
        description = ""

        beneficiary_name = case_data.get('beneficiary_name', '')

        # In production, query OFAC API, PEP databases
        # For now, simulate check
        on_sanctions_list = False  # Would be actual API check
        is_pep = False  # Would be actual database check

        if on_sanctions_list:
            suspicious = True
            confidence = 100.0
            description = "Beneficiary appears on OFAC sanctions list"

        if is_pep:
            suspicious = True
            confidence = 40.0
            description = "Beneficiary is Politically Exposed Person (enhanced due diligence required)"

        indicator = FraudIndicator(
            indicator_type='sanctions_screening',
            severity='high' if confidence >= 60 else 'medium' if confidence >= 30 else 'low',
            description=description,
            confidence=confidence
        )

        return {
            'suspicious': suspicious,
            'indicator': indicator
        }

    def _initialize_rules(self) -> List[Dict]:
        """Initialize fraud detection rules configuration"""
        return [
            {
                'rule_id': 'REL-001',
                'name': 'Non-Relative High-Value Beneficiary',
                'threshold': 100000,
                'confidence': 40
            },
            {
                'rule_id': 'VEL-001',
                'name': 'Multiple Claims Same Beneficiary',
                'threshold': 2,
                'lookback_days': 180,
                'confidence': 70
            },
            {
                'rule_id': 'AMT-001',
                'name': 'High-Value Claim',
                'threshold': 500000,
                'confidence': 30
            },
            {
                'rule_id': 'TIM-001',
                'name': 'Rapid Claim Filing',
                'threshold_days': 3,
                'confidence': 45
            },
            {
                'rule_id': 'DOC-001',
                'name': 'Activity After Death',
                'confidence': 80
            }
        ]

    def _is_recent(self, date_str: str, days: int) -> bool:
        """Check if date is within last N days"""
        try:
            date = datetime.fromisoformat(date_str)
            return (datetime.now() - date).days <= days
        except:
            return False
