"""
Synthetic Core Banking System API Mock
This simulates a real bank's core banking system (Jack Henry, Fiserv, FIS, etc.)
with realistic data structures and API patterns.

In production, this would be replaced with actual API calls to the bank's core system.
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class CoreBankingSystemMock:
    """
    Mock implementation of a core banking system API.

    Real integration points would be:
    - Jack Henry: Symitar/Episys REST API
    - Fiserv: DNA Platform API
    - FIS: Horizon/IBS API

    This mock provides the same interface and data structures.
    """

    def __init__(self):
        # Synthetic account database
        self.accounts = self._generate_synthetic_accounts()
        self.beneficiary_designations = self._generate_beneficiary_designations()
        self.account_holders = self._generate_account_holders()

    def _generate_synthetic_accounts(self) -> Dict:
        """Generate realistic synthetic account data"""
        return {
            'IRA-2019-8821': {
                'account_number': 'IRA-2019-8821',
                'account_type': 'IRA',
                'product_code': 'TRAD_IRA',
                'account_status': 'ACTIVE',
                'open_date': '2019-03-15',
                'current_balance': 127500.00,
                'available_balance': 127500.00,
                'ytd_contributions': 0.00,
                'ytd_distributions': 0.00,
                'tax_year': 2024,
                'custodian': 'Community National Bank',
                'branch': '001',
                'officer_code': 'JD001',
                'last_transaction_date': '2024-12-15',
                'maturity_date': None,
                'rate': 0.00,
                'primary_holder': {
                    'name': 'Michael Motamed',
                    'ssn': '123-45-6789',
                    'dob': '1955-08-22',
                    'address': '123 Main St, Springfield, IL 62701',
                    'phone': '(217) 555-1234',
                    'email': 'michael.motamed@example.com'
                },
                'beneficiaries': ['BEN-001'],
                'restrictions': [],
                'holds': [],
                'liens': []
            },
            'IRA-2021-4412': {
                'account_number': 'IRA-2021-4412',
                'account_type': 'IRA',
                'product_code': 'ROTH_IRA',
                'account_status': 'ACTIVE',
                'open_date': '2021-06-10',
                'current_balance': 45200.00,
                'available_balance': 45200.00,
                'ytd_contributions': 6500.00,
                'ytd_distributions': 0.00,
                'tax_year': 2024,
                'custodian': 'Community National Bank',
                'branch': '002',
                'officer_code': 'SM002',
                'last_transaction_date': '2024-11-30',
                'maturity_date': None,
                'rate': 0.00,
                'primary_holder': {
                    'name': 'Sarah Johnson',
                    'ssn': '234-56-7890',
                    'dob': '1968-03-14',
                    'address': '456 Oak Ave, Springfield, IL 62702',
                    'phone': '(217) 555-5678',
                    'email': 'sarah.johnson@example.com'
                },
                'beneficiaries': ['BEN-002', 'BEN-003'],  # Multiple beneficiaries
                'restrictions': [],
                'holds': [],
                'liens': []
            },
            '401K-2018-9923': {
                'account_number': '401K-2018-9923',
                'account_type': '401K',
                'product_code': '401K_PRETAX',
                'account_status': 'ACTIVE',
                'open_date': '2018-01-05',
                'current_balance': 285000.00,
                'available_balance': 285000.00,
                'ytd_contributions': 22500.00,
                'ytd_distributions': 0.00,
                'tax_year': 2024,
                'custodian': 'Community National Bank',
                'branch': '001',
                'officer_code': 'JD001',
                'employer_id': 'EMP-001',
                'employer_name': 'Acme Corporation',
                'last_transaction_date': '2024-12-20',
                'maturity_date': None,
                'rate': 0.00,
                'primary_holder': {
                    'name': 'Robert Williams',
                    'ssn': '345-67-8901',
                    'dob': '1972-11-08',
                    'address': '789 Elm St, Springfield, IL 62703',
                    'phone': '(217) 555-9012',
                    'email': 'robert.williams@example.com'
                },
                'beneficiaries': ['BEN-004'],
                'restrictions': [],
                'holds': [],
                'liens': []
            },
            'TOD-2020-3344': {
                'account_number': 'TOD-2020-3344',
                'account_type': 'TOD',
                'product_code': 'TOD_SAVINGS',
                'account_status': 'ACTIVE',
                'open_date': '2020-09-12',
                'current_balance': 68750.00,
                'available_balance': 68750.00,
                'ytd_contributions': 0.00,
                'ytd_distributions': 0.00,
                'tax_year': 2024,
                'custodian': 'Community National Bank',
                'branch': '003',
                'officer_code': 'AM003',
                'last_transaction_date': '2024-12-10',
                'maturity_date': None,
                'rate': 2.50,
                'primary_holder': {
                    'name': 'Elizabeth Davis',
                    'ssn': '456-78-9012',
                    'dob': '1950-05-20',
                    'address': '321 Pine Rd, Springfield, IL 62704',
                    'phone': '(217) 555-3456',
                    'email': 'elizabeth.davis@example.com'
                },
                'beneficiaries': ['BEN-005', 'BEN-006'],
                'restrictions': [],
                'holds': [],
                'liens': []
            }
        }

    def _generate_beneficiary_designations(self) -> Dict:
        """Generate realistic beneficiary designation records"""
        return {
            'BEN-001': {
                'designation_id': 'BEN-001',
                'account_number': 'IRA-2019-8821',
                'beneficiary_type': 'PRIMARY',
                'beneficiary_name': 'Rosa Harms',
                'beneficiary_ssn': '987-65-4321',
                'beneficiary_dob': '1960-02-15',
                'relationship': 'Spouse',
                'allocation_percentage': 100.0,
                'designation_date': '2019-03-15',
                'last_updated': '2019-03-15',
                'updated_by': 'Account Holder',
                'contingent': None,
                'per_stirpes': False,
                'address': '123 Main St, Springfield, IL 62701',
                'phone': '(217) 555-7890',
                'email': 'rosa.harms@example.com'
            },
            'BEN-002': {
                'designation_id': 'BEN-002',
                'account_number': 'IRA-2021-4412',
                'beneficiary_type': 'PRIMARY',
                'beneficiary_name': 'David Johnson',
                'beneficiary_ssn': '876-54-3210',
                'beneficiary_dob': '1990-07-22',
                'relationship': 'Child',
                'allocation_percentage': 50.0,
                'designation_date': '2021-06-10',
                'last_updated': '2021-06-10',
                'updated_by': 'Account Holder',
                'contingent': 'BEN-003',
                'per_stirpes': False,
                'address': '789 River Rd, Chicago, IL 60601',
                'phone': '(312) 555-1111',
                'email': 'david.johnson@example.com'
            },
            'BEN-003': {
                'designation_id': 'BEN-003',
                'account_number': 'IRA-2021-4412',
                'beneficiary_type': 'PRIMARY',
                'beneficiary_name': 'Emily Johnson',
                'beneficiary_ssn': '765-43-2109',
                'beneficiary_dob': '1992-11-30',
                'relationship': 'Child',
                'allocation_percentage': 50.0,
                'designation_date': '2021-06-10',
                'last_updated': '2021-06-10',
                'updated_by': 'Account Holder',
                'contingent': None,
                'per_stirpes': False,
                'address': '456 Lake Ave, Peoria, IL 61602',
                'phone': '(309) 555-2222',
                'email': 'emily.johnson@example.com'
            },
            'BEN-004': {
                'designation_id': 'BEN-004',
                'account_number': '401K-2018-9923',
                'beneficiary_type': 'PRIMARY',
                'beneficiary_name': 'Jennifer Williams',
                'beneficiary_ssn': '654-32-1098',
                'beneficiary_dob': '1975-04-18',
                'relationship': 'Spouse',
                'allocation_percentage': 100.0,
                'designation_date': '2018-01-05',
                'last_updated': '2022-08-15',
                'updated_by': 'Account Holder',
                'contingent': None,
                'per_stirpes': False,
                'address': '789 Elm St, Springfield, IL 62703',
                'phone': '(217) 555-9013',
                'email': 'jennifer.williams@example.com'
            },
            'BEN-005': {
                'designation_id': 'BEN-005',
                'account_number': 'TOD-2020-3344',
                'beneficiary_type': 'PRIMARY',
                'beneficiary_name': 'Thomas Davis',
                'beneficiary_ssn': '543-21-0987',
                'beneficiary_dob': '1982-09-05',
                'relationship': 'Child',
                'allocation_percentage': 60.0,
                'designation_date': '2020-09-12',
                'last_updated': '2023-01-20',
                'updated_by': 'Account Holder',
                'contingent': None,
                'per_stirpes': True,
                'address': '111 Maple Dr, Bloomington, IL 61701',
                'phone': '(309) 555-3333',
                'email': 'thomas.davis@example.com'
            },
            'BEN-006': {
                'designation_id': 'BEN-006',
                'account_number': 'TOD-2020-3344',
                'beneficiary_type': 'PRIMARY',
                'beneficiary_name': 'Margaret Davis',
                'beneficiary_ssn': '432-10-9876',
                'beneficiary_dob': '1985-12-12',
                'relationship': 'Child',
                'allocation_percentage': 40.0,
                'designation_date': '2020-09-12',
                'last_updated': '2023-01-20',
                'updated_by': 'Account Holder',
                'contingent': None,
                'per_stirpes': True,
                'address': '222 Cedar Ln, Decatur, IL 62521',
                'phone': '(217) 555-4444',
                'email': 'margaret.davis@example.com'
            }
        }

    def _generate_account_holders(self) -> Dict:
        """Generate account holder records for death verification"""
        return {
            '123-45-6789': {
                'ssn': '123-45-6789',
                'name': 'Michael Motamed',
                'dob': '1955-08-22',
                'status': 'DECEASED',
                'date_of_death': '2024-11-15',
                'death_verified': True,
                'death_verified_date': '2024-11-20',
                'death_verified_method': 'State Registry',
                'accounts': ['IRA-2019-8821']
            },
            '234-56-7890': {
                'ssn': '234-56-7890',
                'name': 'Sarah Johnson',
                'dob': '1968-03-14',
                'status': 'ACTIVE',
                'date_of_death': None,
                'death_verified': False,
                'death_verified_date': None,
                'death_verified_method': None,
                'accounts': ['IRA-2021-4412']
            }
        }

    # =================== API METHODS (What production integration would call) ===================

    def lookup_account(self, account_number: str) -> Optional[Dict]:
        """
        Look up account details from core banking system.

        In production: GET /api/v1/accounts/{account_number}
        """
        return self.accounts.get(account_number)

    def get_beneficiary_designations(self, account_number: str) -> List[Dict]:
        """
        Fetch all beneficiary designations for an account.

        In production: GET /api/v1/accounts/{account_number}/beneficiaries
        """
        beneficiaries = []
        for ben_id, ben_data in self.beneficiary_designations.items():
            if ben_data['account_number'] == account_number:
                beneficiaries.append(ben_data)

        # Sort by allocation percentage (primary beneficiaries first)
        beneficiaries.sort(key=lambda x: x['allocation_percentage'], reverse=True)
        return beneficiaries

    def verify_account_holder(self, name: str, ssn: str) -> Dict:
        """
        Verify deceased account holder identity.

        In production: POST /api/v1/verification/account-holder
        """
        holder = self.account_holders.get(ssn)

        if not holder:
            return {
                'verified': False,
                'reason': 'SSN not found in system',
                'match_score': 0
            }

        # Name matching (fuzzy match in production)
        name_match = holder['name'].lower() == name.lower()

        if name_match:
            return {
                'verified': True,
                'match_score': 100,
                'holder_info': holder
            }
        else:
            return {
                'verified': False,
                'reason': 'Name does not match SSN on file',
                'match_score': 45,
                'expected_name': holder['name']
            }

    def get_account_balance(self, account_number: str) -> Optional[Dict]:
        """
        Get real-time account balance.

        In production: GET /api/v1/accounts/{account_number}/balance
        """
        account = self.lookup_account(account_number)
        if not account:
            return None

        return {
            'account_number': account_number,
            'current_balance': account['current_balance'],
            'available_balance': account['available_balance'],
            'pending_transactions': 0.00,
            'holds': sum([h['amount'] for h in account.get('holds', [])]),
            'as_of_date': datetime.now().isoformat()
        }

    def check_account_restrictions(self, account_number: str) -> Dict:
        """
        Check for liens, holds, legal restrictions.

        In production: GET /api/v1/accounts/{account_number}/restrictions
        """
        account = self.lookup_account(account_number)
        if not account:
            return {'error': 'Account not found'}

        return {
            'account_number': account_number,
            'has_restrictions': len(account['restrictions']) > 0 or len(account['holds']) > 0 or len(account['liens']) > 0,
            'restrictions': account['restrictions'],
            'holds': account['holds'],
            'liens': account['liens'],
            'can_distribute': len(account['restrictions']) == 0 and len(account['liens']) == 0
        }

    def record_death_claim(self, account_number: str, claim_data: Dict) -> Dict:
        """
        Record death claim in core system (creates hold on account).

        In production: POST /api/v1/claims/death
        """
        account = self.lookup_account(account_number)
        if not account:
            return {'success': False, 'error': 'Account not found'}

        # In real system, this would create a hold/restriction on the account
        claim_id = f"CLM-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

        return {
            'success': True,
            'claim_id': claim_id,
            'account_number': account_number,
            'claim_status': 'PENDING',
            'hold_placed': True,
            'hold_amount': account['current_balance'],
            'created_at': datetime.now().isoformat()
        }

    def search_accounts_by_ssn(self, ssn: str) -> List[Dict]:
        """
        Find all accounts for a given SSN (deceased person).

        In production: GET /api/v1/accounts/search?ssn={ssn}
        """
        accounts = []
        for account_number, account_data in self.accounts.items():
            if account_data['primary_holder']['ssn'] == ssn:
                accounts.append(account_data)
        return accounts

    def validate_beneficiary_match(self, account_number: str, beneficiary_name: str, beneficiary_ssn: str) -> Dict:
        """
        Validate beneficiary matches designation on file.

        In production: POST /api/v1/accounts/{account_number}/validate-beneficiary
        """
        beneficiaries = self.get_beneficiary_designations(account_number)

        for ben in beneficiaries:
            if ben['beneficiary_ssn'] == beneficiary_ssn:
                name_match = ben['beneficiary_name'].lower() == beneficiary_name.lower()
                return {
                    'is_valid_beneficiary': True,
                    'name_matches': name_match,
                    'match_score': 100 if name_match else 85,
                    'beneficiary_on_file': ben,
                    'allocation_percentage': ben['allocation_percentage']
                }

        return {
            'is_valid_beneficiary': False,
            'name_matches': False,
            'match_score': 0,
            'reason': 'SSN not found in beneficiary designations'
        }

    def get_transaction_history(self, account_number: str, days: int = 90) -> List[Dict]:
        """
        Get recent transaction history.

        In production: GET /api/v1/accounts/{account_number}/transactions?days={days}
        """
        # Mock transaction history
        account = self.lookup_account(account_number)
        if not account:
            return []

        transactions = []
        base_date = datetime.now()

        # Generate some realistic transactions
        for i in range(5):
            trans_date = base_date - timedelta(days=random.randint(1, days))
            transactions.append({
                'transaction_id': f"TXN-{trans_date.strftime('%Y%m%d')}-{random.randint(1000, 9999)}",
                'date': trans_date.strftime('%Y-%m-%d'),
                'type': random.choice(['INTEREST', 'DIVIDEND', 'CONTRIBUTION', 'FEE']),
                'amount': round(random.uniform(-50, 500), 2),
                'balance_after': account['current_balance'],
                'description': random.choice([
                    'Quarterly Interest Payment',
                    'Monthly Dividend',
                    'Annual Maintenance Fee',
                    'Contribution - Payroll Deduction'
                ])
            })

        transactions.sort(key=lambda x: x['date'], reverse=True)
        return transactions


# Singleton instance
core_banking_api = CoreBankingSystemMock()


def get_core_banking_api():
    """
    Get the core banking API instance.

    In production, this would initialize connection to real core system:
    - Load API credentials from secure vault
    - Establish authenticated session
    - Return API client
    """
    return core_banking_api
