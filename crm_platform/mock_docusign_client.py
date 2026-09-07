#!/usr/bin/env python3
"""
Mock DocuSign Client
Simulates DocuSign eSignature API calls for death claim form signing
Follows real DocuSign API structure but returns mock data

In production, replace this with actual docusign-esign SDK:
    from docusign_esign import ApiClient, EnvelopesApi, EnvelopeDefinition
"""

import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, Optional

# NOTE: These would be real credentials in production
# Store in environment variables or secure vault
DOCUSIGN_INTEGRATION_KEY = ""  # Your Integration Key (Client ID)
DOCUSIGN_USER_ID = ""  # Your User ID
DOCUSIGN_ACCOUNT_ID = ""  # Your Account ID
DOCUSIGN_PRIVATE_KEY_PATH = ""  # Path to private RSA key
DOCUSIGN_BASE_PATH = "https://demo.docusign.net/restapi"  # Use https://www.docusign.net for production

class MockDocuSignClient:
    """
    Mock DocuSign client that simulates eSignature API

    Real implementation would use:
        from docusign_esign import ApiClient, EnvelopesApi, EnvelopeDefinition, Document, Signer, SignHere, Tabs, Recipients
    """

    def __init__(self):
        """Initialize mock DocuSign client"""
        self.base_path = DOCUSIGN_BASE_PATH
        self.account_id = DOCUSIGN_ACCOUNT_ID or "mock-account-12345"
        print(f"[Mock DocuSign Client] Initialized (Demo Mode)")
        print(f"  Base Path: {self.base_path}")
        print(f"  Account ID: {self.account_id}")

    def create_death_claim_envelope(
        self,
        case_id: str,
        beneficiary_name: str,
        beneficiary_email: str,
        deceased_name: str,
        claim_amount: float,
        accounts: list
    ) -> Dict:
        """
        Create DocuSign envelope for death claim form

        Real API call would be:
            envelope_api = EnvelopesApi(api_client)
            envelope_definition = EnvelopeDefinition(...)
            results = envelope_api.create_envelope(account_id, envelope_definition)

        Args:
            case_id: Death claim case ID
            beneficiary_name: Primary beneficiary name
            beneficiary_email: Beneficiary email for signing
            deceased_name: Name of deceased
            claim_amount: Total claim amount
            accounts: List of account dictionaries

        Returns:
            Dict with envelope_id, status, and signing_url
        """

        # In production, this would make actual API call to DocuSign
        # For now, simulate the response

        envelope_id = str(uuid.uuid4())
        created_date = datetime.utcnow().isoformat() + 'Z'

        # Simulate DocuSign envelope creation
        mock_response = {
            'envelope_id': envelope_id,
            'status': 'sent',
            'status_datetime': created_date,
            'email_subject': f'Death Claim Form - {deceased_name} (Case: {case_id})',
            'email_blurb': f'Please review and sign the death claim form for the estate of {deceased_name}.',
            'documents': [
                {
                    'document_id': '1',
                    'name': 'Death Claim Beneficiary Form',
                    'type': 'pdf',
                    'order': '1'
                }
            ],
            'recipients': {
                'signers': [
                    {
                        'recipient_id': '1',
                        'recipient_type': 'signer',
                        'name': beneficiary_name,
                        'email': beneficiary_email,
                        'routing_order': '1',
                        'status': 'sent',
                        'delivery_method': 'email'
                    }
                ]
            },
            'custom_fields': {
                'text_custom_fields': [
                    {'name': 'case_id', 'value': case_id},
                    {'name': 'deceased_name', 'value': deceased_name},
                    {'name': 'claim_amount', 'value': str(claim_amount)}
                ]
            }
        }

        # Generate mock signing URL (in production, use RecipientViewRequest)
        signing_url = self._generate_mock_signing_url(envelope_id, beneficiary_email)

        print(f"[Mock DocuSign] Created envelope {envelope_id}")
        print(f"  Case: {case_id}")
        print(f"  Beneficiary: {beneficiary_name} ({beneficiary_email})")
        print(f"  Amount: ${claim_amount:,.2f}")

        return {
            'success': True,
            'envelope_id': envelope_id,
            'status': 'sent',
            'created_datetime': created_date,
            'signing_url': signing_url,
            'email_subject': mock_response['email_subject'],
            'recipients': mock_response['recipients'],
            'expires_datetime': (datetime.utcnow() + timedelta(days=120)).isoformat() + 'Z'
        }

    def _generate_mock_signing_url(self, envelope_id: str, recipient_email: str) -> str:
        """
        Generate mock signing URL

        Real API call would be:
            recipient_view_request = RecipientViewRequest(
                authentication_method='email',
                client_user_id=recipient_email,
                recipient_id='1',
                return_url='https://yourapp.com/signing-complete',
                user_name=recipient_name,
                email=recipient_email
            )
            view_url = envelope_api.create_recipient_view(account_id, envelope_id, recipient_view_request)
        """
        # Mock URL format similar to real DocuSign
        return f"https://demo.docusign.net/Signing/MTRedeem/v1/{envelope_id}?slt=mock-token"

    def get_envelope_status(self, envelope_id: str) -> Dict:
        """
        Get status of DocuSign envelope

        Real API call would be:
            envelope_api = EnvelopesApi(api_client)
            envelope = envelope_api.get_envelope(account_id, envelope_id)
        """
        # Simulate various statuses based on envelope age
        # In production, this would query DocuSign API

        statuses = ['sent', 'delivered', 'signed', 'completed']

        mock_status = {
            'envelope_id': envelope_id,
            'status': 'sent',  # Would be actual status from API
            'status_datetime': datetime.utcnow().isoformat() + 'Z',
            'sent_datetime': (datetime.utcnow() - timedelta(hours=2)).isoformat() + 'Z',
            'delivered_datetime': None,
            'signed_datetime': None,
            'completed_datetime': None,
            'declined_datetime': None,
            'voided_datetime': None,
            'is_completed': False,
            'recipients': {
                'signers': [
                    {
                        'status': 'sent',
                        'signed_datetime': None
                    }
                ]
            }
        }

        return mock_status

    def download_completed_document(self, envelope_id: str) -> Optional[bytes]:
        """
        Download signed document from DocuSign

        Real API call would be:
            envelope_api = EnvelopesApi(api_client)
            document = envelope_api.get_document(account_id, envelope_id, document_id)
        """
        # In production, this would download the actual signed PDF
        # For now, return None or mock PDF bytes

        print(f"[Mock DocuSign] Would download document for envelope {envelope_id}")
        return None

    def void_envelope(self, envelope_id: str, reason: str) -> Dict:
        """
        Void a DocuSign envelope

        Real API call would be:
            envelope_api = EnvelopesApi(api_client)
            envelope = Envelope(status='voided', voided_reason=reason)
            result = envelope_api.update(account_id, envelope_id, envelope)
        """
        return {
            'success': True,
            'envelope_id': envelope_id,
            'status': 'voided',
            'voided_datetime': datetime.utcnow().isoformat() + 'Z',
            'voided_reason': reason
        }

    def resend_envelope(self, envelope_id: str) -> Dict:
        """
        Resend DocuSign envelope notification

        Real API call would be:
            envelope_api = EnvelopesApi(api_client)
            envelope_api.update_recipients(account_id, envelope_id, recipients)
        """
        return {
            'success': True,
            'envelope_id': envelope_id,
            'status': 'sent',
            'resent_datetime': datetime.utcnow().isoformat() + 'Z'
        }


