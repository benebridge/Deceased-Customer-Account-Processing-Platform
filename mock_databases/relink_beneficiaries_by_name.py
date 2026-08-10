#!/usr/bin/env python3
"""
Relink beneficiaries to deceased by matching last names
"""

import sqlite3
import random
from pathlib import Path
from collections import defaultdict

def main():
    base_dir = Path(__file__).parent

    print("=" * 80)
    print("RELINKING BENEFICIARIES TO DECEASED BY LAST NAME")
    print("=" * 80)
    print()

    # Get deceased persons
    conn_dmf = sqlite3.connect(base_dir / "dmf_mock.db")
    conn_dmf.row_factory = sqlite3.Row
    c_dmf = conn_dmf.cursor()
    c_dmf.execute("SELECT * FROM deceased_persons ORDER BY case_id")
    deceased_list = [dict(row) for row in c_dmf.fetchall()]
    conn_dmf.close()

    # Create deceased lookup by last name
    deceased_by_last_name = {}
    for d in deceased_list:
        last_name = d['last_name']
        if last_name not in deceased_by_last_name:
            deceased_by_last_name[last_name] = []
        deceased_by_last_name[last_name].append(d)

    print("Deceased persons by last name:")
    for last_name, persons in sorted(deceased_by_last_name.items()):
        names = ', '.join([p['full_name'] for p in persons])
        print(f"  {last_name}: {names}")
    print()

    # Get beneficiaries
    conn_ben = sqlite3.connect(base_dir / "beneficiary_registry.db")
    conn_ben.row_factory = sqlite3.Row
    c_ben = conn_ben.cursor()
    c_ben.execute("SELECT * FROM beneficiaries ORDER BY beneficiary_id")
    beneficiaries_list = [dict(row) for row in c_ben.fetchall()]
    conn_ben.close()

    # Group beneficiaries by last name
    beneficiaries_by_last_name = defaultdict(list)
    for b in beneficiaries_list:
        beneficiaries_by_last_name[b['last_name']].append(b)

    print("Beneficiaries by last name:")
    for last_name, bens in sorted(beneficiaries_by_last_name.items()):
        names = ', '.join([b['full_name'] for b in bens])
        print(f"  {last_name}: {names}")
    print()

    # Match beneficiaries to deceased
    print("=" * 80)
    print("MATCHING BENEFICIARIES TO DECEASED")
    print("=" * 80)
    print()

    matches = []
    unmatched_beneficiaries = []

    for ben in beneficiaries_list:
        ben_last_name = ben['last_name']

        # Try to find deceased with matching last name
        if ben_last_name in deceased_by_last_name:
            # Found match by last name
            deceased_matches = deceased_by_last_name[ben_last_name]
            # If multiple deceased with same last name, pick first one
            deceased = deceased_matches[0]
            matches.append({
                'beneficiary': ben,
                'deceased': deceased,
                'match_type': 'exact_last_name'
            })
            print(f"✓ {ben['full_name']} -> Case {deceased['case_id']}: {deceased['full_name']} (matching last name)")
        else:
            # No match found
            unmatched_beneficiaries.append(ben)
            print(f"⚠ {ben['full_name']} - No deceased with last name '{ben_last_name}'")

    print()
    print(f"Matched: {len(matches)} beneficiaries")
    print(f"Unmatched: {len(unmatched_beneficiaries)} beneficiaries")
    print()

    # For unmatched beneficiaries, assign to random deceased
    if unmatched_beneficiaries:
        print("Assigning unmatched beneficiaries to random deceased:")
        for ben in unmatched_beneficiaries:
            deceased = random.choice(deceased_list)
            matches.append({
                'beneficiary': ben,
                'deceased': deceased,
                'match_type': 'random'
            })
            print(f"  {ben['full_name']} -> Case {deceased['case_id']}: {deceased['full_name']} (random)")
        print()

    # Now update the accounts to reflect the new deceased assignments
    print("=" * 80)
    print("UPDATING ACCOUNT ASSIGNMENTS")
    print("=" * 80)
    print()

    # Get current accounts
    conn_fin = sqlite3.connect(base_dir / "financial_accounts.db")
    conn_fin.row_factory = sqlite3.Row
    c_fin = conn_fin.cursor()
    c_fin.execute("SELECT * FROM accounts ORDER BY account_id")
    accounts_list = [dict(row) for row in c_fin.fetchall()]
    conn_fin.close()

    # Get beneficiary designations
    conn_ben = sqlite3.connect(base_dir / "beneficiary_registry.db")
    conn_ben.row_factory = sqlite3.Row
    c_ben = conn_ben.cursor()
    c_ben.execute("SELECT * FROM beneficiary_designations")
    designations_list = [dict(row) for row in c_ben.fetchall()]
    conn_ben.close()

    # Create mapping: beneficiary_id -> deceased_case_id
    ben_to_deceased = {m['beneficiary']['beneficiary_id']: m['deceased']['case_id'] for m in matches}

    # Update accounts to match the new deceased assignments
    conn_fin = sqlite3.connect(base_dir / "financial_accounts.db")
    c_fin = conn_fin.cursor()

    updated_accounts = 0
    for account in accounts_list:
        # Find beneficiaries for this account
        account_designations = [d for d in designations_list if d['account_id'] == account['account_id']]

        if account_designations:
            # Get the first beneficiary for this account
            first_ben_id = account_designations[0]['beneficiary_id']

            # Get the deceased case for this beneficiary
            new_deceased_case_id = ben_to_deceased.get(first_ben_id)

            if new_deceased_case_id and new_deceased_case_id != account['deceased_case_id']:
                # Update the account
                c_fin.execute("UPDATE accounts SET deceased_case_id = ? WHERE account_id = ?",
                            (new_deceased_case_id, account['account_id']))
                updated_accounts += 1

                old_deceased = next((d for d in deceased_list if d['case_id'] == account['deceased_case_id']), None)
                new_deceased = next((d for d in deceased_list if d['case_id'] == new_deceased_case_id), None)

                print(f"  Account {account['account_id']}: Case {account['deceased_case_id']} ({old_deceased['full_name'] if old_deceased else 'Unknown'}) -> Case {new_deceased_case_id} ({new_deceased['full_name'] if new_deceased else 'Unknown'})")

    conn_fin.commit()
    conn_fin.close()

    print()
    print(f"✓ Updated {updated_accounts} accounts")
    print()

    # Print summary by deceased
    print("=" * 80)
    print("SUMMARY BY DECEASED")
    print("=" * 80)
    print()

    for deceased in sorted(deceased_list, key=lambda x: x['case_id']):
        # Find beneficiaries for this deceased
        deceased_beneficiaries = [m['beneficiary'] for m in matches if m['deceased']['case_id'] == deceased['case_id']]

        print(f"Case {deceased['case_id']}: {deceased['full_name']}")
        if deceased_beneficiaries:
            for ben in deceased_beneficiaries:
                print(f"  - {ben['full_name']}")
        else:
            print(f"  (No beneficiaries)")
        print()

    print("=" * 80)
    print("RELINKING COMPLETE")
    print("=" * 80)
    print()
    print("Next step: Regenerate PERSON_REFERENCE_FOR_FORMS.docx")

if __name__ == "__main__":
    main()
