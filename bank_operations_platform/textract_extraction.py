#!/usr/bin/env python3
"""
AWS Textract-based extraction for IDP
"""

import boto3
import re
from pathlib import Path

def extract_blockchain_identifiers(response_blocks):
    """
    Extract blockchain ID and verification URLs from Titan Seal death certificates.
    Looks for:
    - Blockchain ID pattern: 0x[40 hex characters]
    - Verification URLs: https://titanseal.com/verify, https://etherscan.io, etc.
    - QR code data (if Textract can detect it)

    Per dissertation: Blockchain-sealed certificates receive Security Score = 95
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
            eth_pattern = r'0x[0-9a-fA-F]{40}'
            if re.search(eth_pattern, text):
                blockchain_id = re.findall(eth_pattern, text)[0]
                blockchain_data['blockchain_id'] = blockchain_id
                blockchain_data['has_blockchain_seal'] = True
                blockchain_data['seal_issuer'] = 'Titan Seal'

            # Look for verification URLs
            if 'titanseal.com' in text.lower():
                blockchain_data['verification_urls'].append(text)
            if 'etherscan.io' in text.lower() or 'etherchain.org' in text.lower():
                blockchain_data['verification_urls'].append(text)

    return blockchain_data

def extract_death_certificate_textract(file_path):
    """Extract data from death certificate using AWS Textract"""
    try:
        # Initialize Textract client
        textract = boto3.client('textract', region_name='us-east-1')

        # Convert PDF to image first (to avoid size issues)
        from pdf2image import convert_from_path
        from PIL import Image
        import io

        images = convert_from_path(file_path, first_page=1, last_page=1, dpi=200)
        img = images[0]

        # Convert image to bytes
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        file_bytes = img_byte_arr.getvalue()

        # Call Textract - use AnalyzeDocument for form extraction
        response = textract.analyze_document(
            Document={'Bytes': file_bytes},
            FeatureTypes=['FORMS', 'TABLES']
        )

        # Parse the response to extract key-value pairs
        extracted_data = {}

        # Build a map of key-value pairs
        key_map = {}
        value_map = {}
        block_map = {}

        for block in response['Blocks']:
            block_id = block['Id']
            block_map[block_id] = block

            if block['BlockType'] == 'KEY_VALUE_SET':
                if 'KEY' in block['EntityTypes']:
                    key_map[block_id] = block
                else:
                    value_map[block_id] = block

        # Function to get text from block
        def get_text(block, block_map):
            text = ''
            if 'Relationships' in block:
                for relationship in block['Relationships']:
                    if relationship['Type'] == 'CHILD':
                        for child_id in relationship['Ids']:
                            child = block_map[child_id]
                            if child['BlockType'] == 'WORD':
                                text += child['Text'] + ' '
            return text.strip()

        # Extract key-value pairs
        kvs = {}
        for key_block_id, key_block in key_map.items():
            value_block = None
            key_text = get_text(key_block, block_map)

            # Find the associated value
            if 'Relationships' in key_block:
                for relationship in key_block['Relationships']:
                    if relationship['Type'] == 'VALUE':
                        for value_id in relationship['Ids']:
                            value_block = block_map[value_id]
                            value_text = get_text(value_block, block_map)
                            kvs[key_text.lower()] = value_text

        # Extract specific fields we need
        # Look for first name field
        for key, value in kvs.items():
            key_lower = key.lower()

            # Field 1: First name of decedent
            if key_lower == '1. name of decedent- first (given)' or (
                'first' in key_lower and 'given' in key_lower and 'decedent' in key_lower and 'name' in key_lower
            ):
                extracted_data['first_name'] = value.strip().capitalize()

            # Field 3: Last name of decedent (family name)
            # IMPORTANT: Must explicitly check for field 3 and exclude mother/father fields
            elif key_lower == '3. last (family)' or (
                key_lower.startswith('3.') and 'last' in key_lower and 'family' in key_lower
            ):
                extracted_data['last_name'] = value.strip().capitalize()

            # Field 7: Date of death
            elif key_lower == '7. date of death mm/dd/ccyy' or ('7.' in key_lower and 'death' in key_lower and 'date' in key_lower):
                extracted_data['death_date'] = value

            # Field 10: Social Security Number
            elif key_lower == '10. social security number' or ('10.' in key_lower and 'social security' in key_lower):
                extracted_data['ssn'] = value

        # Combine first and last name
        if 'first_name' in extracted_data and 'last_name' in extracted_data:
            extracted_data['deceased_name'] = f"{extracted_data['first_name']} {extracted_data['last_name']}"

        # Extract blockchain identifiers (Titan Seal verification)
        blockchain_verification = extract_blockchain_identifiers(response['Blocks'])

        print(f"Textract extracted data: {extracted_data}")
        print(f"All key-value pairs found: {kvs}")
        print(f"Blockchain verification: {blockchain_verification}")

        return {
            'verified': bool(extracted_data.get('deceased_name')),
            'methods_used': ['aws_textract'],
            'extracted_data': extracted_data,
            'blockchain_verification': blockchain_verification,
            'all_kvs': kvs  # For debugging
        }

    except Exception as e:
        print(f"Error using Textract: {str(e)}")
        return {
            'verified': False,
            'error': str(e),
            'extracted_data': {}
        }


def extract_drivers_license_textract(file_path):
    """Extract data from driver's license using AWS Textract"""
    try:
        # Initialize Textract client
        textract = boto3.client('textract', region_name='us-east-1')

        # Read the file
        with open(file_path, 'rb') as document:
            file_bytes = document.read()

        # Call Textract AnalyzeID for driver's license (specialized API)
        response = textract.analyze_id(
            DocumentPages=[{'Bytes': file_bytes}]
        )

        # Extract identity document fields
        extracted_data = {}

        for doc in response.get('IdentityDocuments', []):
            for field in doc.get('IdentityDocumentFields', []):
                field_type = field.get('Type', {}).get('Text', '')
                field_value = field.get('ValueDetection', {}).get('Text', '')

                # Map fields
                if field_type == 'FIRST_NAME':
                    extracted_data['first_name'] = field_value
                elif field_type == 'LAST_NAME':
                    extracted_data['last_name'] = field_value
                elif field_type == 'DATE_OF_BIRTH':
                    extracted_data['dob'] = field_value
                elif field_type == 'ADDRESS':
                    extracted_data['address'] = field_value
                elif field_type == 'DOCUMENT_NUMBER':
                    extracted_data['dl_number'] = field_value

        # Combine first and last name
        if 'first_name' in extracted_data and 'last_name' in extracted_data:
            extracted_data['name'] = f"{extracted_data['first_name']} {extracted_data['last_name']}"

        print(f"Textract AnalyzeID extracted: {extracted_data}")

        return {
            'verified': bool(extracted_data.get('name')),
            'method': 'aws_textract_analyzeid',
            'extracted_data': extracted_data
        }

    except Exception as e:
        print(f"Error using Textract AnalyzeID: {str(e)}")
        return {
            'verified': False,
            'error': str(e),
            'extracted_data': {}
        }


