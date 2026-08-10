#!/usr/bin/env python3
"""
Organize all claim forms into case folders
Each case folder contains:
- Beneficiary Claim Form
- Corresponding Driver's License
- Corresponding Death Certificate
"""

import sqlite3
import shutil
from pathlib import Path

def main():
    base_dir = Path(__file__).parent

    # Source directories
    death_certs_dir = base_dir / "Mock Death Certs"
    drivers_licenses_dir = base_dir / "Generated_Driver_Licenses"
    claim_forms_dir = base_dir / "Generated_Claim_Forms"

    # Output directory
    cases_dir = base_dir / "Cases"
    cases_dir.mkdir(exist_ok=True)

    # Database paths
    db_dir = base_dir / "mock_databases"
    beneficiary_db = db_dir / "beneficiary_registry.db"
    financial_db = db_dir / "financial_accounts.db"
    dmf_db = db_dir / "dmf_mock.db"

    print("=" * 80)
    print("ORGANIZING DOCUMENTS INTO CASE FOLDERS")
    print("=" * 80)
    print()

    # Get all claim forms
    claim_forms = list(claim_forms_dir.glob("Claim_Form_*.pdf"))
    print(f"Found {len(claim_forms)} claim forms to organize")
    print()

    # Connect to databases
    conn_ben = sqlite3.connect(beneficiary_db)
    conn_ben.row_factory = sqlite3.Row
    c_ben = conn_ben.cursor()

    conn_fin = sqlite3.connect(financial_db)
    conn_fin.row_factory = sqlite3.Row
    c_fin = conn_fin.cursor()

    conn_dmf = sqlite3.connect(dmf_db)
    conn_dmf.row_factory = sqlite3.Row
    c_dmf = conn_dmf.cursor()

    success_count = 0

    for claim_form_path in claim_forms:
        # Parse filename: Claim_Form_{account_id}_{beneficiary_id}_{last_name}_{first_name}.pdf
        filename = claim_form_path.stem
        parts = filename.split('_')

        # Extract account_id and beneficiary_id
        # Format: Claim_Form_IRA-XXX-X_YYY_LastName_FirstName
        account_id = parts[2]  # e.g., IRA-001-1
        beneficiary_id = int(parts[3])  # e.g., 018
        last_name = parts[4]
        first_name = parts[5]

        # Get beneficiary info
        c_ben.execute("SELECT * FROM beneficiaries WHERE beneficiary_id = ?", (beneficiary_id,))
        beneficiary = c_ben.fetchone()

        if not beneficiary:
            print(f"⚠️  Skipping: Beneficiary {beneficiary_id} not found")
            continue

        # Get account info
        c_fin.execute("SELECT * FROM accounts WHERE account_id = ?", (account_id,))
        account = c_fin.fetchone()

        if not account:
            print(f"⚠️  Skipping: Account {account_id} not found")
            continue

        # Get deceased info
        deceased_case_id = account['deceased_case_id']
        c_dmf.execute("SELECT * FROM deceased_persons WHERE case_id = ?", (deceased_case_id,))
        deceased = c_dmf.fetchone()

        if not deceased:
            print(f"⚠️  Skipping: Deceased case {deceased_case_id} not found")
            continue

        # Create case folder name
        case_folder_name = f"Case_{account_id}_{beneficiary_id:03d}_{last_name}_{first_name}"
        case_folder = cases_dir / case_folder_name
        case_folder.mkdir(exist_ok=True)

        # Find and copy claim form
        claim_dest = case_folder / claim_form_path.name
        shutil.copy2(claim_form_path, claim_dest)

        # Find and copy driver's license
        dl_filename = f"CA_DL_{beneficiary_id:03d}_{last_name}_{first_name}.png"
        dl_source = drivers_licenses_dir / dl_filename

        if dl_source.exists():
            dl_dest = case_folder / dl_filename
            shutil.copy2(dl_source, dl_dest)
        else:
            print(f"  ⚠️  Driver's license not found: {dl_filename}")

        # Find and copy death certificate
        # Death certificates are named by deceased person
        deceased_last = deceased['last_name']
        deceased_first = deceased['first_name']

        # Try to find death certificate (could be PDF)
        death_cert_found = False

        # Look for PDF with deceased person's name
        for dc_file in death_certs_dir.glob(f"*{deceased_last}*{deceased_first}*.pdf"):
            dc_dest = case_folder / f"Death_Cert_{deceased_last}_{deceased_first}.pdf"
            shutil.copy2(dc_file, dc_dest)
            death_cert_found = True
            break

        # Also check for just last name match
        if not death_cert_found:
            for dc_file in death_certs_dir.glob(f"*{deceased_last}*.pdf"):
                dc_dest = case_folder / f"Death_Cert_{deceased_last}_{deceased_first}.pdf"
                shutil.copy2(dc_file, dc_dest)
                death_cert_found = True
                break

        if not death_cert_found:
            print(f"  ⚠️  Death certificate not found for: {deceased['full_name']}")

        print(f"✓ Created case folder: {case_folder_name}")
        success_count += 1

    conn_ben.close()
    conn_fin.close()
    conn_dmf.close()

    print()
    print("=" * 80)
    print("ORGANIZATION COMPLETE")
    print("=" * 80)
    print(f"Successfully created {success_count} case folders")
    print(f"Location: {cases_dir}")
    print()
    print("Each case folder contains:")
    print("  - Beneficiary Claim Form")
    print("  - Driver's License")
    print("  - Death Certificate")
    print()

if __name__ == "__main__":
    main()
