#!/usr/bin/env python3
"""
Database Query Helper for BeneBridge Mock Databases
Easy-to-use functions for querying mock data
"""

import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Optional

class BeneBridgeDB:
    """Helper class for querying BeneBridge mock databases"""

    def __init__(self, base_dir=None):
        if base_dir is None:
            base_dir = Path(__file__).parent

        self.dmf_db = base_dir / "dmf_mock.db"
        self.beneficiary_db = base_dir / "beneficiary_registry.db"
        self.identity_db = base_dir / "identity_verification.db"
        self.financial_db = base_dir / "financial_accounts.db"
        self.fraud_db = base_dir / "fraud_indicators.db"

    def _query(self, db_path, query, params=()):
        """Execute query and return results as list of dicts"""
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(query, params)
        results = [dict(row) for row in c.fetchall()]
        conn.close()
        return results

    # ========== DMF Queries ==========

    def get_deceased_by_ssn(self, ssn: str) -> Optional[Dict]:
        """Look up deceased person by SSN"""
        results = self._query(
            self.dmf_db,
            "SELECT * FROM deceased_persons WHERE ssn = ?",
            (ssn,)
        )
        return results[0] if results else None

    def get_deceased_by_case_id(self, case_id: int) -> Optional[Dict]:
        """Look up deceased person by case ID"""
        results = self._query(
            self.dmf_db,
            "SELECT * FROM deceased_persons WHERE case_id = ?",
            (case_id,)
        )
        return results[0] if results else None

    def get_deceased_by_name(self, full_name: str) -> List[Dict]:
        """Search deceased persons by name (fuzzy match)"""
        return self._query(
            self.dmf_db,
            "SELECT * FROM deceased_persons WHERE full_name LIKE ?",
            (f"%{full_name}%",)
        )

    def get_all_deceased(self) -> List[Dict]:
        """Get all deceased persons"""
        return self._query(
            self.dmf_db,
            "SELECT * FROM deceased_persons ORDER BY case_id"
        )

    # ========== Beneficiary Queries ==========

    def get_beneficiary_by_id(self, beneficiary_id: int) -> Optional[Dict]:
        """Look up beneficiary by ID"""
        results = self._query(
            self.beneficiary_db,
            "SELECT * FROM beneficiaries WHERE beneficiary_id = ?",
            (beneficiary_id,)
        )
        return results[0] if results else None

    def get_beneficiary_by_ssn(self, ssn: str) -> Optional[Dict]:
        """Look up beneficiary by SSN"""
        results = self._query(
            self.beneficiary_db,
            "SELECT * FROM beneficiaries WHERE ssn = ?",
            (ssn,)
        )
        return results[0] if results else None

    def get_beneficiaries_for_account(self, account_id: str) -> List[Dict]:
        """Get all beneficiaries for a specific account with percentages"""
        return self._query(
            self.beneficiary_db,
            '''SELECT b.*, bd.percentage, bd.designation_type
               FROM beneficiaries b
               JOIN beneficiary_designations bd ON b.beneficiary_id = bd.beneficiary_id
               WHERE bd.account_id = ?
               ORDER BY bd.percentage DESC''',
            (account_id,)
        )

    def get_beneficiaries_for_case(self, case_id: int) -> List[Dict]:
        """Get all beneficiaries for a deceased case"""
        # First get all accounts for this case
        accounts = self.get_accounts_by_case(case_id)
        if not accounts:
            return []

        # Get beneficiaries for all accounts (deduplicated)
        beneficiary_ids = set()
        for account in accounts:
            beneficiaries = self.get_beneficiaries_for_account(account['account_id'])
            for b in beneficiaries:
                beneficiary_ids.add(b['beneficiary_id'])

        # Get full beneficiary records
        results = []
        for bid in beneficiary_ids:
            b = self.get_beneficiary_by_id(bid)
            if b:
                results.append(b)

        return results

    # ========== Identity Verification Queries ==========

    def verify_identity_by_dl(self, dl_number: str, dl_state: str) -> Optional[Dict]:
        """Verify identity using driver's license"""
        results = self._query(
            self.identity_db,
            '''SELECT * FROM identity_records
               WHERE drivers_license = ? AND dl_state = ?''',
            (dl_number, dl_state)
        )
        return results[0] if results else None

    def verify_identity_by_ssn(self, ssn: str) -> Optional[Dict]:
        """Verify identity using SSN"""
        results = self._query(
            self.identity_db,
            "SELECT * FROM identity_records WHERE ssn = ?",
            (ssn,)
        )
        return results[0] if results else None

    def get_identity_by_name_dob(self, full_name: str, dob: str) -> List[Dict]:
        """Look up identity by name and DOB"""
        return self._query(
            self.identity_db,
            '''SELECT * FROM identity_records
               WHERE full_name LIKE ? AND dob = ?''',
            (f"%{full_name}%", dob)
        )

    # ========== Financial Account Queries ==========

    def get_account_by_id(self, account_id: str) -> Optional[Dict]:
        """Get account details by ID"""
        results = self._query(
            self.financial_db,
            "SELECT * FROM accounts WHERE account_id = ?",
            (account_id,)
        )
        return results[0] if results else None

    def get_accounts_by_case(self, case_id: int) -> List[Dict]:
        """Get all accounts for a deceased case"""
        return self._query(
            self.financial_db,
            '''SELECT * FROM accounts
               WHERE deceased_case_id = ?
               ORDER BY balance DESC''',
            (case_id,)
        )

    def get_total_estate_value(self, case_id: int) -> float:
        """Calculate total estate value for a case"""
        accounts = self.get_accounts_by_case(case_id)
        return sum(account['balance'] for account in accounts)

    def get_institutions(self) -> List[Dict]:
        """Get all financial institutions"""
        return self._query(
            self.financial_db,
            "SELECT * FROM institutions ORDER BY name"
        )

    # ========== Fraud Detection Queries ==========

    def check_fraud_indicators(self, case_id: int) -> List[Dict]:
        """Check for fraud indicators on a case"""
        return self._query(
            self.fraud_db,
            '''SELECT * FROM fraud_indicators
               WHERE case_id = ? AND status = 'active'
               ORDER BY severity DESC''',
            (case_id,)
        )

    def check_beneficiary_fraud(self, beneficiary_id: int) -> List[Dict]:
        """Check if beneficiary has fraud flags"""
        return self._query(
            self.fraud_db,
            '''SELECT * FROM fraud_indicators
               WHERE beneficiary_id = ? AND status = 'active' ''',
            (beneficiary_id,)
        )

    def is_blacklisted(self, ssn: str) -> Optional[Dict]:
        """Check if person is on blacklist"""
        results = self._query(
            self.fraud_db,
            '''SELECT * FROM blacklisted_individuals
               WHERE ssn = ? AND status = 'active' ''',
            (ssn,)
        )
        return results[0] if results else None

    def get_all_fraud_cases(self) -> List[Dict]:
        """Get all cases with fraud indicators"""
        return self._query(
            self.fraud_db,
            '''SELECT * FROM fraud_indicators
               WHERE status = 'active'
               ORDER BY severity DESC, case_id'''
        )

    # ========== Comprehensive Case Queries ==========

    def get_complete_case(self, case_id: int) -> Dict:
        """Get complete case information including deceased, accounts, and beneficiaries"""
        deceased = self.get_deceased_by_case_id(case_id)
        accounts = self.get_accounts_by_case(case_id)
        fraud_indicators = self.check_fraud_indicators(case_id)

        # Get beneficiaries with their designations
        beneficiaries_with_accounts = []
        for account in accounts:
            beneficiaries = self.get_beneficiaries_for_account(account['account_id'])
            for b in beneficiaries:
                beneficiaries_with_accounts.append({
                    'beneficiary': {k: v for k, v in b.items() if k not in ['percentage', 'designation_type']},
                    'account_id': account['account_id'],
                    'percentage': b['percentage'],
                    'designation_type': b['designation_type']
                })

        return {
            'case_id': case_id,
            'deceased': deceased,
            'accounts': accounts,
            'total_estate_value': sum(a['balance'] for a in accounts),
            'beneficiaries': beneficiaries_with_accounts,
            'fraud_indicators': fraud_indicators,
            'has_fraud_flags': len(fraud_indicators) > 0
        }

    def print_case_summary(self, case_id: int):
        """Print human-readable case summary"""
        case = self.get_complete_case(case_id)

        print("=" * 80)
        print(f"CASE #{case_id} SUMMARY")
        print("=" * 80)

        if not case['deceased']:
            print("Case not found!")
            return

        d = case['deceased']
        print(f"\nDECEASED: {d['full_name']}")
        print(f"  SSN: {d['ssn']}")
        print(f"  DOB: {d['dob']}")
        print(f"  DOD: {d['dod']}")
        print(f"  Gender: {d['gender']}")
        print(f"  Address: {d['address_street']}, {d['address_city']}, {d['address_state']} {d['address_zip']}")

        print(f"\nFINANCIAL ACCOUNTS ({len(case['accounts'])})")
        print(f"  Total Estate Value: ${case['total_estate_value']:,.2f}")
        for account in case['accounts']:
            print(f"  - {account['account_id']}: {account['institution_name']} {account['account_type']}")
            print(f"    Balance: ${account['balance']:,.2f}")

        print(f"\nBENEFICIARIES ({len(set(b['beneficiary']['beneficiary_id'] for b in case['beneficiaries']))} unique)")
        for item in case['beneficiaries']:
            b = item['beneficiary']
            print(f"  - {b['full_name']} ({item['percentage']}% of {item['account_id']})")
            print(f"    Contact: {b['phone']}, {b['email']}")

        if case['fraud_indicators']:
            print(f"\n⚠️  FRAUD INDICATORS ({len(case['fraud_indicators'])})")
            for fi in case['fraud_indicators']:
                print(f"  - [{fi['severity'].upper()}] {fi['indicator_type']}: {fi['description']}")
        else:
            print(f"\n✓ No fraud indicators")

        print("=" * 80)