def extract_claim_form_textract(file_path):
    """Extract data from beneficiary claim form using AWS Textract"""
    try:
        # Initialize Textract client
        textract = boto3.client('textract', region_name='us-east-1')

        # Convert PDF pages to images first
        from pdf2image import convert_from_path
        from PIL import Image
        import io

        # Convert first page to image
        images = convert_from_path(file_path, first_page=1, last_page=1, dpi=200)
        img = images[0]

        # Convert image to bytes
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        file_bytes = img_byte_arr.getvalue()

        # Call Textract - use AnalyzeDocument for form extraction
        response = textract.analyze_document(
            Document={'Bytes': file_bytes},
            FeatureTypes=['FORMS']
        )

        # Parse the response to extract key-value pairs
        extracted_data = {}

        # Build a map of key-value pairs
        key_map = {}
        value_map = {}
        block_map = {}

        for block in response['Blocks']:
            block_id = block['Id']
            block_map[block_id] = block

            if block['BlockType'] == 'KEY_VALUE_SET':
                if 'KEY' in block['EntityTypes']:
                    key_map[block_id] = block
                else:
                    value_map[block_id] = block

        # Function to get text from block
        def get_text(block, block_map):
            text = ''
            if 'Relationships' in block:
                for relationship in block['Relationships']:
                    if relationship['Type'] == 'CHILD':
                        for child_id in relationship['Ids']:
                            child = block_map[child_id]
                            if child['BlockType'] == 'WORD':
                                text += child['Text'] + ' '
            return text.strip()

        # Extract key-value pairs
        kvs = {}
        for key_block_id, key_block in key_map.items():
            value_block = None
            key_text = get_text(key_block, block_map)

            # Find the associated value
            if 'Relationships' in key_block:
                for relationship in key_block['Relationships']:
                    if relationship['Type'] == 'VALUE':
                        for value_id in relationship['Ids']:
                            value_block = block_map[value_id]
                            value_text = get_text(value_block, block_map)
                            kvs[key_text.lower()] = value_text

        # Extract specific fields
        for key, value in kvs.items():
            key_lower = key.lower()
            if 'full name' in key_lower:
                extracted_data['deceased_name'] = value
            elif 'account' in key_lower and '#' in key_lower:
                extracted_data['account_number'] = value
            elif 'name of beneficiary' in key_lower:
                extracted_data['beneficiary_name'] = value
            elif ('ss#' in key_lower or 'tax id' in key_lower) and 'or' in key_lower:
                # This is "SS# or Tax ID#" field
                if value and value.strip():
                    extracted_data['beneficiary_ssn'] = value

        print(f"Textract extracted claim form data: {extracted_data}")
        print(f"All key-value pairs: {kvs}")

        return {
            'extracted': bool(extracted_data),
            'data': extracted_data,
            'all_kvs': kvs  # For debugging
        }

    except Exception as e:
        print(f"Error using Textract: {str(e)}")
        return {
            'extracted': False,
            'error': str(e),
            'data': {}
        }


if __name__ == '__main__':
    # Test the extraction functions
    base_path = Path(__file__).parent.parent / "Cases/Case_IRA-001-1_018_Thompson_Karen"

    print("=" * 80)
    print("TESTING TEXTRACT EXTRACTION")
    print("=" * 80)
    print()

    # Test death certificate
    print("Testing Death Certificate:")
    dc_result = extract_death_certificate_textract(base_path / "Death_Cert_Thompson_Jennifer.pdf")
    print(f"Result: {dc_result}")
    print()

    # Test driver's license
    print("Testing Driver's License:")
    dl_result = extract_drivers_license_textract(base_path / "CA_DL_018_Thompson_Karen.png")
    print(f"Result: {dl_result}")
    print()

    # Test claim form
    print("Testing Claim Form:")
    claim_result = extract_claim_form_textract(base_path / "Claim_Form_IRA-001-1_018_Thompson_Karen.pdf")
    print(f"Result: {claim_result}")
    print()
