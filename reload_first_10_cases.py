#!/usr/bin/env python3
"""
Reload database with only the first 10 cases from synthetic_cases folder
"""

import sqlite3
import json
import os
from datetime import datetime

# Get first 10 unique case folders (excluding duplicates with " 2")
cases_dir = 'synthetic_cases'
all_folders = sorted([f for f in os.listdir(cases_dir) if not f.endswith(' 2') and os.path.isdir(os.path.join(cases_dir, f))])
first_10_folders = all_folders[:10]

print("=" * 80)
print("Reloading Database with First 10 Cases")
print("=" * 80)
print("\nSelected cases:")
for i, folder in enumerate(first_10_folders, 1):
    print(f"  {i}. {folder}")

# Connect to database
conn = sqlite3.connect('benebridge.db')
c = conn.cursor()

# Clear existing data
print("\n1. Clearing existing cases and documents...")
c.execute('DELETE FROM documents')
c.execute('DELETE FROM cases')
print("   ✓ Cleared")

# Load the first 10 cases
print("\n2. Loading first 10 cases...")
for folder in first_10_folders:
    metadata_path = os.path.join(cases_dir, folder, 'metadata.json')

    if not os.path.exists(metadata_path):
        print(f"   ✗ Skipping {folder} - no metadata.json")
        continue

    with open(metadata_path, 'r') as f:
        data = json.load(f)

    # Map account_type to match database expectations
    account_type = data['account_type']
    if account_type == 'Brokerage':
        account_type = 'investment'
    elif account_type == 'Checking':
        account_type = 'checking'
    elif account_type == 'Savings':
        account_type = 'savings'
    elif account_type in ['401k', '401(k)']:
        account_type = '401k'
    elif account_type == 'IRA':
        account_type = 'IRA'

    # Insert case
    c.execute('''INSERT INTO cases (
        case_number, deceased_name, deceased_ssn, deceased_sex, date_of_death,
        beneficiary_name, beneficiary_ssn, beneficiary_email, beneficiary_phone,
        beneficiary_address,
        account_type, account_number, account_balance, financial_institution,
        death_cert_type, blockchain_hash, death_certificate_number,
        status, workflow_stage, priority, submission_date,
        id_verified, beneficiary_info_verified, access_code
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (data['case_number'],
         data['deceased_name'],
         data['deceased_ssn'],
         data.get('deceased_sex', 'M'),
         data['date_of_death'],
         data['beneficiary_name'],
         None,  # beneficiary_ssn not in metadata
         data['beneficiary_email'],
         data['beneficiary_phone'],
         data.get('beneficiary_address', ''),
         account_type,
         data['account_number'],
         float(data['account_balance']),
         data['financial_institution'],
         data.get('death_cert_type', 'physical'),
         data.get('blockchain_hash'),
         data.get('death_certificate_number'),
         data['status'],
         1,  # workflow_stage
         'medium',  # priority
         data['submission_date'],
         False,  # id_verified
         False,  # beneficiary_info_verified
         data.get('access_code', '')
        ))

    case_id = c.lastrowid

    # Insert documents
    docs = data.get('documents', {})
    doc_type_mapping = {
        'death_certificate': 'death_certificate',
        'drivers_license_front': 'id_front',
        'drivers_license_back': 'id_back',
        'beneficiary_claim_form': 'beneficiary_form'
    }

    for doc_key, doc_filename in docs.items():
        doc_path = f"synthetic_cases/{folder}/{doc_filename}"
        if os.path.exists(doc_path):
            doc_type = doc_type_mapping.get(doc_key, 'beneficiary_form')
            c.execute('''INSERT INTO documents (
                case_id, document_type, filename, file_path, uploaded_at
            ) VALUES (?, ?, ?, ?, ?)''',
                (case_id,
                 doc_type,
                 doc_filename,
                 doc_path,
                 datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))

    print(f"   ✓ Loaded {data['case_number']} - {data['deceased_name']} ({len(docs)} documents)")

conn.commit()

# Verify
c.execute('SELECT COUNT(*) FROM cases')
case_count = c.fetchone()[0]

c.execute('SELECT COUNT(*) FROM documents')
doc_count = c.fetchone()[0]

conn.close()

print("\n" + "=" * 80)
print("✓ Database Reloaded Successfully")
print("=" * 80)
print(f"\nTotal cases: {case_count}")
print(f"Total documents: {doc_count}")
print("\nYou can now access these cases at:")
print("  http://localhost:5007/workspace")
print("\nCase numbers:")
for folder in first_10_folders:
    print(f"  - {folder}")
