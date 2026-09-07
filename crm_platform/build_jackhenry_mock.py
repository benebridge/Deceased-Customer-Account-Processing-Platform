#!/usr/bin/env python3
"""
Build Jack Henry Mock Database
Consolidates data from existing mock databases into single Jack Henry-schema database
"""

import sqlite3
import json
from datetime import datetime

# Database paths
MOCK_DB_PATH = '../mock_databases'
DMF_DB = f'{MOCK_DB_PATH}/dmf_mock.db'
BENEFICIARY_DB = f'{MOCK_DB_PATH}/beneficiary_registry.db'
FINANCIAL_DB = f'{MOCK_DB_PATH}/financial_accounts.db'
OUTPUT_DB = './jackhenry_mock.db'

def create_jackhenry_schema(conn):
    """Create Jack Henry database schema (4 tables)"""
    c = conn.cursor()

    # Table 1: customers (deceased account holders)
    c.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            customer_id TEXT PRIMARY KEY,
            sub TEXT UNIQUE NOT NULL,
            given_name TEXT,
            family_name TEXT,
            full_name TEXT,
            email TEXT,
            email_verified INTEGER DEFAULT 0,
            phone_number TEXT,
            phone_number_verified INTEGER DEFAULT 0,
            birthdate TEXT,
            address_json TEXT,
            ssn TEXT UNIQUE,
            created_date TEXT NOT NULL,
            last_updated TEXT NOT NULL,
            last_synced TEXT NOT NULL
        )
    ''')

    # Table 2: accounts (financial accounts owned by deceased)
    c.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            account_id TEXT PRIMARY KEY,
            customer_sub TEXT NOT NULL,
            account_uuid TEXT,
            account_number TEXT UNIQUE,
            account_type TEXT,
            account_name TEXT,
            status TEXT DEFAULT 'active',
            balance_available REAL,
            balance_current REAL,
            balance_pending REAL,
            currency TEXT DEFAULT 'USD',
            opened_date TEXT,
            closed_date TEXT,
            is_primary INTEGER DEFAULT 0,
            created_date TEXT NOT NULL,
            last_updated TEXT NOT NULL,
            last_synced TEXT NOT NULL,
            fetched_date TEXT,
            FOREIGN KEY (customer_sub) REFERENCES customers(sub)
        )
    ''')

    # Table 3: beneficiaries (designated beneficiaries on accounts)
    c.execute('''
        CREATE TABLE IF NOT EXISTS beneficiaries (
            beneficiary_id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id TEXT NOT NULL,
            beneficiary_type TEXT NOT NULL,
            designation_type TEXT,
            full_name TEXT NOT NULL,
            first_name TEXT,
            middle_name TEXT,
            last_name TEXT,
            suffix TEXT,
            relationship TEXT,
            ssn TEXT,
            tax_id TEXT,
            date_of_birth TEXT,
            address_json TEXT,
            phone TEXT,
            email TEXT,
            percentage REAL,
            is_primary INTEGER DEFAULT 1,
            is_contingent INTEGER DEFAULT 0,
            share_type TEXT,
            created_date TEXT NOT NULL,
            last_updated TEXT NOT NULL,
            last_synced TEXT NOT NULL,
            FOREIGN KEY (account_id) REFERENCES accounts(account_id)
        )
    ''')

    # Table 4: death_notifications (death records from DMF)
    c.execute('''
        CREATE TABLE IF NOT EXISTS death_notifications (
            notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_ssn TEXT UNIQUE NOT NULL,
            customer_sub TEXT,
            full_name TEXT NOT NULL,
            first_name TEXT,
            last_name TEXT,
            date_of_death TEXT NOT NULL,
            date_of_birth TEXT,
            notification_source TEXT DEFAULT 'DMF',
            notification_date TEXT NOT NULL,
            verified INTEGER DEFAULT 1,
            created_date TEXT NOT NULL,
            FOREIGN KEY (customer_sub) REFERENCES customers(sub)
        )
    ''')

    conn.commit()
    print("✓ Created Jack Henry schema with 4 tables")