# Factory function for Flask app
def create_docusign_client() -> MockDocuSignClient:
    """Create DocuSign client instance"""
    return MockDocuSignClient()


# Test function
if __name__ == '__main__':
    print("="*60)
    print("MOCK DOCUSIGN CLIENT - TEST")
    print("="*60 + "\n")

    client = MockDocuSignClient()

    # Test: Create death claim envelope
    print("\nTest: Create Death Claim Envelope")
    print("="*60)

    result = client.create_death_claim_envelope(
        case_id='DC-20260817-143052',
        beneficiary_name='Sarah Thompson',
        beneficiary_email='sarah.thompson@example.com',
        deceased_name='Jennifer Thompson',
        claim_amount=125750.50,
        accounts=[
            {'type': 'CHECKING', 'balance': 45250.00},
            {'type': 'SAVINGS', 'balance': 30500.50},
            {'type': 'IRA', 'balance': 50000.00}
        ]
    )

    if result['success']:
        print(f"\n✓ Envelope created successfully!")
        print(f"  Envelope ID: {result['envelope_id']}")
        print(f"  Status: {result['status']}")
        print(f"  Signing URL: {result['signing_url'][:80]}...")
        print(f"  Expires: {result['expires_datetime']}")

    # Test: Get envelope status
    print("\n" + "="*60)
    print("Test: Get Envelope Status")
    print("="*60)

    status = client.get_envelope_status(result['envelope_id'])
    print(f"\nEnvelope Status: {status['status']}")
    print(f"Sent: {status['sent_datetime']}")

    print("\n" + "="*60)
    print("Mock DocuSign client ready for integration!")
    print("="*60 + "\n")
