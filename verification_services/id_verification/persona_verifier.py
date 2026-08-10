"""
Persona ID Verification Integration
Implements real ID verification using Persona's API

Persona handles:
- Government ID verification (driver's licenses, state IDs, passports)
- Selfie capture + liveness detection
- AAMVA database lookup (for driver's licenses)
- Fraud detection
- Address verification
"""

import os
import requests
from typing import Dict, Optional
from datetime import datetime
import time

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.models import (
    VerificationResult, VerificationStatus, VerificationMethod,
    IDDocumentData
)


class PersonaIDVerifier:
    """
    Verifies government-issued IDs using Persona's API

    Supports:
    - Driver's licenses (all 50 states)
    - State ID cards
    - Passports
    - Selfie + liveness detection
    """

    def __init__(self):
        """Initialize Persona client"""
        self.api_key = os.getenv('PERSONA_API_KEY')
        self.base_url = 'https://withpersona.com/api/v1'
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Persona-Version': '2023-01-05'
        }

        if not self.api_key:
            raise ValueError("PERSONA_API_KEY environment variable not set")

    def verify_id_with_selfie(
        self,
        reference_id: str,
        expected_name: Optional[str] = None,
        expected_dob: Optional[str] = None
    ) -> VerificationResult:
        """
        Create a Persona inquiry for ID + selfie verification

        This creates a web link that the user visits to:
        1. Upload their government ID (front and back)
        2. Take a selfie with liveness detection
        3. Persona verifies everything automatically

        Args:
            reference_id: Your internal reference (e.g., case number)
            expected_name: Expected name on ID
            expected_dob: Expected date of birth

        Returns:
            VerificationResult with inquiry URL and session details
        """
        start_time = time.time()

        try:
            # Create inquiry
            inquiry_data = {
                'data': {
                    'attributes': {
                        'inquiry-template-id': os.getenv('PERSONA_TEMPLATE_ID'),
                        'reference-id': reference_id,
                        'note': f'BeneBridge verification for {reference_id}'
                    }
                }
            }

            # Add expected fields if provided
            if expected_name or expected_dob:
                inquiry_data['data']['attributes']['fields'] = {}
                if expected_name:
                    inquiry_data['data']['attributes']['fields']['name-first'] = expected_name.split()[0]
                    if len(expected_name.split()) > 1:
                        inquiry_data['data']['attributes']['fields']['name-last'] = expected_name.split()[-1]
                if expected_dob:
                    inquiry_data['data']['attributes']['fields']['birthdate'] = expected_dob

            response = requests.post(
                f'{self.base_url}/inquiries',
                json=inquiry_data,
                headers=self.headers
            )

            if response.status_code not in [200, 201]:
                return self._fail_result(start_time, f"Persona API error: {response.text}")

            result = response.json()
            inquiry_id = result['data']['id']
            inquiry_url = result['data']['attributes'].get('url')

            processing_time = (time.time() - start_time) * 1000

            return VerificationResult(
                status=VerificationStatus.PENDING,
                confidence_score=0.0,  # Will be updated when user completes
                method=VerificationMethod.PERSONA,
                processing_time_ms=processing_time,
                timestamp=datetime.now(),
                details={
                    'inquiry_id': inquiry_id,
                    'inquiry_url': inquiry_url,
                    'reference_id': reference_id,
                    'message': 'Send inquiry_url to user to complete verification'
                }
            )

        except Exception as e:
            return self._fail_result(start_time, f"Verification error: {str(e)}")

    def check_inquiry_status(self, inquiry_id: str) -> VerificationResult:
        """
        Check the status of a Persona inquiry

        Args:
            inquiry_id: Persona inquiry ID

        Returns:
            VerificationResult with current status and extracted data
        """
        start_time = time.time()

        try:
            # Get inquiry details
            response = requests.get(
                f'{self.base_url}/inquiries/{inquiry_id}',
                headers=self.headers
            )

            if response.status_code != 200:
                return self._fail_result(start_time, f"Failed to fetch inquiry: {response.text}")

            inquiry = response.json()['data']
            attributes = inquiry['attributes']

            # Get verification status
            status_str = attributes.get('status', 'pending')
            persona_status = {
                'completed': VerificationStatus.VERIFIED,
                'approved': VerificationStatus.VERIFIED,
                'declined': VerificationStatus.FAILED,
                'needs-review': VerificationStatus.NEEDS_REVIEW,
                'pending': VerificationStatus.PENDING,
                'expired': VerificationStatus.FAILED
            }.get(status_str, VerificationStatus.PENDING)

            # Extract verification details
            fields = attributes.get('fields', {})
            extracted_data = {
                'name_first': fields.get('name-first'),
                'name_last': fields.get('name-last'),
                'birthdate': fields.get('birthdate'),
                'address': fields.get('address-street-1'),
                'city': fields.get('address-city'),
                'state': fields.get('address-subdivision'),
                'postal_code': fields.get('address-postal-code'),
                'id_number': fields.get('identification-number'),
                'id_state': fields.get('identification-subdivision')
            }

            # Get verification checks
            verifications = self._get_verification_checks(inquiry_id)

            # Calculate confidence based on Persona's checks
            confidence_score = self._calculate_persona_confidence(attributes, verifications)

            processing_time = (time.time() - start_time) * 1000

            return VerificationResult(
                status=persona_status,
                confidence_score=confidence_score,
                method=VerificationMethod.PERSONA,
                processing_time_ms=processing_time,
                timestamp=datetime.now(),
                details={
                    'inquiry_id': inquiry_id,
                    'persona_status': status_str,
                    'extracted_data': extracted_data,
                    'verifications': verifications
                }
            )

        except Exception as e:
            return self._fail_result(start_time, f"Status check error: {str(e)}")

    def _get_verification_checks(self, inquiry_id: str) -> Dict:
        """Get all verification checks for an inquiry"""
        try:
            response = requests.get(
                f'{self.base_url}/inquiries/{inquiry_id}/verifications',
                headers=self.headers
            )

            if response.status_code != 200:
                return {}

            verifications = response.json()['data']
            checks = {}

            for verification in verifications:
                check_type = verification['type']
                attributes = verification['attributes']
                status = attributes.get('status')
                checks[check_type] = {
                    'status': status,
                    'checks': attributes.get('checks', [])
                }

            return checks

        except Exception:
            return {}

    def _calculate_persona_confidence(self, attributes: Dict, verifications: Dict) -> float:
        """Calculate confidence score based on Persona verification results"""
        score = 0.0

        # Base score from inquiry status
        status = attributes.get('status', 'pending')
        if status == 'approved':
            score = 90.0
        elif status == 'completed':
            score = 85.0
        elif status == 'needs-review':
            score = 60.0
        elif status == 'declined':
            score = 20.0
        else:
            return 0.0  # Pending or unknown

        # Boost score based on passed verifications
        verification_boost = 0

        for check_name, check_data in verifications.items():
            if check_data.get('status') == 'passed':
                if 'government-id' in check_name:
                    verification_boost += 5
                elif 'selfie' in check_name:
                    verification_boost += 3
                elif 'database' in check_name:
                    verification_boost += 2

        return min(100.0, score + verification_boost)

    def _fail_result(self, start_time: float, error_message: str) -> VerificationResult:
        """Helper to create failure result"""
        return VerificationResult(
            status=VerificationStatus.FAILED,
            confidence_score=0.0,
            method=VerificationMethod.PERSONA,
            processing_time_ms=(time.time() - start_time) * 1000,
            timestamp=datetime.now(),
            details={},
            error_message=error_message
        )


# Helper functions for easy import
def create_verification_inquiry(
    reference_id: str,
    expected_name: Optional[str] = None,
    expected_dob: Optional[str] = None
) -> VerificationResult:
    """
    Create a new Persona verification inquiry

    Returns a VerificationResult with the inquiry URL that should be sent to the user
    """
    verifier = PersonaIDVerifier()
    return verifier.verify_id_with_selfie(reference_id, expected_name, expected_dob)


def check_verification_status(inquiry_id: str) -> VerificationResult:
    """
    Check the status of an existing Persona inquiry
    """
    verifier = PersonaIDVerifier()
    return verifier.check_inquiry_status(inquiry_id)
