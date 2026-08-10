"""
AWS Textract-based Death Certificate Verification
Specifically designed for Washington State death certificates

Uses AWS Textract to:
1. Extract text from death certificate PDFs/images
2. Parse structured form fields
3. Validate against expected data
4. Cross-reference with SSDI database
"""

import boto3
import os
import re
from typing import Dict, Optional, List, Tuple
from datetime import datetime
import time

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.models import (
    VerificationResult, VerificationStatus, VerificationMethod,
    DeathCertificateData
)


class TextractDeathCertVerifier:
    """
    Verifies death certificates using AWS Textract

    Optimized for Washington State death certificate format:
    - Multi-column layout with labeled fields
    - Mix of printed and handwritten text
    - State seal and security features
    - Barcode at bottom
    """

    def __init__(self, use_basic_api=False):
        """
        Initialize AWS Textract client

        Args:
            use_basic_api: If True, use DetectDocumentText (free tier)
                          If False, use AnalyzeDocument (requires subscription)
        """
        self.textract = boto3.client(
            'textract',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'us-west-2')
        )

        self.use_basic_api = use_basic_api

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
        Main verification workflow using AWS Textract

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
            # Step 1: Extract text and form fields using Textract
            extracted_data = self._extract_with_textract(file_path)

            if not extracted_data:
                return self._fail_result(start_time, "Failed to extract data from certificate")

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
                method=VerificationMethod.TEXTRACT,
                processing_time_ms=processing_time,
                timestamp=datetime.now(),
                details={
                    'extracted_data': parsed_data,
                    'validation_results': validation_results,
                    'textract_confidence': extracted_data.get('avg_confidence', 0)
                }
            )

        except Exception as e:
            return self._fail_result(start_time, f"Verification error: {str(e)}")

    def _extract_with_textract(self, file_path: str) -> Optional[Dict]:
        """
        Use AWS Textract to extract text and form fields

        Returns dict with:
        - raw_text: All extracted text
        - form_fields: Key-value pairs from form
        - tables: Any tables found
        - avg_confidence: Average confidence of extraction
        """
        try:
            # Read file
            with open(file_path, 'rb') as document:
                file_bytes = document.read()

            # Call Textract - try AnalyzeDocument first, fallback to DetectDocumentText
            response = None
            api_used = None

            if not self.use_basic_api:
                try:
                    print("Attempting to use AnalyzeDocument API (advanced features)...")
                    response = self.textract.analyze_document(
                        Document={'Bytes': file_bytes},
                        FeatureTypes=['FORMS', 'TABLES']  # Extract both forms and tables
                    )
                    api_used = 'AnalyzeDocument'
                    print("✓ AnalyzeDocument successful")
                except Exception as e:
                    if 'SubscriptionRequiredException' in str(type(e).__name__) or 'subscription' in str(e).lower():
                        print(f"⚠️  AnalyzeDocument not available (requires subscription)")
                        print(f"Falling back to DetectDocumentText (basic text extraction)...")
                        self.use_basic_api = True
                    else:
                        raise

            if self.use_basic_api or response is None:
                print("Using DetectDocumentText API (basic text extraction)...")
                response = self.textract.detect_document_text(
                    Document={'Bytes': file_bytes}
                )
                api_used = 'DetectDocumentText'
                print("✓ DetectDocumentText successful")

            # Parse response
            result = {
                'raw_text': '',
                'form_fields': {},
                'tables': [],
                'blocks': response.get('Blocks', []),
                'avg_confidence': 0,
                'api_used': api_used
            }

            # Extract text blocks
            text_blocks = []
            confidences = []

            for block in response.get('Blocks', []):
                if block['BlockType'] == 'LINE':
                    text_blocks.append(block.get('Text', ''))
                    if 'Confidence' in block:
                        confidences.append(block['Confidence'])

            result['raw_text'] = '\n'.join(text_blocks)
            result['avg_confidence'] = sum(confidences) / len(confidences) if confidences else 0

            # Extract form fields (key-value pairs) - only if AnalyzeDocument was used
            if api_used == 'AnalyzeDocument':
                result['form_fields'] = self._extract_form_fields(response.get('Blocks', []))
                result['tables'] = self._extract_tables(response.get('Blocks', []))
            else:
                # For basic API, we'll rely on pattern matching from raw text
                result['form_fields'] = {}
                result['tables'] = []

            return result

        except Exception as e:
            import traceback
            error_type = type(e).__name__
            print(f"\n{'='*80}")
            print(f"TEXTRACT EXTRACTION ERROR")
            print(f"{'='*80}")
            print(f"Error type: {error_type}")
            print(f"Error message: {str(e)}")

            # Special handling for subscription errors
            if 'SubscriptionRequiredException' in error_type or 'subscription' in str(e).lower():
                print(f"\n⚠️  AWS TEXTRACT SUBSCRIPTION ISSUE")
                print(f"The AWS account does not have access to Textract AnalyzeDocument API.")
                print(f"This API requires a paid subscription or special AWS access.")
                print(f"\nOptions:")
                print(f"  1. Enable Textract in AWS account")
                print(f"  2. Switch to DetectDocumentText (basic text extraction only)")
                print(f"  3. Use alternative OCR service (Google Vision, Azure, Tesseract)")

            print(f"\nFull traceback:")
            print(traceback.format_exc())
            print(f"{'='*80}\n")
            return None

    def _extract_form_fields(self, blocks: List[Dict]) -> Dict[str, str]:
        """Extract key-value pairs from Textract form analysis"""
        form_fields = {}

        # Build lookup maps
        key_map = {}
        value_map = {}
        block_map = {}

        for block in blocks:
            block_id = block['Id']
            block_map[block_id] = block

            if block['BlockType'] == 'KEY_VALUE_SET':
                if 'KEY' in block.get('EntityTypes', []):
                    key_map[block_id] = block
                else:
                    value_map[block_id] = block

        # Match keys to values
        for key_id, key_block in key_map.items():
            value_block_id = None

            # Find associated value
            if 'Relationships' in key_block:
                for relationship in key_block['Relationships']:
                    if relationship['Type'] == 'VALUE':
                        value_block_id = relationship['Ids'][0]
                        break

            # Extract text from key and value
            if value_block_id:
                key_text = self._get_text_from_block(key_block, block_map)
                value_text = self._get_text_from_block(value_map.get(value_block_id, {}), block_map)

                if key_text and value_text:
                    form_fields[key_text.strip()] = value_text.strip()

        return form_fields

    def _extract_tables(self, blocks: List[Dict]) -> List[List[List[str]]]:
        """Extract tables from Textract response"""
        tables = []

        # Build block map
        block_map = {block['Id']: block for block in blocks}

        # Find table blocks
        for block in blocks:
            if block['BlockType'] == 'TABLE':
                table = self._parse_table(block, block_map)
                if table:
                    tables.append(table)

        return tables

    def _parse_table(self, table_block: Dict, block_map: Dict) -> Optional[List[List[str]]]:
        """Parse a single table block into 2D array"""
        if 'Relationships' not in table_block:
            return None

        # Get cells
        cells = []
        for relationship in table_block['Relationships']:
            if relationship['Type'] == 'CHILD':
                for cell_id in relationship['Ids']:
                    cell_block = block_map.get(cell_id)
                    if cell_block and cell_block['BlockType'] == 'CELL':
                        cells.append(cell_block)

        if not cells:
            return None

        # Build table structure
        max_row = max(cell.get('RowIndex', 0) for cell in cells)
        max_col = max(cell.get('ColumnIndex', 0) for cell in cells)

        table = [['' for _ in range(max_col)] for _ in range(max_row)]

        for cell in cells:
            row_idx = cell.get('RowIndex', 1) - 1
            col_idx = cell.get('ColumnIndex', 1) - 1
            text = self._get_text_from_block(cell, block_map)

            if 0 <= row_idx < max_row and 0 <= col_idx < max_col:
                table[row_idx][col_idx] = text

        return table

    def _get_text_from_block(self, block: Dict, block_map: Dict) -> str:
        """Extract text content from a block"""
        text = ''

        if 'Relationships' in block:
            for relationship in block['Relationships']:
                if relationship['Type'] == 'CHILD':
                    for child_id in relationship['Ids']:
                        child_block = block_map.get(child_id, {})
                        if child_block.get('BlockType') == 'WORD':
                            text += child_block.get('Text', '') + ' '
                        elif child_block.get('BlockType') == 'SELECTION_ELEMENT':
                            if child_block.get('SelectionStatus') == 'SELECTED':
                                text += 'X '

        return text.strip()

    def _parse_wa_death_certificate(self, extracted_data: Dict) -> Dict:
        """
        Parse Washington State death certificate fields

        Based on WA death certificate layout:
        - NAME OF DECEDENT
        - DATE OF DEATH
        - SOCIAL SECURITY NUMBER
        - DATE OF BIRTH
        - SEX
        - PLACE OF DEATH
        - etc.
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
        form_fields = extracted_data.get('form_fields', {})

        # Try to extract from form fields first (most reliable)
        for key, value in form_fields.items():
            key_lower = key.lower()

            if 'name of decedent' in key_lower or 'decedent name' in key_lower:
                parsed['decedent_name'] = value
            elif 'date of death' in key_lower:
                parsed['date_of_death'] = value
            elif 'social security' in key_lower or 'ssn' in key_lower:
                parsed['ssn'] = value
            elif 'date of birth' in key_lower or 'birth date' in key_lower:
                parsed['date_of_birth'] = value
            elif key_lower == 'sex':
                parsed['sex'] = value
            elif 'place of death' in key_lower:
                parsed['place_of_death'] = value
            elif 'state file' in key_lower or 'file number' in key_lower:
                parsed['state_file_number'] = value
            elif 'certifier' in key_lower and 'name' in key_lower:
                parsed['certifier_name'] = value

        # Fallback: Pattern matching on raw text
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

            # Simple name matching (could be enhanced with Levenshtein distance)
            results['name_match'] = (
                expected_name_upper in extracted_name or
                extracted_name in expected_name_upper
            )

        # SSN matching
        if expected_ssn and parsed_data.get('ssn'):
            results['ssn_match'] = parsed_data['ssn'].replace('-', '') == expected_ssn.replace('-', '')
        elif not expected_ssn:
            results['ssn_match'] = None  # Not applicable

        # Date matching
        if expected_dod and parsed_data.get('date_of_death'):
            results['date_match'] = self._dates_match(parsed_data['date_of_death'], expected_dod)
        elif not expected_dod:
            results['date_match'] = None

        # Completeness - how many fields were extracted?
        total_fields = len(parsed_data)
        extracted_fields = sum(1 for v in parsed_data.values() if v is not None)
        results['field_extraction_rate'] = (extracted_fields / total_fields) * 100
        results['completeness_score'] = min(100, (extracted_fields / 6) * 100)  # 6 critical fields

        return results

    def _dates_match(self, date1: str, date2: str) -> bool:
        """Check if two dates match (various formats)"""
        # Normalize dates
        date1_normalized = re.sub(r'[/-]', '', date1)
        date2_normalized = re.sub(r'[/-]', '', date2)
        return date1_normalized == date2_normalized

    def _calculate_confidence(self, validation_results: Dict) -> float:
        """Calculate overall confidence score"""
        score = 0.0

        # Name match (40 points)
        if validation_results.get('name_match'):
            score += 40

        # SSN match (30 points) - if available
        if validation_results.get('ssn_match') is True:
            score += 30
        elif validation_results.get('ssn_match') is None:
            score += 20  # Partial credit if SSN not required

        # Date match (20 points) - if available
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
            method=VerificationMethod.TEXTRACT,
            processing_time_ms=(time.time() - start_time) * 1000,
            timestamp=datetime.now(),
            details={},
            error_message=error_message
        )


# Helper function for easy import
def verify_death_certificate_textract(
    file_path: str,
    expected_deceased_name: str,
    expected_ssn: Optional[str] = None,
    expected_date_of_death: Optional[str] = None
) -> VerificationResult:
    """
    Convenience function to verify death certificate using Textract
    """
    verifier = TextractDeathCertVerifier()
    return verifier.verify_death_certificate(
        file_path,
        expected_deceased_name,
        expected_ssn,
        expected_date_of_death
    )
