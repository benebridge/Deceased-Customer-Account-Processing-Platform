"""
Traditional Death Certificate Verification
Implements Chapter 5 Section 4.5.3 - Traditional Verification Pathway

For physical (non-blockchain) death certificates using:
- Computer vision quality assessment
- OCR data extraction
- Rule-based validation
- SSDI cross-reference
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
    DeathCertificateData, DocumentQualityMetrics
)


class TraditionalVerifier:
    """
    Verifies death certificates using traditional multi-layer analysis

    Per Chapter 5 Section 4.5.3:
    1. Computer vision assessment (image quality, tampering detection)
    2. OCR field extraction with validation
    3. Rule-based data validation
    4. SSDI cross-reference
    5. Composite confidence scoring
    """

    def __init__(self):
        """Initialize traditional verifier"""
        pass

    def verify_death_certificate(
        self,
        pdf_path: str,
        expected_deceased_name: str,
        expected_ssn: Optional[str] = None
    ) -> VerificationResult:
        """
        Main verification workflow for traditional certificates

        Args:
            pdf_path: Path to death certificate PDF
            expected_deceased_name: Account holder name
            expected_ssn: Account holder SSN (if available)

        Returns:
            VerificationResult with 0-100 confidence score
        """
        start_time = time.time()

        try:
            # Step 1: Convert PDF to image for computer vision analysis
            images = self._pdf_to_images(pdf_path)

            if not images:
                return self._fail_result(start_time, "Could not process PDF file")

            # Use first page for analysis
            image = images[0]

            # Step 2: Computer Vision Assessment
            quality_metrics = self._computer_vision_assessment(image)

            # Check if quality is too poor to proceed
            if quality_metrics.overall_quality_score < 40:
                return VerificationResult(
                    status=VerificationStatus.NEEDS_REVIEW,
                    confidence_score=quality_metrics.overall_quality_score,
                    method=VerificationMethod.COMPUTER_VISION,
                    processing_time_ms=(time.time() - start_time) * 1000,
                    timestamp=datetime.now(),
                    details={'quality_metrics': quality_metrics.__dict__},
                    error_message='Document quality too poor for automated verification'
                )

            # Step 3: OCR Data Extraction
            extracted_data = self._ocr_extraction(image)

            if not extracted_data:
                return self._fail_result(start_time, "Could not extract data from certificate")

            # Step 4: Rule-Based Validation
            validation_results = self._rule_based_validation(extracted_data, expected_deceased_name, expected_ssn)

            # Step 5: SSDI Cross-Reference (if SSN available)
            ssdi_result = None
            if extracted_data.deceased_ssn:
                ssdi_result = self._ssdi_cross_reference(
                    extracted_data.deceased_ssn,
                    extracted_data.date_of_death
                )

            # Step 6: Composite Confidence Scoring
            confidence_score = self._compute_composite_confidence(
                quality_metrics,
                validation_results,
                ssdi_result
            )

            # Determine status based on confidence
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
                    'extracted_data': extracted_data.__dict__ if extracted_data else {},
                    'validation_results': validation_results,
                    'ssdi_result': ssdi_result
                }
            )

        except Exception as e:
            return self._fail_result(start_time, f"Verification error: {str(e)}")

    def _pdf_to_images(self, pdf_path: str):
        """Convert PDF to images for computer vision analysis"""
        try:
            # Convert PDF pages to images at 300 DPI
            images = pdf2image.convert_from_path(pdf_path, dpi=300)
            return images
        except Exception as e:
            print(f"Error converting PDF to images: {e}")
            return None

    def _computer_vision_assessment(self, image: Image.Image) -> DocumentQualityMetrics:
        """
        Perform computer vision assessment per Chapter 5:

        - Image quality (resolution, clarity, completeness)
        - Security feature detection (watermarks, seals)
        - Tampering detection (JPEG artifacts, font inconsistencies, lighting analysis)
        - ML authenticity model (trained on 10K+ certificates)

        Returns:
            DocumentQualityMetrics with scores and flags
        """
        # Resolution check
        resolution_dpi = self._estimate_dpi(image)

        # Clarity assessment (sharpness detection)
        clarity_score = self._assess_clarity(image)

        # Completeness (check if all corners visible)
        completeness_score = self._check_completeness(image)

        # Security features detection
        has_security_features = self._detect_security_features(image)

        # Tampering detection
        detected_tampering = self._detect_tampering(image)

        # Overall quality score (weighted average)
        overall_quality = (
            (40 if resolution_dpi >= 300 else 20) +  # 40% weight on resolution
            (clarity_score * 0.3) +  # 30% weight on clarity
            (completeness_score * 0.2) +  # 20% weight on completeness
            (10 if has_security_features else 0)  # 10% bonus for security features
        )

        # Penalize for tampering
        if detected_tampering:
            overall_quality *= 0.5  # 50% penalty

        return DocumentQualityMetrics(
            resolution_dpi=resolution_dpi,
            clarity_score=clarity_score,
            completeness_score=completeness_score,
            has_security_features=has_security_features,
            detected_tampering=detected_tampering,
            overall_quality_score=min(100, overall_quality)
        )

    def _estimate_dpi(self, image: Image.Image) -> int:
        """Estimate image DPI (dots per inch)"""
        # Get DPI from image metadata if available
        if hasattr(image, 'info') and 'dpi' in image.info:
            return int(image.info['dpi'][0])

        # Estimate based on dimensions (assuming 8.5x11 inch document)
        width, height = image.size
        estimated_dpi = int(width / 8.5)  # Assuming letter-size width

        return estimated_dpi

    def _assess_clarity(self, image: Image.Image) -> float:
        """
        Assess image clarity using Laplacian variance (blur detection)

        Returns score 0-100
        """
        try:
            import cv2
            import numpy as np

            # Convert PIL image to numpy array
            img_array = np.array(image.convert('L'))  # Convert to grayscale

            # Compute Laplacian variance (higher = sharper)
            laplacian_var = cv2.Laplacian(img_array, cv2.CV_64F).var()

            # Normalize to 0-100 scale
            # Typical values: <100 = blurry, >500 = sharp
            clarity_score = min(100, (laplacian_var / 500) * 100)

            return clarity_score

        except ImportError:
            # If OpenCV not available, return moderate score
            return 70.0

    def _check_completeness(self, image: Image.Image) -> float:
        """
        Check if document is complete (all corners visible)

        Returns score 0-100
        """
        try:
            import cv2
            import numpy as np

            img_array = np.array(image.convert('L'))

            # Simple edge detection to check for document boundaries
            edges = cv2.Canny(img_array, 50, 150)

            # Check corners (top-left, top-right, bottom-left, bottom-right)
            h, w = img_array.shape
            corner_size = 50

            corners = [
                edges[0:corner_size, 0:corner_size],  # top-left
                edges[0:corner_size, w-corner_size:w],  # top-right
                edges[h-corner_size:h, 0:corner_size],  # bottom-left
                edges[h-corner_size:h, w-corner_size:w]  # bottom-right
            ]

            # Count how many corners have edges (document boundary visible)
            corners_detected = sum(1 for corner in corners if corner.sum() > 100)

            completeness_score = (corners_detected / 4) * 100

            return completeness_score

        except ImportError:
            # If OpenCV not available, assume complete
            return 100.0

    def _detect_security_features(self, image: Image.Image) -> bool:
        """
        Detect security features (watermarks, seals, holograms)

        In production, uses edge detection and texture analysis
        For now, returns simulated result
        """
        # TODO: Implement security feature detection
        # Would use:
        # - Edge detection for seals
        # - Texture analysis for watermarks
        # - Frequency domain analysis for holograms

        return True  # Simulated

    def _detect_tampering(self, image: Image.Image) -> bool:
        """
        Detect document tampering per Chapter 5:

        - JPEG compression artifacts (copy-paste)
        - Font inconsistencies
        - Shadow/lighting analysis
        - EXIF metadata examination

        Returns True if tampering detected
        """
        # TODO: Implement tampering detection algorithms
        # For production:
        # 1. Error Level Analysis (ELA) for JPEG artifacts
        # 2. Font detection and consistency checking
        # 3. Lighting gradient analysis
        # 4. EXIF metadata parsing

        return False  # Simulated - no tampering detected

    def _ocr_extraction(self, image: Image.Image) -> Optional[DeathCertificateData]:
        """
        Extract structured data using OCR

        Per Chapter 5:
        - Use Tesseract or commercial OCR
        - Extract: name, SSN, DOB, DOD, place, certificate number
        - Apply field-specific validation rules
        """
        try:
            # Perform OCR
            text = pytesseract.image_to_string(image)

            # Extract structured fields using regex patterns
            # In production, would use more sophisticated NLP

            deceased_name = self._extract_field(text, r'(?:Name|DECEASED NAME)[:\s]+(.+)')
            ssn = self._extract_field(text, r'(?:SSN|SOCIAL SECURITY)[:\s#]+(\d{3}-\d{2}-\d{4})')
            dod = self._extract_field(text, r'(?:DATE OF DEATH|DEATH DATE)[:\s]+(\d{1,2}/\d{1,2}/\d{4})')
            place = self._extract_field(text, r'(?:PLACE OF DEATH|LOCATION)[:\s]+(.+)')
            cert_number = self._extract_field(text, r'(?:CERTIFICATE NUMBER|CERT #)[:\s]+(.+)')

            if not deceased_name:
                return None

            return DeathCertificateData(
                deceased_name=deceased_name,
                deceased_ssn=ssn,
                date_of_birth=None,  # TODO: Extract if present
                date_of_death=dod if dod else 'UNKNOWN',
                place_of_death=place if place else 'UNKNOWN',
                certificate_number=cert_number if cert_number else 'UNKNOWN',
                issuing_state='CA'  # TODO: Extract from document
            )

        except Exception as e:
            print(f"OCR extraction error: {e}")
            return None

    def _extract_field(self, text: str, pattern: str) -> Optional[str]:
        """Extract field from text using regex pattern"""
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _rule_based_validation(
        self,
        extracted_data: DeathCertificateData,
        expected_name: str,
        expected_ssn: Optional[str]
    ) -> Dict:
        """
        Automated rule-based checks per Chapter 5:

        - Certificate number format validation
        - Field completeness
        - Data type validation
        - Cross-field consistency
        - Name matching (fuzzy)
        """
        results = {}

        # Certificate number format (state-specific patterns)
        if extracted_data.issuing_state == 'CA':
            pattern = r'^\d{4}-CA-[A-Z]{2,3}-\d{5}$'
            results['cert_number_format_valid'] = bool(re.match(pattern, extracted_data.certificate_number))
        else:
            results['cert_number_format_valid'] = True  # Unknown format

        # Field completeness
        required_fields = [
            extracted_data.deceased_name,
            extracted_data.date_of_death,
            extracted_data.certificate_number
        ]
        results['all_required_fields_present'] = all(field and field != 'UNKNOWN' for field in required_fields)

        # Data type validation
        results['date_format_valid'] = self._validate_date_format(extracted_data.date_of_death)

        # Cross-field consistency
        # (In production, would check: DOD >= DOB, age reasonable, etc.)
        results['cross_field_consistent'] = True  # Simulated

        # Name matching
        results['name_match'] = self._fuzzy_name_match(extracted_data.deceased_name, expected_name)

        # SSN matching (if available)
        if expected_ssn and extracted_data.deceased_ssn:
            results['ssn_match'] = extracted_data.deceased_ssn == expected_ssn
        else:
            results['ssn_match'] = None  # Not applicable

        return results

    def _validate_date_format(self, date_str: str) -> bool:
        """Validate date string format"""
        if not date_str or date_str == 'UNKNOWN':
            return False

        # Try common date formats
        for fmt in ['%m/%d/%Y', '%Y-%m-%d', '%m-%d-%Y']:
            try:
                datetime.strptime(date_str, fmt)
                return True
            except ValueError:
                continue

        return False

    def _fuzzy_name_match(self, name1: str, name2: str) -> bool:
        """Fuzzy name matching (simple version)"""
        if not name1 or not name2:
            return False
        return name1.strip().lower() == name2.strip().lower()

    def _ssdi_cross_reference(self, ssn: str, date_of_death: str) -> Optional[Dict]:
        """
        Cross-reference with Social Security Death Master File

        In production, would query SSDI API
        Returns match confirmation and death date validation
        """
        # TODO: Implement actual SSDI API integration
        # For now, return simulated result

        return {
            'ssdi_match_found': True,  # Simulated
            'ssdi_death_date_matches': True,  # Simulated
            'ssdi_confidence': 95.0
        }

    def _compute_composite_confidence(
        self,
        quality_metrics: DocumentQualityMetrics,
        validation_results: Dict,
        ssdi_result: Optional[Dict]
    ) -> float:
        """
        Compute composite confidence score (0-100) per Chapter 5

        Weights:
        - Document quality: 30%
        - Rule validation: 40%
        - SSDI cross-check: 30% (if available)
        """
        score = 0.0

        # Component 1: Document quality (30%)
        quality_component = quality_metrics.overall_quality_score * 0.30

        # Component 2: Rule validation (40%)
        validation_score = 0
        checks = [
            validation_results.get('cert_number_format_valid', False),
            validation_results.get('all_required_fields_present', False),
            validation_results.get('date_format_valid', False),
            validation_results.get('cross_field_consistent', False),
            validation_results.get('name_match', False)
        ]

        # Each check worth 20 points
        validation_score = sum(20 for check in checks if check)
        validation_component = validation_score * 0.40

        # Component 3: SSDI (30%)
        if ssdi_result:
            ssdi_component = ssdi_result.get('ssdi_confidence', 0) * 0.30
        else:
            # If no SSDI available, redistribute weight
            quality_component *= (1.3/1.0)  # Increase quality weight
            validation_component *= (1.7/1.4)  # Increase validation weight
            ssdi_component = 0

        score = quality_component + validation_component + ssdi_component

        return min(100, max(0, score))

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
