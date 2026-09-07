#!/usr/bin/env python3
"""
Test script to test Tesseract OCR death certificate verification
"""
import os
import sys

# Add verification services to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'verification_services'))

from death_cert_verification.tesseract_verifier import TesseractDeathCertVerifier

def test_tesseract():
    """Test Tesseract OCR on latest uploaded death certificate"""

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
    print("TESTING TESSERACT OCR DEATH CERTIFICATE VERIFICATION")
    print("=" * 80)
    print(f"\nFile: {latest_file}")
    print(f"Full path: {file_path}")
    print(f"File size: {os.path.getsize(file_path)} bytes")

    # Initialize verifier
    print("\n" + "=" * 80)
    print("INITIALIZING TESSERACT VERIFIER")
    print("=" * 80)
    try:
        verifier = TesseractDeathCertVerifier()
        print("✓ Tesseract verifier initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize verifier: {e}")
        import traceback
        traceback.print_exc()
        return

    # Test extraction
    print("\n" + "=" * 80)
    print("RUNNING TESSERACT OCR EXTRACTION")
    print("=" * 80)
    try:
        extracted_data = verifier._extract_with_tesseract(file_path)

        if extracted_data:
            print("✓ Tesseract OCR extraction successful!")
            print(f"\nAverage confidence: {extracted_data.get('avg_confidence', 0):.2f}%")

            print("\n" + "-" * 80)
            print("RAW TEXT (first 1000 chars):")
            print("-" * 80)
            raw_text = extracted_data.get('raw_text', '')
            print(raw_text[:1000])

        else:
            print("✗ Tesseract OCR extraction returned None")
            return

    except Exception as e:
        print(f"✗ Tesseract extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Test parsing
    print("\n" + "=" * 80)
    print("PARSING DEATH CERTIFICATE FIELDS")
    print("=" * 80)
    parsed = verifier._parse_wa_death_certificate(extracted_data)
    for key, value in parsed.items():
        print(f"  {key}: {value}")

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
    test_tesseract()
