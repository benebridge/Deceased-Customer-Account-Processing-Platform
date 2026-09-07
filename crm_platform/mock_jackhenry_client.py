#!/usr/bin/env python3
"""
Mock Jack Henry Client
Simulates Jack Henry API calls by querying local jackhenry_mock.db database
Provides same interface as real JackHenryClient for seamless integration
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional

MOCK_DATABASE = './jackhenry_mock.db'

class MockJackHenryClient:
    """
    Mock client that simulates Jack Henry Consumer API
    Queries local database instead of making real API calls
    """

    def __init__(self):
        """Initialize mock client"""
        self.db_path = MOCK_DATABASE
        print(f"[Mock Jack Henry Client] Initialized with database: {self.db_path}")

    def search_customer_by_ssn(self, ssn: str) -> Optional[Dict]:
        """
        Search for deceased customer by SSN

        Args:
            ssn: Social Security Number (format: XXX-XX-XXXX)

        Returns:
            Customer dict if found, None otherwise
        """
        # Normalize SSN (remove dashes if present)
        ssn_normalized = ssn.replace('-', '')
        ssn_formatted = f"{ssn_normalized[:3]}-{ssn_normalized[3:5]}-{ssn_normalized[5:]}"

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute('''
            SELECT * FROM customers
            WHERE ssn = ? OR ssn = ?
        ''', (ssn, ssn_formatted))

        row = c.fetchone()
        conn.close()

        if not row:
            return None

        # Convert to dict
        customer = dict(row)

        # Parse address JSON
        if customer['address_json']:
            customer['address'] = json.loads(customer['address_json'])

        return customer

    def search_customer_by_name_dob(self, first_name: str, last_name: str, dob: str) -> Optional[Dict]:
        """
        Search for deceased customer by name and date of birth

        Args:
            first_name: First name
            last_name: Last name
            dob: Date of birth (format: MM/DD/YYYY or YYYY-MM-DD)

        Returns:
            Customer dict if found, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute('''
            SELECT * FROM customers
            WHERE LOWER(given_name) = LOWER(?)
            AND LOWER(family_name) = LOWER(?)
            AND birthdate = ?
        ''', (first_name, last_name, dob))

        row = c.fetchone()
        conn.close()

        if not row:
            return None

        customer = dict(row)
        if customer['address_json']:
            customer['address'] = json.loads(customer['address_json'])

        return customer

    def get_customer_accounts(self, customer_sub: str) -> List[Dict]:
        """
        Get all accounts for a customer

        Args:
            customer_sub: Customer subject identifier

        Returns:
            List of account dicts
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute('''
            SELECT * FROM accounts
            WHERE customer_sub = ?
            ORDER BY account_type, account_id
        ''', (customer_sub,))

        rows = c.fetchall()
        conn.close()

        accounts = []
        for row in rows:
            account = dict(row)
            accounts.append(account)

        return accounts

    def get_account_beneficiaries(self, account_id: str) -> List[Dict]:
        """
        Get all beneficiaries for an account

        Args:
            account_id: Account identifier

        Returns:
            List of beneficiary dicts
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute('''
            SELECT * FROM beneficiaries
            WHERE account_id = ?
            ORDER BY is_primary DESC, percentage DESC
        ''', (account_id,))

        rows = c.fetchall()
        conn.close()

        beneficiaries = []
        for row in rows:
            beneficiary = dict(row)

            # Parse address JSON
            if beneficiary['address_json']:
                beneficiary['address'] = json.loads(beneficiary['address_json'])

            beneficiaries.append(beneficiary)

        return beneficiaries

    def get_death_notification(self, ssn: str) -> Optional[Dict]:
        """
        Get death notification record for customer

        Args:
            ssn: Social Security Number

        Returns:
            Death notification dict if found, None otherwise
        """
        # Normalize SSN
        ssn_normalized = ssn.replace('-', '')
        ssn_formatted = f"{ssn_normalized[:3]}-{ssn_normalized[3:5]}-{ssn_normalized[5:]}"

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute('''
            SELECT * FROM death_notifications
            WHERE customer_ssn = ? OR customer_ssn = ?
        ''', (ssn, ssn_formatted))

        row = c.fetchone()
        conn.close()

        if not row:
            return None

        return dict(row)

    def get_complete_customer_data(self, ssn: str) -> Optional[Dict]:
        """
        Get complete customer data including accounts and beneficiaries
        This is the primary method used for creating death claim cases

        Args:
            ssn: Social Security Number of deceased

        Returns:
            Complete customer data dict with accounts and beneficiaries, or None if not found
        """
        # Get customer
        customer = self.search_customer_by_ssn(ssn)
        if not customer:
            return None

        # Get death notification
        death_notification = self.get_death_notification(ssn)

        # Get accounts
        accounts = self.get_customer_accounts(customer['sub'])

        # Get beneficiaries for each account
        for account in accounts:
            account['beneficiaries'] = self.get_account_beneficiaries(account['account_id'])

        # Assemble complete data
        complete_data = {
            'customer': customer,
            'death_notification': death_notification,
            'accounts': accounts,
            'summary': {
                'total_accounts': len(accounts),
                'total_beneficiaries': sum(len(acc['beneficiaries']) for acc in accounts),
                'total_balance': sum(acc['balance_current'] or 0 for acc in accounts),
                'account_types': list(set(acc['account_type'] for acc in accounts))
            }
        }

        return complete_data

    def verify_ssn_exists(self, ssn: str) -> bool:
        """
        Quick check if SSN exists in database

        Args:
            ssn: Social Security Number

        Returns:
            True if customer exists, False otherwise
        """
        customer = self.search_customer_by_ssn(ssn)
        return customer is not None

    def get_all_deceased_customers(self) -> List[Dict]:
        """
        Get list of all deceased customers in database
        Useful for testing and demo purposes

        Returns:
            List of customer dicts with basic info
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute('''
            SELECT c.customer_id, c.full_name, c.ssn, c.birthdate,
                   d.date_of_death, d.notification_source
            FROM customers c
            LEFT JOIN death_notifications d ON c.ssn = d.customer_ssn
            ORDER BY c.full_name
        ''')

        rows = c.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_database_stats(self) -> Dict:
        """
        Get statistics about the mock database

        Returns:
            Dict with database statistics
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        stats = {}

        c.execute('SELECT COUNT(*) as count FROM customers')
        stats['total_customers'] = c.fetchone()['count']

        c.execute('SELECT COUNT(*) as count FROM accounts')
        stats['total_accounts'] = c.fetchone()['count']

        c.execute('SELECT COUNT(*) as count FROM beneficiaries')
        stats['total_beneficiaries'] = c.fetchone()['count']

        c.execute('SELECT COUNT(*) as count FROM death_notifications')
        stats['total_death_notifications'] = c.fetchone()['count']

        c.execute('SELECT SUM(balance_current) as total FROM accounts')
        result = c.fetchone()
        stats['total_balance'] = result['total'] if result['total'] else 0

        c.execute('SELECT account_type, COUNT(*) as count FROM accounts GROUP BY account_type')
        stats['accounts_by_type'] = {row['account_type']: row['count'] for row in c.fetchall()}

        conn.close()

        return stats


