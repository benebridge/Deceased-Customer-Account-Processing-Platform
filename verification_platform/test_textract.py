#!/usr/bin/env python3
"""
Test script to debug Textract death certificate verification
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add verification services to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'verification_services'))

from death_cert_verification.textract_verifier import TextractDeathCertVerifier

def test_textract():
    """Test Textract on latest uploaded death certificate"""

    # Get the latest file
    uploads_dir = "uploads/death_certs"
    files = [f for f in os.listdir(uploads_dir) if f.endswith('.pdf')]
    if not files:
        print("No PDF files found in uploads/death_certs")
        return

    # Sort by modification time and get latest
    files.sort(key=lambda x: os.path.getmtime(os.path.join(uploads_dir, x)), reverse=True)
    latest_file = files[0]
    file_path = os.path.join(uploads_dir, latest_file)

    print("=" * 80)
    print("TESTING TEXTRACT DEATH CERTIFICATE VERIFICATION")
    print("=" * 80)
    print(f"\nFile: {latest_file}")
    print(f"Full path: {file_path}")
    print(f"File size: {os.path.getsize(file_path)} bytes")
    print(f"File exists: {os.path.exists(file_path)}")

    # Check AWS credentials
    print("\n" + "=" * 80)
    print("AWS CREDENTIALS CHECK")
    print("=" * 80)
    print(f"AWS_ACCESS_KEY_ID: {os.getenv('AWS_ACCESS_KEY_ID')[:10]}... (masked)")
    print(f"AWS_SECRET_ACCESS_KEY: {os.getenv('AWS_SECRET_ACCESS_KEY')[:10]}... (masked)")
    print(f"AWS_REGION: {os.getenv('AWS_REGION')}")

    # Initialize verifier
    print("\n" + "=" * 80)
    print("INITIALIZING TEXTRACT VERIFIER")
    print("=" * 80)
    try:
        verifier = TextractDeathCertVerifier()
        print("✓ Verifier initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize verifier: {e}")
        import traceback
        traceback.print_exc()
        return

    # Test extraction
    print("\n" + "=" * 80)
    print("RUNNING TEXTRACT EXTRACTION")
    print("=" * 80)
    try:
        extracted_data = verifier._extract_with_textract(file_path)

        if extracted_data:
            print("✓ Textract extraction successful!")
            print(f"\nAverage confidence: {extracted_data.get('avg_confidence', 0):.2f}%")
            print(f"Number of blocks: {len(extracted_data.get('blocks', []))}")
            print(f"Form fields found: {len(extracted_data.get('form_fields', {}))}")
            print(f"Tables found: {len(extracted_data.get('tables', []))}")

            print("\n" + "-" * 80)
            print("RAW TEXT (first 500 chars):")
            print("-" * 80)
            raw_text = extracted_data.get('raw_text', '')
            print(raw_text[:500])

            print("\n" + "-" * 80)
            print("FORM FIELDS:")
            print("-" * 80)
            for key, value in extracted_data.get('form_fields', {}).items():
                print(f"  {key}: {value}")

        else:
            print("✗ Textract extraction returned None")

    except Exception as e:
        print(f"✗ Textract extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Test full verification
    print("\n" + "=" * 80)
    print("RUNNING FULL VERIFICATION")
    print("=" * 80)
    try:
        result = verifier.verify_death_certificate(
            file_path=file_path,
            expected_deceased_name="Mary Allen",
            expected_ssn=None,
            expected_date_of_death=None
        )

        print(f"✓ Verification complete!")
        print(f"\nStatus: {result.status.value}")
        print(f"Confidence: {result.confidence_score:.2f}")
        print(f"Method: {result.method.value}")
        print(f"Processing time: {result.processing_time_ms:.2f}ms")

        if result.error_message:
            print(f"\nError message: {result.error_message}")

        print("\n" + "-" * 80)
        print("PARSED DATA:")
        print("-" * 80)
        parsed = result.details.get('extracted_data', {})
        for key, value in parsed.items():
            print(f"  {key}: {value}")

        print("\n" + "-" * 80)
        print("VALIDATION RESULTS:")
        print("-" * 80)
        validation = result.details.get('validation_results', {})
        for key, value in validation.items():
            print(f"  {key}: {value}")

    except Exception as e:
        print(f"✗ Verification failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_textract()
