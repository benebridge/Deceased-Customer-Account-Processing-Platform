"""
Tesseract OCR-based Death Certificate Verification
Free, open-source alternative to AWS Textract

Uses Tesseract OCR to:
1. Extract text from death certificate PDFs/images
2. Parse structured form fields using pattern matching
3. Validate against expected data
"""

import os
import re
from typing import Dict, Optional
from datetime import datetime
import time
import subprocess
import tempfile
from pathlib import Path

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.models import (
    VerificationResult, VerificationStatus, VerificationMethod,
    DeathCertificateData
)


class TesseractDeathCertVerifier:
    """
    Verifies death certificates using Tesseract OCR

    Free alternative to AWS Textract that runs locally
    """

    def __init__(self):
        """Initialize Tesseract verifier"""
        # Check if tesseract is available
        try:
            subprocess.run(['tesseract', '--version'],
                         capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError("Tesseract OCR is not installed. Install with: brew install tesseract")

        # Washington State specific patterns
        self.wa_patterns = {
            'state_file_number': r'\d{4}-\d{6}',  # Format: YYYY-NNNNNN
            'ssn': r'\d{3}-\d{2}-\d{4}',
            'date': r'\d{1,2}/\d{1,2}/\d{4}',  # MM/DD/YYYY
        }

    def verify_death_certificate(
        self,
        file_path: str,
        expected_deceased_name: str,
        expected_ssn: Optional[str] = None,
        expected_date_of_death: Optional[str] = None
    ) -> VerificationResult:
        """
        Main verification workflow using Tesseract OCR

        Args:
            file_path: Path to death certificate (PDF or image)
            expected_deceased_name: Name from account records
            expected_ssn: SSN from account records (optional)
            expected_date_of_death: Expected date of death (optional)

        Returns:
            VerificationResult with confidence score
        """
        start_time = time.time()

        try:
            # Step 1: Extract text using Tesseract
            extracted_data = self._extract_with_tesseract(file_path)

            if not extracted_data or not extracted_data.get('raw_text'):
                return self._fail_result(start_time, "Failed to extract text from certificate")

            # Step 2: Parse Washington State specific fields
            parsed_data = self._parse_wa_death_certificate(extracted_data)

            # Step 3: Validate extracted data
            validation_results = self._validate_certificate_data(
                parsed_data,
                expected_deceased_name,
                expected_ssn,
                expected_date_of_death
            )

            # Step 4: Calculate confidence score
            confidence_score = self._calculate_confidence(validation_results)

            # Step 5: Determine verification status
            status = self._determine_status(confidence_score, validation_results)

            processing_time = (time.time() - start_time) * 1000

            return VerificationResult(
                status=status,
                confidence_score=confidence_score,
                method=VerificationMethod.OCR,  # Using generic OCR method
                processing_time_ms=processing_time,
                timestamp=datetime.now(),
                details={
                    'extracted_data': parsed_data,
                    'validation_results': validation_results,
                    'ocr_engine': 'tesseract',
                    'avg_confidence': extracted_data.get('avg_confidence', 0)
                }
            )

        except Exception as e:
            return self._fail_result(start_time, f"Verification error: {str(e)}")

    def _extract_with_tesseract(self, file_path: str) -> Optional[Dict]:
        """
        Use Tesseract OCR to extract text from document

        Returns dict with:
        - raw_text: All extracted text
        - avg_confidence: Average confidence of extraction (from TSV output)
        """
        try:
            # Convert PDF to images if needed
            if file_path.lower().endswith('.pdf'):
                image_files = self._pdf_to_images(file_path)
            else:
                image_files = [file_path]

            all_text = []
            all_confidences = []

            for image_file in image_files:
                # Run Tesseract with TSV output to get confidence scores
                result = subprocess.run(
                    ['tesseract', image_file, 'stdout', '--psm', '1', 'tsv'],
                    capture_output=True,
                    text=True,
                    check=True
                )

                tsv_output = result.stdout

                # Also get plain text
                result_text = subprocess.run(
                    ['tesseract', image_file, 'stdout', '--psm', '1'],
                    capture_output=True,
                    text=True,
                    check=True
                )

                text = result_text.stdout
                all_text.append(text)

                # Parse TSV for confidence scores
                for line in tsv_output.split('\n')[1:]:  # Skip header
                    parts = line.split('\t')
                    if len(parts) >= 11 and parts[10]:  # Confidence is 11th column
                        try:
                            conf = float(parts[10])
                            if conf > 0:  # Only count valid confidences
                                all_confidences.append(conf)
                        except ValueError:
                            pass

            # Combine results
            raw_text = '\n\n'.join(all_text)
            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0

            print(f"Tesseract OCR extracted {len(raw_text)} characters")
            print(f"Average confidence: {avg_confidence:.2f}%")

            return {
                'raw_text': raw_text,
                'avg_confidence': avg_confidence
            }

        except subprocess.CalledProcessError as e:
            print(f"Tesseract OCR error: {e}")
            print(f"Stderr: {e.stderr}")
            return None
        except Exception as e:
            print(f"Error extracting with Tesseract: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _pdf_to_images(self, pdf_path: str) -> list:
        """
        Convert PDF to images for OCR processing

        Returns list of image file paths
        """
        try:
            # Use pdf2image library if available, otherwise use imagemagick
            try:
                from pdf2image import convert_from_path

                images = convert_from_path(pdf_path, dpi=300)
                image_files = []

                # Save to temp files
                for i, image in enumerate(images):
                    temp_file = tempfile.NamedTemporaryFile(
                        suffix='.png', delete=False
                    )
                    image.save(temp_file.name, 'PNG')
                    image_files.append(temp_file.name)

                return image_files

            except ImportError:
                # Fallback to ImageMagick convert command
                temp_dir = tempfile.mkdtemp()
                output_pattern = os.path.join(temp_dir, 'page-%03d.png')

                subprocess.run(
                    ['convert', '-density', '300', pdf_path, output_pattern],
                    check=True,
                    capture_output=True
                )

                # Find generated images
                image_files = sorted(Path(temp_dir).glob('page-*.png'))
                return [str(f) for f in image_files]

        except Exception as e:
            print(f"Error converting PDF to images: {e}")
            # Return original file as fallback
            return [pdf_path]

    def _parse_wa_death_certificate(self, extracted_data: Dict) -> Dict:
        """
        Parse Washington State death certificate fields from raw text
        """
        parsed = {
            'decedent_name': None,
            'date_of_death': None,
            'ssn': None,
            'date_of_birth': None,
            'sex': None,
            'place_of_death': None,
            'state_file_number': None,
            'certifier_name': None,
            'certificate_number': None
        }

        raw_text = extracted_data.get('raw_text', '')
        lines = raw_text.split('\n')

        # Track first and last name separately for Washington State format
        first_name = None
        last_name = None

        # Pattern matching for specific fields
        for i, line in enumerate(lines):
            line_upper = line.upper()
            line_clean = line.strip()

            # Washington State specific: FIRST AND MIDDLE NAME(S): and LAST NAME(S):
            if 'FIRST AND MIDDLE NAME' in line_upper or 'FIRST NAME' in line_upper:
                # Extract value after colon
                parts = line_clean.split(':', 1)
                if len(parts) == 2 and parts[1].strip():
                    first_name = parts[1].strip()

            if 'LAST NAME' in line_upper and 'FIRST' not in line_upper:
                # Extract value after colon
                parts = line_clean.split(':', 1)
                if len(parts) == 2 and parts[1].strip():
                    last_name = parts[1].strip()

            # Generic name fields
            if ('NAME OF DECEDENT' in line_upper or 'DECEDENT NAME' in line_upper) and not parsed['decedent_name']:
                # Try next line or same line after the label
                if i + 1 < len(lines):
                    name_candidate = lines[i + 1].strip()
                    if name_candidate and len(name_candidate) > 3:
                        parsed['decedent_name'] = name_candidate
                # Also try extracting from same line
                parts = line.split(':', 1)
                if len(parts) == 2 and parts[1].strip():
                    parsed['decedent_name'] = parts[1].strip()

            # Date of death - handle both numeric and text dates
            if 'DATE OF DEATH' in line_upper:
                # Try numeric format first
                date_match = re.search(self.wa_patterns['date'], line)
                if date_match:
                    parsed['date_of_death'] = date_match.group()
                else:
                    # Try text format like "AUGUST 27, 2024"
                    text_date_match = re.search(r'([A-Z]+\s+\d{1,2},\s+\d{4})', line_upper)
                    if text_date_match:
                        parsed['date_of_death'] = text_date_match.group(1)
                    else:
                        # Extract value after colon
                        parts = line_clean.split(':', 1)
                        if len(parts) == 2 and parts[1].strip():
                            parsed['date_of_death'] = parts[1].strip()

            # Social Security Number
            if 'SOCIAL SECURITY' in line_upper or 'SSN' in line_upper:
                ssn_match = re.search(self.wa_patterns['ssn'], line)
                if ssn_match:
                    parsed['ssn'] = ssn_match.group()
                elif i + 1 < len(lines):
                    ssn_match = re.search(self.wa_patterns['ssn'], lines[i + 1])
                    if ssn_match:
                        parsed['ssn'] = ssn_match.group()

            # Date of birth - handle both numeric and text dates
            if ('BIRTH DATE' in line_upper or 'DATE OF BIRTH' in line_upper) and 'DEATH' not in line_upper:
                # Try numeric format first
                date_match = re.search(self.wa_patterns['date'], line)
                if date_match:
                    parsed['date_of_birth'] = date_match.group()
                else:
                    # Try text format
                    text_date_match = re.search(r'([A-Z]+\s+\d{1,2},\s+\d{4})', line_upper)
                    if text_date_match:
                        parsed['date_of_birth'] = text_date_match.group(1)
                    else:
                        # Extract value after colon
                        parts = line_clean.split(':', 1)
                        if len(parts) == 2 and parts[1].strip():
                            parsed['date_of_birth'] = parts[1].strip()

            # Sex
            if 'SEX:' in line_upper:
                # Extract value after "SEX:"
                sex_match = re.search(r'SEX:\s*(MALE|FEMALE|M|F)', line_upper)
                if sex_match:
                    parsed['sex'] = sex_match.group(1)

            # County/Place of death
            if 'COUNTY OF DEATH' in line_upper or 'PLACE OF DEATH' in line_upper:
                parts = line_clean.split(':', 1)
                if len(parts) == 2 and parts[1].strip():
                    parsed['place_of_death'] = parts[1].strip()

        # Combine first and last name if found
        if first_name and last_name:
            parsed['decedent_name'] = f"{first_name} {last_name}"
        elif first_name:
            parsed['decedent_name'] = first_name
        elif last_name:
            parsed['decedent_name'] = last_name

        # Fallback: Pattern matching on entire text
        if not parsed['state_file_number']:
            match = re.search(self.wa_patterns['state_file_number'], raw_text)
            if match:
                parsed['state_file_number'] = match.group()

        if not parsed['ssn']:
            match = re.search(self.wa_patterns['ssn'], raw_text)
            if match:
                parsed['ssn'] = match.group()

        return parsed

    def _validate_certificate_data(
        self,
        parsed_data: Dict,
        expected_name: str,
        expected_ssn: Optional[str],
        expected_dod: Optional[str]
    ) -> Dict:
        """Validate extracted data against expected values"""
        results = {
            'name_match': False,
            'ssn_match': False,
            'date_match': False,
            'completeness_score': 0,
            'field_extraction_rate': 0
        }

        # Name matching (fuzzy)
        if parsed_data.get('decedent_name'):
            extracted_name = parsed_data['decedent_name'].upper()
            expected_name_upper = expected_name.upper()

            # Simple name matching
            results['name_match'] = (
                expected_name_upper in extracted_name or
                extracted_name in expected_name_upper or
                self._fuzzy_name_match(extracted_name, expected_name_upper)
            )

        # SSN matching
        if expected_ssn and parsed_data.get('ssn'):
            results['ssn_match'] = parsed_data['ssn'].replace('-', '') == expected_ssn.replace('-', '')
        elif not expected_ssn:
            results['ssn_match'] = None

        # Date matching
        if expected_dod and parsed_data.get('date_of_death'):
            results['date_match'] = self._dates_match(parsed_data['date_of_death'], expected_dod)
        elif not expected_dod:
            results['date_match'] = None

        # Completeness
        total_fields = len(parsed_data)
        extracted_fields = sum(1 for v in parsed_data.values() if v is not None)
        results['field_extraction_rate'] = (extracted_fields / total_fields) * 100
        results['completeness_score'] = min(100, (extracted_fields / 6) * 100)

        return results

    def _fuzzy_name_match(self, name1: str, name2: str) -> bool:
        """Simple fuzzy name matching"""
        # Remove common prefixes/suffixes
        name1_clean = re.sub(r'\b(MR|MRS|MS|DR|JR|SR|III|II)\b', '', name1).strip()
        name2_clean = re.sub(r'\b(MR|MRS|MS|DR|JR|SR|III|II)\b', '', name2).strip()

        # Split into words
        words1 = set(name1_clean.split())
        words2 = set(name2_clean.split())

        # Check if most words match
        if not words1 or not words2:
            return False

        intersection = words1 & words2
        return len(intersection) >= min(len(words1), len(words2)) * 0.7

    def _dates_match(self, date1: str, date2: str) -> bool:
        """Check if two dates match"""
        date1_normalized = re.sub(r'[/-]', '', date1)
        date2_normalized = re.sub(r'[/-]', '', date2)
        return date1_normalized == date2_normalized

    def _calculate_confidence(self, validation_results: Dict) -> float:
        """Calculate overall confidence score"""
        score = 0.0

        # Name match (40 points)
        if validation_results.get('name_match'):
            score += 40

        # SSN match (30 points)
        if validation_results.get('ssn_match') is True:
            score += 30
        elif validation_results.get('ssn_match') is None:
            score += 20

        # Date match (20 points)
        if validation_results.get('date_match') is True:
            score += 20
        elif validation_results.get('date_match') is None:
            score += 10

        # Completeness (10 points)
        score += validation_results.get('completeness_score', 0) * 0.1

        return min(100.0, score)

    def _determine_status(self, confidence_score: float, validation_results: Dict) -> VerificationStatus:
        """Determine verification status based on confidence"""
        if confidence_score >= 85:
            return VerificationStatus.VERIFIED
        elif confidence_score >= 70:
            return VerificationStatus.NEEDS_REVIEW
        else:
            return VerificationStatus.FAILED

    def _fail_result(self, start_time: float, error_message: str) -> VerificationResult:
        """Helper to create failure result"""
        return VerificationResult(
            status=VerificationStatus.FAILED,
            confidence_score=0.0,
            method=VerificationMethod.OCR,
            processing_time_ms=(time.time() - start_time) * 1000,
            timestamp=datetime.now(),
            details={'ocr_engine': 'tesseract'},
            error_message=error_message
        )


# Helper function for easy import
def verify_death_certificate_tesseract(
    file_path: str,
    expected_deceased_name: str,
    expected_ssn: Optional[str] = None,
    expected_date_of_death: Optional[str] = None
) -> VerificationResult:
    """
    Convenience function to verify death certificate using Tesseract OCR
    """
    verifier = TesseractDeathCertVerifier()
    return verifier.verify_death_certificate(
        file_path,
        expected_deceased_name,
        expected_ssn,
        expected_date_of_death
    )