def populate_customers(conn):
    """Populate customers table from DMF database (deceased persons)"""
    c = conn.cursor()

    # Connect to DMF database
    dmf_conn = sqlite3.connect(DMF_DB)
    dmf_conn.row_factory = sqlite3.Row
    dmf_c = dmf_conn.cursor()

    dmf_c.execute('SELECT * FROM deceased_persons')
    deceased_records = dmf_c.fetchall()

    now = datetime.utcnow().isoformat()
    inserted = 0

    for record in deceased_records:
        # Skip records without SSN
        if not record['ssn']:
            continue

        # Create address JSON
        address_json = json.dumps({
            'street': record['address_street'],
            'city': record['address_city'],
            'state': record['address_state'],
            'zip': record['address_zip']
        })

        # Use SSN as customer_id and sub
        customer_id = f"CUST_{record['ssn'].replace('-', '')}"
        sub = customer_id

        try:
            c.execute('''
                INSERT INTO customers
                (customer_id, sub, given_name, family_name, full_name, email, email_verified,
                 phone_number, phone_number_verified, birthdate, address_json, ssn,
                 created_date, last_updated, last_synced)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                customer_id,
                sub,
                record['first_name'],
                record['last_name'],
                record['full_name'],
                None,  # email
                0,     # email_verified
                None,  # phone_number
                0,     # phone_number_verified
                record['dob'],
                address_json,
                record['ssn'],
                now,
                now,
                now
            ))
            inserted += 1
        except sqlite3.IntegrityError:
            # Duplicate SSN, skip
            continue

    conn.commit()
    dmf_conn.close()
    print(f"✓ Inserted {inserted} customers from DMF database")
    return inserted

def populate_accounts(conn):
    """Populate accounts table from financial_accounts database"""
    c = conn.cursor()

    # Connect to financial accounts database
    fin_conn = sqlite3.connect(FINANCIAL_DB)
    fin_conn.row_factory = sqlite3.Row
    fin_c = fin_conn.cursor()

    fin_c.execute('SELECT * FROM accounts')
    account_records = fin_c.fetchall()

    now = datetime.utcnow().isoformat()
    inserted = 0

    for record in account_records:
        # Get customer_sub based on deceased_case_id
        # First, get the deceased SSN from DMF
        dmf_conn = sqlite3.connect(DMF_DB)
        dmf_conn.row_factory = sqlite3.Row
        dmf_c = dmf_conn.cursor()

        dmf_c.execute('SELECT ssn FROM deceased_persons WHERE case_id = ?', (record['deceased_case_id'],))
        dmf_record = dmf_c.fetchone()
        dmf_conn.close()

        if not dmf_record or not dmf_record['ssn']:
            continue

        customer_sub = f"CUST_{dmf_record['ssn'].replace('-', '')}"

        # Verify customer exists
        c.execute('SELECT customer_id FROM customers WHERE sub = ?', (customer_sub,))
        if not c.fetchone():
            continue

        account_id = record['account_id']

        try:
            c.execute('''
                INSERT INTO accounts
                (account_id, customer_sub, account_uuid, account_number, account_type, account_name,
                 status, balance_available, balance_current, balance_pending, currency,
                 opened_date, closed_date, is_primary, created_date, last_updated, last_synced, fetched_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                account_id,
                customer_sub,
                account_id,  # account_uuid same as account_id
                record['account_number'],
                record['account_type'],
                f"{record['account_type']} Account",
                record['status'],
                record['balance'],
                record['balance'],
                0.0,
                'USD',
                record['opened_date'],
                None,
                1,
                now,
                now,
                now,
                now
            ))
            inserted += 1
        except sqlite3.IntegrityError:
            # Duplicate account_id, skip
            continue

    conn.commit()
    fin_conn.close()
    print(f"✓ Inserted {inserted} accounts from financial_accounts database")
    return inserted

