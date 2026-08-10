"""
ID Document Analysis and Verification
Implements Chapter 5 identity verification through document authenticity checking

Verifies driver's licenses, state IDs, and other government-issued identification
"""

import time
import re
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
from PIL import Image
import pdf2image
import pytesseract

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.models import (
    VerificationResult, VerificationStatus, VerificationMethod,
    IDDocumentData, DocumentQualityMetrics
)


class IDDocumentAnalyzer:
    """
    Analyzes and verifies government-issued ID documents

    Per Chapter 5:
    - Document authenticity checking (security features, tampering)
    - Data extraction via OCR
    - Format validation (state-specific patterns)
    - Expiration checking
    - Barcode/magnetic stripe validation
    - AAMVA database verification (for driver's licenses)
    """

    def __init__(self):
        """Initialize ID document analyzer"""
        # State-specific ID patterns and security features
        self.state_patterns = self._load_state_patterns()

    def verify_id_document(
        self,
        image_path: str,
        expected_name: Optional[str] = None,
        expected_dob: Optional[str] = None
    ) -> VerificationResult:
        """
        Main verification workflow for ID documents

        Args:
            image_path: Path to ID image (front)
            expected_name: Expected name for matching
            expected_dob: Expected date of birth for matching

        Returns:
            VerificationResult with confidence score
        """
        start_time = time.time()

        try:
            # Step 1: Load and analyze image quality
            image = self._load_image(image_path)
            if image is None:
                return self._fail_result(start_time, "Could not load image")

            quality_metrics = self._assess_document_quality(image)

            if quality_metrics.overall_quality_score < 50:
                return VerificationResult(
                    status=VerificationStatus.NEEDS_REVIEW,
                    confidence_score=quality_metrics.overall_quality_score,
                    method=VerificationMethod.COMPUTER_VISION,
                    processing_time_ms=(time.time() - start_time) * 1000,
                    timestamp=datetime.now(),
                    details={'quality_metrics': quality_metrics.__dict__},
                    error_message='ID image quality too poor for automated verification'
                )

            # Step 2: Extract data via OCR
            extracted_data = self._extract_id_data(image)

            if not extracted_data:
                return self._fail_result(start_time, "Could not extract ID data")

            # Step 3: Validate document format and security features
            validation_results = self._validate_id_format(extracted_data, image)

            # Step 4: Check expiration
            is_expired = self._check_expiration(extracted_data.expiration_date)

            if is_expired:
                return VerificationResult(
                    status=VerificationStatus.FAILED,
                    confidence_score=50.0,
                    method=VerificationMethod.TRADITIONAL,
                    processing_time_ms=(time.time() - start_time) * 1000,
                    timestamp=datetime.now(),
                    details={
                        'extracted_data': extracted_data.__dict__,
                        'reason': 'ID document expired'
                    },
                    error_message='ID document is expired'
                )

            # Step 5: Name and DOB matching (if provided)
            match_results = self._match_identity(extracted_data, expected_name, expected_dob)

            # Step 6: AAMVA verification (if driver's license)
            aamva_result = None
            if self._is_drivers_license(extracted_data):
                aamva_result = self._aamva_verification(extracted_data)

            # Step 7: Compute composite confidence
            confidence_score = self._compute_confidence(
                quality_metrics,
                validation_results,
                match_results,
                aamva_result
            )

            # Determine status
            if confidence_score >= 90:
                status = VerificationStatus.VERIFIED
            elif confidence_score >= 75:
                status = VerificationStatus.NEEDS_REVIEW
            else:
                status = VerificationStatus.FAILED

            return VerificationResult(
                status=status,
                confidence_score=confidence_score,
                method=VerificationMethod.TRADITIONAL,
                processing_time_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.now(),
                details={
                    'quality_metrics': quality_metrics.__dict__,
                    'extracted_data': extracted_data.__dict__,
                    'validation_results': validation_results,
                    'match_results': match_results,
                    'aamva_result': aamva_result
                }
            )

        except Exception as e:
            return self._fail_result(start_time, f"Verification error: {str(e)}")

    def _load_image(self, image_path: str) -> Optional[Image.Image]:
        """Load image from file"""
        try:
            return Image.open(image_path)
        except Exception as e:
            print(f"Error loading image: {e}")
            return None

    def _assess_document_quality(self, image: Image.Image) -> DocumentQualityMetrics:
        """
        Assess ID document image quality

        Checks:
        - Resolution (min 300 DPI recommended)
        - Clarity (sharpness)
        - Lighting (even, not too dark/bright)
        - Completeness (all corners visible)
        - Security features visible
        """
        # Resolution check
        resolution_dpi = self._estimate_dpi(image)

        # Clarity
        clarity_score = self._assess_clarity(image)

        # Completeness
        completeness_score = self._check_completeness(image)

        # Security features detection
        has_security_features = self._detect_security_features(image)

        # Tampering detection
        detected_tampering = self._detect_tampering(image)

        # Overall score
        overall_quality = (
            (30 if resolution_dpi >= 300 else 15) +
            (clarity_score * 0.35) +
            (completeness_score * 0.25) +
            (10 if has_security_features else 0)
        )

        if detected_tampering:
            overall_quality *= 0.4  # Major penalty for tampering

        return DocumentQualityMetrics(
            resolution_dpi=resolution_dpi,
            clarity_score=clarity_score,
            completeness_score=completeness_score,
            has_security_features=has_security_features,
            detected_tampering=detected_tampering,
            overall_quality_score=min(100, overall_quality)
        )

    def _estimate_dpi(self, image: Image.Image) -> int:
        """Estimate image DPI"""
        if hasattr(image, 'info') and 'dpi' in image.info:
            return int(image.info['dpi'][0])
        width, height = image.size
        # Assuming credit card size (3.375" x 2.125")
        return int(width / 3.375)

    def _assess_clarity(self, image: Image.Image) -> float:
        """Assess image sharpness using Laplacian variance"""
        try:
            import cv2
            import numpy as np
            img_array = np.array(image.convert('L'))
            laplacian_var = cv2.Laplacian(img_array, cv2.CV_64F).var()
            return min(100, (laplacian_var / 500) * 100)
        except ImportError:
            return 75.0  # Assume decent quality

    def _check_completeness(self, image: Image.Image) -> float:
        """Check if all corners of ID are visible"""
        try:
            import cv2
            import numpy as np
            img_array = np.array(image.convert('L'))
            edges = cv2.Canny(img_array, 50, 150)
            # Check for continuous rectangular border
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                largest_contour = max(contours, key=cv2.contourArea)
                peri = cv2.arcLength(largest_contour, True)
                approx = cv2.approxPolyDP(largest_contour, 0.02 * peri, True)
                # ID should be rectangular (4 corners)
                return 100.0 if len(approx) == 4 else 60.0
            return 50.0
        except ImportError:
            return 100.0  # Assume complete

    def _detect_security_features(self, image: Image.Image) -> bool:
        """
        Detect security features on ID:
        - Holographic overlays
        - UV patterns
        - Microprinting
        - Guilloche patterns

        In production, uses specialized computer vision
        """
        # TODO: Implement security feature detection
        # Would use texture analysis, frequency domain analysis
        return True  # Simulated

    def _detect_tampering(self, image: Image.Image) -> bool:
        """
        Detect ID tampering:
        - Photo replacement
        - Data alteration
        - Laminate resealing
        """
        # TODO: Implement tampering detection
        # Error Level Analysis, lighting consistency, edge analysis
        return False  # Simulated - no tampering

    def _extract_id_data(self, image: Image.Image) -> Optional[IDDocumentData]:
        """
        Extract structured data from ID using OCR

        Fields:
        - Name
        - Date of birth
        - Document number (license #, ID #)
        - Issue date, expiration date
        - Issuing state
        - Address
        """
        try:
            text = pytesseract.image_to_string(image)

            # Extract fields using regex patterns
            name = self._extract_field(text, r'(?:NAME|FN|FULL NAME)[:\s]+(.+)')
            dob = self._extract_field(text, r'(?:DOB|DATE OF BIRTH)[:\s]+(\d{1,2}/\d{1,2}/\d{4})')
            doc_number = self._extract_field(text, r'(?:DL|LICENSE|ID)[#:\s]+([A-Z0-9]+)')
            issue_date = self._extract_field(text, r'(?:ISS|ISSUED)[:\s]+(\d{1,2}/\d{1,2}/\d{4})')
            exp_date = self._extract_field(text, r'(?:EXP|EXPIRES)[:\s]+(\d{1,2}/\d{1,2}/\d{4})')
            state = self._extract_field(text, r'(?:STATE|ISSUED BY)[:\s]+([A-Z]{2})')
            address = self._extract_field(text, r'(?:ADDRESS|ADDR)[:\s]+(.+)')

            if not name or not dob:
                return None

            return IDDocumentData(
                name=name,
                date_of_birth=dob,
                document_number=doc_number if doc_number else 'UNKNOWN',
                issue_date=issue_date if issue_date else 'UNKNOWN',
                expiration_date=exp_date if exp_date else 'UNKNOWN',
                issuing_state=state if state else 'UNKNOWN',
                address=address
            )

        except Exception as e:
            print(f"OCR extraction error: {e}")
            return None

    def _extract_field(self, text: str, pattern: str) -> Optional[str]:
        """Extract field from text using regex"""
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
        return None

    def _validate_id_format(self, extracted_data: IDDocumentData, image: Image.Image) -> Dict:
        """
        Validate ID format per state specifications

        Checks:
        - Document number format (state-specific)
        - Date formats
        - Field completeness
        - Barcode presence and validation
        """
        results = {}

        # State-specific document number validation
        state = extracted_data.issuing_state
        if state in self.state_patterns:
            pattern = self.state_patterns[state]['dl_pattern']
            results['doc_number_format_valid'] = bool(re.match(pattern, extracted_data.document_number))
        else:
            results['doc_number_format_valid'] = True  # Unknown state

        # Field completeness
        required_fields = [
            extracted_data.name,
            extracted_data.date_of_birth,
            extracted_data.document_number,
            extracted_data.issue_date,
            extracted_data.expiration_date
        ]
        results['all_required_fields_present'] = all(
            field and field != 'UNKNOWN' for field in required_fields
        )

        # Date format validation
        results['dates_valid'] = (
            self._validate_date(extracted_data.date_of_birth) and
            self._validate_date(extracted_data.issue_date) and
            self._validate_date(extracted_data.expiration_date)
        )

        # Barcode validation (2D barcode on back of most modern IDs)
        # In production, would decode and verify against front data
        results['barcode_valid'] = True  # Simulated

        return results

    def _validate_date(self, date_str: str) -> bool:
        """Validate date format"""
        if not date_str or date_str == 'UNKNOWN':
            return False
        for fmt in ['%m/%d/%Y', '%Y-%m-%d', '%m-%d-%Y']:
            try:
                datetime.strptime(date_str, fmt)
                return True
            except ValueError:
                continue
        return False

    def _check_expiration(self, exp_date_str: str) -> bool:
        """Check if ID is expired"""
        if not exp_date_str or exp_date_str == 'UNKNOWN':
            return False  # Cannot determine, assume not expired

        try:
            for fmt in ['%m/%d/%Y', '%Y-%m-%d', '%m-%d-%Y']:
                try:
                    exp_date = datetime.strptime(exp_date_str, fmt)
                    return exp_date < datetime.now()
                except ValueError:
                    continue
        except:
            pass

        return False  # Cannot parse, assume not expired

    def _match_identity(
        self,
        extracted_data: IDDocumentData,
        expected_name: Optional[str],
        expected_dob: Optional[str]
    ) -> Dict:
        """Match extracted data against expected identity"""
        results = {}

        if expected_name:
            results['name_match'] = self._fuzzy_name_match(extracted_data.name, expected_name)
        else:
            results['name_match'] = None

        if expected_dob:
            results['dob_match'] = extracted_data.date_of_birth == expected_dob
        else:
            results['dob_match'] = None

        return results

    def _fuzzy_name_match(self, name1: str, name2: str) -> bool:
        """Fuzzy name matching"""
        if not name1 or not name2:
            return False
        # Simple case-insensitive comparison
        # In production: use Levenshtein distance, Soundex, nickname database
        return name1.strip().lower() == name2.strip().lower()

    def _is_drivers_license(self, extracted_data: IDDocumentData) -> bool:
        """Determine if document is a driver's license (vs state ID)"""
        # Check document number pattern or presence of class field
        # Most DL numbers follow specific state patterns
        return extracted_data.issuing_state in self.state_patterns

    def _aamva_verification(self, extracted_data: IDDocumentData) -> Optional[Dict]:
        """
        Verify against AAMVA (American Association of Motor Vehicle Administrators) database

        In production:
        - Query AAMVA database for license validation
        - Check for suspensions, revocations
        - Verify authenticity

        Returns verification result
        """
        # TODO: Implement AAMVA API integration
        # Requires commercial license/agreement with AAMVA

        return {
            'aamva_verified': True,  # Simulated
            'license_valid': True,
            'no_suspensions': True,
            'confidence': 95.0
        }

    def _compute_confidence(
        self,
        quality_metrics: DocumentQualityMetrics,
        validation_results: Dict,
        match_results: Dict,
        aamva_result: Optional[Dict]
    ) -> float:
        """
        Compute composite confidence score

        Weights:
        - Document quality: 25%
        - Format validation: 30%
        - Identity matching: 25%
        - AAMVA verification: 20%
        """
        score = 0.0

        # Quality component (25%)
        quality_component = quality_metrics.overall_quality_score * 0.25

        # Format validation (30%)
        validation_score = 0
        checks = [
            validation_results.get('doc_number_format_valid', False),
            validation_results.get('all_required_fields_present', False),
            validation_results.get('dates_valid', False),
            validation_results.get('barcode_valid', False)
        ]
        validation_score = sum(25 for check in checks if check)
        validation_component = validation_score * 0.30

        # Identity matching (25%)
        match_score = 0
        if match_results.get('name_match') is True:
            match_score += 50
        if match_results.get('dob_match') is True:
            match_score += 50
        match_component = match_score * 0.25

        # AAMVA (20%)
        if aamva_result:
            aamva_component = aamva_result.get('confidence', 0) * 0.20
        else:
            # Redistribute weight if no AAMVA
            quality_component *= 1.25
            validation_component *= 1.33
            aamva_component = 0

        score = quality_component + validation_component + match_component + aamva_component

        return min(100, max(0, score))

    def _load_state_patterns(self) -> Dict:
        """
        Load state-specific ID patterns and requirements

        Each state has different DL number formats, security features, etc.
        """
        return {
            'CA': {
                'dl_pattern': r'^[A-Z]\d{7}$',  # California: 1 letter + 7 digits
                'security_features': ['hologram', 'UV', 'microprint']
            },
            'NY': {
                'dl_pattern': r'^\d{9}$',  # New York: 9 digits
                'security_features': ['hologram', 'laser_perf']
            },
            'TX': {
                'dl_pattern': r'^\d{8}$',  # Texas: 8 digits
                'security_features': ['hologram', 'UV']
            },
            'FL': {
                'dl_pattern': r'^[A-Z]\d{12}$',  # Florida: 1 letter + 12 digits
                'security_features': ['hologram', 'UV']
            }
            # Add more states as needed
        }

    def _fail_result(self, start_time: float, error_message: str) -> VerificationResult:
        """Helper to create failure result"""
        return VerificationResult(
            status=VerificationStatus.FAILED,
            confidence_score=0.0,
            method=VerificationMethod.TRADITIONAL,
            processing_time_ms=(time.time() - start_time) * 1000,
            timestamp=datetime.now(),
            details={},
            error_message=error_message
        )
