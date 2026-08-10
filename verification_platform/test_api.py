#!/usr/bin/env python3
"""
Test the verification API with an existing death certificate
"""
import requests
import json
import time

BASE_URL = "http://localhost:5008"

def test_death_cert_verification():
    """Test death certificate verification via API"""

    print("=" * 80)
    print("TESTING DEATH CERTIFICATE VERIFICATION API")
    print("=" * 80)

    # Get the most recent session from database
    import sqlite3
    conn = sqlite3.connect('verification_platform.db')
    c = conn.cursor()

    # Get latest session with uploaded death cert
    c.execute('''SELECT session_id FROM verification_sessions
                 WHERE death_cert_uploaded = 1
                 ORDER BY created_at DESC LIMIT 1''')
    result = c.fetchone()

    if not result:
        print("No sessions with uploaded death certificates found")
        return

    session_id = result[0]
    print(f"\nUsing session: {session_id}")

    # Trigger verification
    print(f"\nTriggering verification...")
    response = requests.post(f"{BASE_URL}/verify/{session_id}")

    print(f"\nResponse status: {response.status_code}")
    print(f"\nResponse body:")
    result = response.json()
    print(json.dumps(result, indent=2))

    # Check results
    if 'death_cert_result' in result:
        dc_result = result['death_cert_result']
        print("\n" + "=" * 80)
        print("DEATH CERTIFICATE VERIFICATION RESULT")
        print("=" * 80)
        print(f"Status: {dc_result['status']}")
        print(f"Confidence: {dc_result['confidence']:.2f}%")
        print(f"Method: {dc_result['method']}")
        print(f"Processing time: {dc_result['processing_time_ms']:.2f}ms")

        if 'details' in dc_result:
            details = dc_result['details']

            if 'extracted_data' in details:
                print("\n" + "-" * 80)
                print("EXTRACTED DATA:")
                print("-" * 80)
                for key, value in details['extracted_data'].items():
                    print(f"  {key}: {value}")

            if 'validation_results' in details:
                print("\n" + "-" * 80)
                print("VALIDATION RESULTS:")
                print("-" * 80)
                for key, value in details['validation_results'].items():
                    print(f"  {key}: {value}")

            if 'ocr_engine' in details:
                print(f"\nOCR Engine: {details['ocr_engine']}")
                print(f"Average OCR Confidence: {details.get('avg_confidence', 0):.2f}%")

    conn.close()

if __name__ == '__main__':
    test_death_cert_verification()