def populate_beneficiaries(conn):
    """Populate beneficiaries table from beneficiary_registry database"""
    c = conn.cursor()

    # Connect to beneficiary registry database
    ben_conn = sqlite3.connect(BENEFICIARY_DB)
    ben_conn.row_factory = sqlite3.Row
    ben_c = ben_conn.cursor()

    # Get all beneficiary designations with beneficiary details
    ben_c.execute('''
        SELECT bd.*, b.*
        FROM beneficiary_designations bd
        JOIN beneficiaries b ON bd.beneficiary_id = b.beneficiary_id
    ''')
    beneficiary_records = ben_c.fetchall()

    now = datetime.utcnow().isoformat()
    inserted = 0

    for record in beneficiary_records:
        # Verify account exists in our accounts table
        c.execute('SELECT account_id FROM accounts WHERE account_id = ?', (record['account_id'],))
        if not c.fetchone():
            continue

        # Create address JSON
        address_json = json.dumps({
            'street': record['address_street'],
            'city': record['address_city'],
            'state': record['address_state'],
            'zip': record['address_zip']
        })

        # Determine if primary or contingent based on designation_type
        is_primary = 1 if record['designation_type'].upper() == 'PRIMARY' else 0
        is_contingent = 1 if record['designation_type'].upper() == 'CONTINGENT' else 0

        try:
            c.execute('''
                INSERT INTO beneficiaries
                (account_id, beneficiary_type, designation_type, full_name, first_name, middle_name,
                 last_name, suffix, relationship, ssn, tax_id, date_of_birth, address_json,
                 phone, email, percentage, is_primary, is_contingent, share_type,
                 created_date, last_updated, last_synced)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record['account_id'],
                'INDIVIDUAL',
                record['designation_type'],
                record['full_name'],
                record['first_name'],
                None,  # middle_name
                record['last_name'],
                None,  # suffix
                None,  # relationship
                record['ssn'],
                record['ssn'],
                record['dob'],
                address_json,
                record['phone'],
                record['email'],
                record['percentage'],
                is_primary,
                is_contingent,
                'PERCENTAGE',
                now,
                now,
                now
            ))
            inserted += 1
        except sqlite3.IntegrityError as e:
            print(f"  Warning: Could not insert beneficiary {record['full_name']}: {e}")
            continue

    conn.commit()
    ben_conn.close()
    print(f"✓ Inserted {inserted} beneficiaries from beneficiary_registry database")
    return inserted

def populate_death_notifications(conn):
    """Populate death_notifications table from DMF database"""
    c = conn.cursor()

    # Connect to DMF database
    dmf_conn = sqlite3.connect(DMF_DB)
    dmf_conn.row_factory = sqlite3.Row
    dmf_c = dmf_conn.cursor()

    dmf_c.execute('SELECT * FROM deceased_persons')
    deceased_records = dmf_c.fetchall()

    now = datetime.utcnow().isoformat()
    inserted = 0

    for record in deceased_records:
        # Skip records without SSN
        if not record['ssn']:
            continue

        customer_sub = f"CUST_{record['ssn'].replace('-', '')}"

        # Verify customer exists
        c.execute('SELECT customer_id FROM customers WHERE sub = ?', (customer_sub,))
        if not c.fetchone():
            continue

        try:
            c.execute('''
                INSERT INTO death_notifications
                (customer_ssn, customer_sub, full_name, first_name, last_name,
                 date_of_death, date_of_birth, notification_source, notification_date, verified, created_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record['ssn'],
                customer_sub,
                record['full_name'],
                record['first_name'],
                record['last_name'],
                record['dod'],
                record['dob'],
                'DMF',
                now,
                1,
                now
            ))
            inserted += 1
        except sqlite3.IntegrityError:
            # Duplicate SSN, skip
            continue

    conn.commit()
    dmf_conn.close()
    print(f"✓ Inserted {inserted} death notifications from DMF database")
    return inserted

def print_summary(conn):
    """Print database summary statistics"""
    c = conn.cursor()

    print("\n" + "="*60)
    print("DATABASE SUMMARY")
    print("="*60)

    c.execute('SELECT COUNT(*) FROM customers')
    print(f"Customers (Deceased Account Holders): {c.fetchone()[0]}")

    c.execute('SELECT COUNT(*) FROM accounts')
    print(f"Accounts: {c.fetchone()[0]}")

    c.execute('SELECT COUNT(*) FROM beneficiaries')
    print(f"Beneficiaries: {c.fetchone()[0]}")

    c.execute('SELECT COUNT(*) FROM death_notifications')
    print(f"Death Notifications: {c.fetchone()[0]}")

    print("="*60)

    # Sample data
    print("\nSAMPLE CUSTOMER (first record):")
    c.execute('SELECT * FROM customers LIMIT 1')
    customer = c.fetchone()
    if customer:
        print(f"  Customer ID: {customer[0]}")
        print(f"  Name: {customer[4]}")
        print(f"  SSN: {customer[11]}")
        print(f"  DOB: {customer[9]}")

    print("\nSAMPLE ACCOUNT (first record):")
    c.execute('SELECT * FROM accounts LIMIT 1')
    account = c.fetchone()
    if account:
        print(f"  Account ID: {account[0]}")
        print(f"  Account Number: {account[3]}")
        print(f"  Type: {account[4]}")
        print(f"  Balance: ${account[8]:,.2f}")

    print("\nSAMPLE BENEFICIARY (first record):")
    c.execute('SELECT * FROM beneficiaries LIMIT 1')
    beneficiary = c.fetchone()
    if beneficiary:
        print(f"  Beneficiary ID: {beneficiary[0]}")
        print(f"  Name: {beneficiary[4]}")
        print(f"  SSN: {beneficiary[10]}")
        print(f"  Percentage: {beneficiary[16]}%")

    print("="*60 + "\n")

def main():
    """Main execution"""
    print("\n" + "="*60)
    print("BUILDING JACK HENRY MOCK DATABASE")
    print("="*60 + "\n")

    # Create new database
    conn = sqlite3.connect(OUTPUT_DB)

    # Create schema
    create_jackhenry_schema(conn)

    # Populate tables
    populate_customers(conn)
    populate_accounts(conn)
    populate_beneficiaries(conn)
    populate_death_notifications(conn)

    # Print summary
    print_summary(conn)

    conn.close()

    print(f"✓ Jack Henry mock database created: {OUTPUT_DB}")
    print("\nDatabase is ready for integration with CRM platform!\n")

if __name__ == '__main__':
    main()