# Convenience function for Flask app
def create_mock_client() -> MockJackHenryClient:
    """Factory function to create mock client instance"""
    return MockJackHenryClient()


# Test function
if __name__ == '__main__':
    print("="*60)
    print("MOCK JACK HENRY CLIENT - TEST")
    print("="*60 + "\n")

    client = MockJackHenryClient()

    # Test 1: Get database stats
    print("Database Statistics:")
    stats = client.get_database_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Test 2: Search by SSN
    print("\n" + "="*60)
    print("Test: Search by SSN (Jennifer Thompson)")
    print("="*60)

    data = client.get_complete_customer_data('501-62-9628')
    if data:
        print(f"\n✓ Found customer: {data['customer']['full_name']}")
        print(f"  SSN: {data['customer']['ssn']}")
        print(f"  DOB: {data['customer']['birthdate']}")
        print(f"  Death Date: {data['death_notification']['date_of_death']}")
        print(f"  Total Accounts: {data['summary']['total_accounts']}")
        print(f"  Total Beneficiaries: {data['summary']['total_beneficiaries']}")
        print(f"  Total Balance: ${data['summary']['total_balance']:,.2f}")
        print(f"  Account Types: {', '.join(data['summary']['account_types'])}")

        print("\nAccounts:")
        for acc in data['accounts']:
            print(f"  - {acc['account_type']} {acc['account_number']}: ${acc['balance_current']:,.2f}")
            for ben in acc['beneficiaries']:
                print(f"    → {ben['full_name']} ({ben['percentage']}%)")
    else:
        print("✗ Customer not found")

    # Test 3: List all deceased customers
    print("\n" + "="*60)
    print("All Deceased Customers in Database:")
    print("="*60)

    all_deceased = client.get_all_deceased_customers()
    for customer in all_deceased[:10]:  # Show first 10
        print(f"  {customer['full_name']} | SSN: {customer['ssn']} | DOD: {customer['date_of_death']}")

    if len(all_deceased) > 10:
        print(f"  ... and {len(all_deceased) - 10} more")

    print("\n" + "="*60)
    print("Mock client is ready for integration!")
    print("="*60 + "\n")
