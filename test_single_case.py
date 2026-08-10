"""
Test script to generate a single case with enhanced visual styling
This will help us verify the improvements before regenerating all 500 cases
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generate_realistic_documents import SyntheticDataGenerator

# Generate just one case for testing
generator = SyntheticDataGenerator(output_dir='test_case')

# Clear test directory if exists
import shutil
if os.path.exists('test_case'):
    shutil.rmtree('test_case')

print("Generating single test case...")
case_data, case_dir = generator.create_complete_case(is_fraud=False)

print(f"\nTest case created: {case_data['case_number']}")
print(f"Location: {case_dir}")
print(f"Access Code: {case_data['access_code']}")
print(f"\nDocuments generated:")
print(f"  - death_certificate.pdf")
print(f"  - beneficiary_claim_form.pdf")
print(f"  - drivers_license_front.png")
print(f"  - drivers_license_back.png")
print(f"  - metadata.json")

print("\nPlease review the documents and let me know what visual improvements are needed.")

generator.close()
