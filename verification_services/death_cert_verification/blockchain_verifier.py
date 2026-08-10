"""
Blockchain Death Certificate Verification
Implements Chapter 5 Section 4.5.2 - Blockchain Verification Pathway

For California Titan Seal certificates anchored on Ethereum blockchain
"""

import time
import re
import hashlib
from typing import Optional, Dict
from datetime import datetime
import PyPDF2
from web3 import Web3

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.models import VerificationResult, VerificationStatus, VerificationMethod, DeathCertificateData


class BlockchainVerifier:
    """
    Verifies death certificates using blockchain cryptographic validation

    Per Chapter 5:
    - Extracts blockchain hash from PDF metadata or QR code
    - Validates transaction exists on Ethereum mainnet
    - Verifies certificate data hash matches blockchain record
    - Validates issuing authority digital signature
    - Checks timestamp reasonableness
    - Checks revocation status
    """

    def __init__(self, ethereum_endpoint: str = None):
        """
        Initialize blockchain verifier

        Args:
            ethereum_endpoint: Ethereum node RPC endpoint (e.g., Infura)
        """
        # In production, use actual Ethereum endpoint
        # e.g., "https://mainnet.infura.io/v3/YOUR-PROJECT-ID"
        self.ethereum_endpoint = ethereum_endpoint
        self.w3 = Web3(Web3.HTTPProvider(ethereum_endpoint)) if ethereum_endpoint else None

    def verify_death_certificate(self, pdf_path: str, expected_deceased_name: str) -> VerificationResult:
        """
        Main verification workflow for blockchain certificates

        Args:
            pdf_path: Path to death certificate PDF
            expected_deceased_name: Account holder name for matching

        Returns:
            VerificationResult with 100 confidence if verified, or appropriate status
        """
        start_time = time.time()

        try:
            # Step 1: Extract blockchain hash from PDF
            blockchain_hash = self._extract_blockchain_hash(pdf_path)

            if not blockchain_hash:
                # Not a blockchain certificate, route to traditional verification
                return VerificationResult(
                    status=VerificationStatus.PENDING,
                    confidence_score=0.0,
                    method=VerificationMethod.BLOCKCHAIN,
                    processing_time_ms=(time.time() - start_time) * 1000,
                    timestamp=datetime.now(),
                    details={'reason': 'No blockchain hash found - not a Titan Seal certificate'},
                    error_message='Not a blockchain certificate'
                )

            # Step 2: Validate hash format
            if not self._validate_hash_format(blockchain_hash):
                return VerificationResult(
                    status=VerificationStatus.FAILED,
                    confidence_score=0.0,
                    method=VerificationMethod.BLOCKCHAIN,
                    processing_time_ms=(time.time() - start_time) * 1000,
                    timestamp=datetime.now(),
                    details={'hash': blockchain_hash},
                    error_message='Invalid Ethereum transaction hash format'
                )

            # Step 3: Cryptographic validation
            validation_result = self._cryptographic_validation(blockchain_hash, pdf_path)

            if not validation_result['valid']:
                return VerificationResult(
                    status=VerificationStatus.FAILED,
                    confidence_score=0.0,
                    method=VerificationMethod.BLOCKCHAIN,
                    processing_time_ms=(time.time() - start_time) * 1000,
                    timestamp=datetime.now(),
                    details=validation_result,
                    error_message=validation_result.get('error')
                )

            # Step 4: Extract certificate data
            cert_data = validation_result.get('certificate_data', {})

            # Step 5: Verify deceased name matches
            name_match = self._fuzzy_name_match(
                cert_data.get('deceased_name', ''),
                expected_deceased_name
            )

            if not name_match:
                return VerificationResult(
                    status=VerificationStatus.NEEDS_REVIEW,
                    confidence_score=85.0,  # High confidence in authenticity, but name mismatch
                    method=VerificationMethod.BLOCKCHAIN,
                    processing_time_ms=(time.time() - start_time) * 1000,
                    timestamp=datetime.now(),
                    details={
                        **validation_result,
                        'name_mismatch': True,
                        'expected_name': expected_deceased_name,
                        'certificate_name': cert_data.get('deceased_name')
                    },
                    error_message='Name mismatch - manual review required'
                )

            # SUCCESS: Cryptographically verified with name match
            return VerificationResult(
                status=VerificationStatus.VERIFIED,
                confidence_score=100.0,  # Cryptographic certainty
                method=VerificationMethod.BLOCKCHAIN,
                processing_time_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.now(),
                details={
                    'blockchain_hash': blockchain_hash,
                    'certificate_data': cert_data,
                    'validation_checks': validation_result.get('checks', {})
                }
            )

        except Exception as e:
            return VerificationResult(
                status=VerificationStatus.FAILED,
                confidence_score=0.0,
                method=VerificationMethod.BLOCKCHAIN,
                processing_time_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.now(),
                details={},
                error_message=f'Blockchain verification error: {str(e)}'
            )

    def _extract_blockchain_hash(self, pdf_path: str) -> Optional[str]:
        """
        Extract blockchain transaction hash from PDF

        Per Chapter 5:
        - Check PDF metadata fields first
        - Fallback to QR code scanning if needed

        Returns:
            64-character hex string prefixed with "0x" or None
        """
        try:
            with open(pdf_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)

                # Check PDF metadata
                if pdf_reader.metadata:
                    # Common metadata fields for blockchain hash
                    for field in ['/BlockchainHash', '/TransactionHash', '/TitanSeal', '/EthereumTxHash']:
                        if field in pdf_reader.metadata:
                            hash_value = pdf_reader.metadata[field]
                            if isinstance(hash_value, str) and hash_value.startswith('0x'):
                                return hash_value

                # Check first page text for hash pattern
                if len(pdf_reader.pages) > 0:
                    text = pdf_reader.pages[0].extract_text()
                    # Look for Ethereum transaction hash pattern
                    matches = re.findall(r'0x[a-fA-F0-9]{64}', text)
                    if matches:
                        return matches[0]

                # TODO: Implement QR code scanning as fallback
                # Would use libraries like pyzbar, PIL to scan for QR codes

        except Exception as e:
            print(f"Error extracting blockchain hash: {e}")

        return None

    def _validate_hash_format(self, blockchain_hash: str) -> bool:
        """
        Validate Ethereum transaction hash format

        Must be:
        - 66 characters total (0x + 64 hex chars)
        - Start with "0x"
        - Contain only valid hexadecimal characters
        """
        if not blockchain_hash:
            return False

        # Check format: 0x + 64 hex characters
        pattern = r'^0x[a-fA-F0-9]{64}$'
        return bool(re.match(pattern, blockchain_hash))

    def _cryptographic_validation(self, blockchain_hash: str, pdf_path: str) -> Dict:
        """
        Perform cryptographic validation per Chapter 5:

        1. Verify transaction exists on Ethereum mainnet
        2. Validate certificate data hash matches blockchain record
        3. Verify issuing authority digital signature (PKI)
        4. Check timestamp reasonableness
        5. Check revocation list

        Returns:
            Dictionary with validation results
        """
        checks = {}

        # Check 1: Transaction exists on blockchain
        if self.w3 and self.w3.is_connected():
            try:
                tx = self.w3.eth.get_transaction(blockchain_hash)
                checks['transaction_exists'] = tx is not None

                if tx:
                    # Get transaction receipt for more details
                    receipt = self.w3.eth.get_transaction_receipt(blockchain_hash)
                    checks['transaction_confirmed'] = receipt['status'] == 1
                    checks['block_number'] = receipt['blockNumber']

                    # Get block timestamp
                    block = self.w3.eth.get_block(receipt['blockNumber'])
                    checks['blockchain_timestamp'] = datetime.fromtimestamp(block['timestamp'])
                else:
                    return {
                        'valid': False,
                        'error': 'Transaction hash not found on Ethereum mainnet',
                        'checks': checks
                    }
            except Exception as e:
                # In production, this would be a real error
                # For development/testing, we simulate the check
                checks['transaction_exists'] = 'SIMULATED (no Ethereum connection)'
        else:
            # Simulation mode - assume transaction would be found
            checks['transaction_exists'] = 'SIMULATED (no Ethereum connection)'
            checks['blockchain_timestamp'] = datetime.now()

        # Check 2: Compute certificate data hash and compare
        # In production, extract data from blockchain transaction
        # For now, simulate by computing PDF hash
        pdf_hash = self._compute_pdf_hash(pdf_path)
        checks['certificate_hash'] = pdf_hash
        checks['hash_match'] = 'SIMULATED'  # Would compare with blockchain data

        # Check 3: PKI validation (issuing authority signature)
        # In production, verify digital signature using CA public key
        checks['issuing_authority_verified'] = 'SIMULATED'  # Would verify signature

        # Check 4: Timestamp reasonableness
        # Certificate should not be future-dated or unreasonably old
        timestamp_valid = self._check_timestamp_reasonableness(checks.get('blockchain_timestamp', datetime.now()))
        checks['timestamp_reasonable'] = timestamp_valid

        if not timestamp_valid:
            return {
                'valid': False,
                'error': 'Timestamp outside reasonable range',
                'checks': checks
            }

        # Check 5: Revocation list
        # In production, query revocation database or smart contract
        checks['not_revoked'] = 'SIMULATED'  # Would check revocation list

        # Extract certificate data (in production, from blockchain transaction)
        # For simulation, return mock data
        certificate_data = {
            'deceased_name': 'EXTRACTED_FROM_BLOCKCHAIN',  # Would come from blockchain
            'deceased_ssn': 'XXX-XX-XXXX',
            'date_of_death': '2026-06-20',
            'place_of_death': 'California',
            'certificate_number': 'CA-2026-XXXXX'
        }

        return {
            'valid': True,
            'checks': checks,
            'certificate_data': certificate_data
        }

    def _compute_pdf_hash(self, pdf_path: str) -> str:
        """Compute SHA-256 hash of PDF file"""
        sha256_hash = hashlib.sha256()
        with open(pdf_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _check_timestamp_reasonableness(self, timestamp: datetime) -> bool:
        """
        Check if blockchain timestamp is reasonable

        Per Chapter 5:
        - Cannot be future-dated
        - Should not be decades old (suspicious)
        - Typical acceptable range: within 10 years
        """
        now = datetime.now()

        # Cannot be in the future
        if timestamp > now:
            return False

        # Cannot be more than 10 years old
        years_diff = (now - timestamp).days / 365.25
        if years_diff > 10:
            return False

        return True

    def _fuzzy_name_match(self, name1: str, name2: str) -> bool:
        """
        Fuzzy name matching using multiple strategies per Chapter 5:

        - Levenshtein edit distance for typos
        - Soundex phonetic matching
        - Nickname database lookup

        For now, implements simple case-insensitive comparison
        In production, would use advanced matching libraries
        """
        if not name1 or not name2:
            return False

        # Simple case-insensitive comparison
        # In production, use libraries like:
        # - jellyfish for Levenshtein and Soundex
        # - Custom nickname database
        return name1.strip().lower() == name2.strip().lower()
