#!/usr/bin/env python3
"""
Create accounts for deceased that don't have any, then link beneficiaries
"""

import sqlite3
import random
from pathlib import Path
from datetime import datetime, timedelta

def generate_account_number():
    """Generate account number"""
    return ''.join([str(random.randint(0, 9)) for _ in range(10)])

def main():
    base_dir = Path(__file__).parent

    # Get deceased without accounts
    conn_fin = sqlite3.connect(base_dir / "financial_accounts.db")
    conn_fin.row_factory = sqlite3.Row
    c_fin = conn_fin.cursor()

    c_fin.execute("SELECT deceased_case_id FROM accounts GROUP BY deceased_case_id")
    cases_with_accounts = set(row['deceased_case_id'] for row in c_fin.fetchall())

    # Get all deceased
    conn_dmf = sqlite3.connect(base_dir / "dmf_mock.db")
    conn_dmf.row_factory = sqlite3.Row
    c_dmf = conn_dmf.cursor()
    c_dmf.execute("SELECT * FROM deceased_persons ORDER BY case_id")
    all_deceased = [dict(row) for row in c_dmf.fetchall()]
    conn_dmf.close()

    # Find deceased without accounts
    deceased_without_accounts = [d for d in all_deceased if d['case_id'] not in cases_with_accounts]

    print("=" * 80)
    print("CREATING ACCOUNTS FOR DECEASED WITHOUT ACCOUNTS")
    print("=" * 80)
    print()

    print(f"Found {len(deceased_without_accounts)} deceased without accounts:")
    for d in deceased_without_accounts:
        print(f"  Case {d['case_id']}: {d['full_name']}")
    print()

    # Get next available account number
    c_fin.execute("SELECT MAX(CAST(SUBSTR(account_id, 5, 3) AS INTEGER)) as max_num FROM accounts")
    result = c_fin.fetchone()
    next_account_num = (result['max_num'] if result['max_num'] else 0) + 1

    # Create 1-2 accounts for each deceased without accounts
    new_accounts = []
    for deceased in deceased_without_accounts:
        num_accounts = random.randint(1, 2)

        for i in range(num_accounts):
            account_id = f"IRA-{next_account_num:03d}-{i+1}"
            balance = round(random.uniform(50000, 1000000), 2)
            opened_date = datetime.now() - timedelta(days=random.randint(365, 7300))
            last_activity = datetime.now() - timedelta(days=random.randint(1, 365))

            account = {
                'account_id': account_id,
                'deceased_case_id': deceased['case_id'],
                'institution_name': 'Community National Bank',
                'institution_type': 'bank',
                'routing_number': '122016066',
                'account_number': generate_account_number(),
                'account_type': 'IRA',
                'balance': balance,
                'status': 'active',
                'opened_date': opened_date.strftime("%Y-%m-%d"),
                'last_activity_date': last_activity.strftime("%Y-%m-%d")
            }
            new_accounts.append(account)

            print(f"  Creating {account_id} for Case {deceased['case_id']} - Balance: ${balance:,.2f}")

        next_account_num += 1

    # Insert new accounts
    for account in new_accounts:
        c_fin.execute('''INSERT INTO accounts
                        (account_id, deceased_case_id, institution_name, institution_type,
                         routing_number, account_number, account_type, balance, status,
                         opened_date, last_activity_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                     (account['account_id'], account['deceased_case_id'], account['institution_name'],
                      account['institution_type'], account['routing_number'], account['account_number'],
                      account['account_type'], account['balance'], account['status'],
                      account['opened_date'], account['last_activity_date']))

    conn_fin.commit()
    conn_fin.close()

    print()
    print(f"✓ Created {len(new_accounts)} new accounts")
    print()

    # Now link beneficiaries to these new accounts
    print("=" * 80)
    print("LINKING BENEFICIARIES TO NEW ACCOUNTS")
    print("=" * 80)
    print()

    # Get beneficiaries
    conn_ben = sqlite3.connect(base_dir / "beneficiary_registry.db")
    conn_ben.row_factory = sqlite3.Row
    c_ben = conn_ben.cursor()
    c_ben.execute("SELECT * FROM beneficiaries")
    all_beneficiaries = [dict(row) for row in c_ben.fetchall()]

    # Get existing designations
    c_ben.execute("SELECT beneficiary_id FROM beneficiary_designations")
    beneficiaries_with_designations = set(row['beneficiary_id'] for row in c_ben.fetchall())

    # Find unlinked beneficiaries
    unlinked_beneficiaries = [b for b in all_beneficiaries if b['beneficiary_id'] not in beneficiaries_with_designations]

    print(f"Found {len(unlinked_beneficiaries)} unlinked beneficiaries:")
    for b in unlinked_beneficiaries:
        print(f"  ID {b['beneficiary_id']}: {b['full_name']}")
    print()

    # Link them to the new accounts
    new_designations = []

    # Group new accounts by deceased_case_id
    accounts_by_case = {}
    for account in new_accounts:
        case_id = account['deceased_case_id']
        if case_id not in accounts_by_case:
            accounts_by_case[case_id] = []
        accounts_by_case[case_id].append(account)

    # Distribute unlinked beneficiaries to deceased without accounts
    deceased_without_accounts_ids = [d['case_id'] for d in deceased_without_accounts]

    # Calculate how many beneficiaries each should get (1-3 each)
    ben_distribution = {}
    for case_id in deceased_without_accounts_ids:
        num_bens = random.randint(1, min(3, len(unlinked_beneficiaries)))
        ben_distribution[case_id] = num_bens

    # Assign beneficiaries
    ben_index = 0
    for case_id in deceased_without_accounts_ids:
        num_bens_for_case = ben_distribution[case_id]
        case_accounts = accounts_by_case.get(case_id, [])

        if not case_accounts or ben_index >= len(unlinked_beneficiaries):
            continue

        deceased = next((d for d in deceased_without_accounts if d['case_id'] == case_id), None)

        print(f"Case {case_id}: {deceased['full_name'] if deceased else 'Unknown'}")

        for i in range(num_bens_for_case):
            if ben_index >= len(unlinked_beneficiaries):
                break

            beneficiary = unlinked_beneficiaries[ben_index]
            ben_index += 1

            print(f"  - Linking {beneficiary['full_name']}")

            # Create designations for this beneficiary across all accounts for this case
            for account in case_accounts:
                if num_bens_for_case == 1:
                    percentage = 100
                elif i == 0:
                    percentage = random.choice([50, 60, 70])
                elif i == 1 and num_bens_for_case == 2:
                    # Calculate remainder
                    existing = sum(d['percentage'] for d in new_designations if d['account_id'] == account['account_id'])
                    percentage = 100 - existing
                else:
                    # Third beneficiary
                    existing = sum(d['percentage'] for d in new_designations if d['account_id'] == account['account_id'])
                    percentage = 100 - existing

                designation = {
                    'account_id': account['account_id'],
                    'beneficiary_id': beneficiary['beneficiary_id'],
                    'percentage': percentage,
                    'designation_type': 'primary',
                    'designated_date': (datetime.now() - timedelta(days=random.randint(365, 3650))).strftime("%Y-%m-%d")
                }
                new_designations.append(designation)

        print()

    # Insert new designations
    for des in new_designations:
        c_ben.execute('''INSERT INTO beneficiary_designations
                        (account_id, beneficiary_id, percentage, designation_type, designated_date)
                        VALUES (?, ?, ?, ?, ?)''',
                     (des['account_id'], des['beneficiary_id'], des['percentage'],
                      des['designation_type'], des['designated_date']))

    conn_ben.commit()
    conn_ben.close()

    print(f"✓ Created {len(new_designations)} new beneficiary designations")
    print()

    print("=" * 80)
    print("COMPLETE")
    print("=" * 80)
    print()
    print("All deceased now have accounts and beneficiaries!")

if __name__ == "__main__":
    main()