# ========== CLI Interface ==========

def main():
    """Command-line interface for querying databases"""
    import sys

    db = BeneBridgeDB()

    if len(sys.argv) < 2:
        print("BeneBridge Database Query Helper")
        print("\nUsage:")
        print("  python query_helper.py case <case_id>         - Show complete case summary")
        print("  python query_helper.py deceased <ssn>         - Look up deceased by SSN")
        print("  python query_helper.py beneficiary <ssn>      - Look up beneficiary by SSN")
        print("  python query_helper.py verify <dl> <state>    - Verify ID by driver's license")
        print("  python query_helper.py fraud                  - Show all fraud cases")
        print("  python query_helper.py all                    - List all cases")
        print("\nExamples:")
        print("  python query_helper.py case 1")
        print("  python query_helper.py deceased 400-36-9992")
        print("  python query_helper.py verify HE168575 MA")
        return

    command = sys.argv[1]

    if command == "case":
        if len(sys.argv) < 3:
            print("Usage: python query_helper.py case <case_id>")
            return
        case_id = int(sys.argv[2])
        db.print_case_summary(case_id)

    elif command == "deceased":
        if len(sys.argv) < 3:
            print("Usage: python query_helper.py deceased <ssn>")
            return
        ssn = sys.argv[2]
        result = db.get_deceased_by_ssn(ssn)
        if result:
            print(json.dumps(result, indent=2))
        else:
            print(f"No deceased person found with SSN: {ssn}")

    elif command == "beneficiary":
        if len(sys.argv) < 3:
            print("Usage: python query_helper.py beneficiary <ssn>")
            return
        ssn = sys.argv[2]
        result = db.get_beneficiary_by_ssn(ssn)
        if result:
            print(json.dumps(result, indent=2))
        else:
            print(f"No beneficiary found with SSN: {ssn}")

    elif command == "verify":
        if len(sys.argv) < 4:
            print("Usage: python query_helper.py verify <dl_number> <state>")
            return
        dl_number = sys.argv[2]
        state = sys.argv[3]
        result = db.verify_identity_by_dl(dl_number, state)
        if result:
            print(json.dumps(result, indent=2))
        else:
            print(f"No identity found with DL: {dl_number} ({state})")

    elif command == "fraud":
        fraud_cases = db.get_all_fraud_cases()
        print(f"\nFound {len(fraud_cases)} fraud indicators:\n")
        for fi in fraud_cases:
            print(f"Case {fi['case_id']} - Beneficiary {fi['beneficiary_id']}")
            print(f"  Type: {fi['indicator_type']}")
            print(f"  Severity: {fi['severity']}")
            print(f"  Description: {fi['description']}")
            print()

    elif command == "all":
        all_deceased = db.get_all_deceased()
        print(f"\nAll Cases ({len(all_deceased)}):\n")
        for d in all_deceased:
            fraud = db.check_fraud_indicators(d['case_id'])
            fraud_flag = " ⚠️ FRAUD" if fraud else ""
            print(f"Case {d['case_id']}: {d['full_name']} (DOD: {d['dod']}){fraud_flag}")

    else:
        print(f"Unknown command: {command}")
        print("Run without arguments to see usage")


if __name__ == "__main__":
    main()
