import sqlite3
import json
from datetime import datetime

def setup_database():
    """Creates database schema and seeds with synthetic data"""

    # Connect to SQLite database (creates file if doesn't exist)
    conn = sqlite3.connect('benebridge.db')
    cursor = conn.cursor()

    # Drop existing tables (fresh start)
    cursor.execute('DROP TABLE IF EXISTS activity_log')
    cursor.execute('DROP TABLE IF EXISTS documents')
    cursor.execute('DROP TABLE IF EXISTS cases')
    cursor.execute('DROP TABLE IF EXISTS users')

    # Create users table (institution employees)
    cursor.execute('''
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT CHECK(role IN ('admin', 'compliance', 'operations', 'manager')) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Create cases table
    cursor.execute('''
    CREATE TABLE cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_number TEXT UNIQUE NOT NULL,
        deceased_name TEXT NOT NULL,
        deceased_ssn TEXT,
        deceased_sex TEXT CHECK(deceased_sex IN ('M', 'F')),
        date_of_death DATE NOT NULL,
        beneficiary_name TEXT NOT NULL,
        beneficiary_ssn TEXT,
        beneficiary_address TEXT NOT NULL,
        beneficiary_phone TEXT,
        beneficiary_email TEXT,
        account_number TEXT NOT NULL,
        account_type TEXT NOT NULL,
        account_balance REAL NOT NULL,
        financial_institution TEXT NOT NULL,
        death_cert_type TEXT CHECK(death_cert_type IN ('blockchain', 'physical')) NOT NULL,
        blockchain_hash TEXT,
        death_certificate_number TEXT,
        death_cert_verification_score INTEGER DEFAULT 0,
        id_verified BOOLEAN DEFAULT 0,
        beneficiary_info_verified BOOLEAN DEFAULT 0,
        status TEXT CHECK(status IN ('pending', 'under_review', 'approved', 'paid', 'rejected')) DEFAULT 'pending',
        submission_date TIMESTAMP NOT NULL,
        access_code TEXT,
        workflow_stage INTEGER DEFAULT 1,
        priority TEXT DEFAULT 'medium',
        reviewed_by INTEGER,
        reviewed_at TIMESTAMP,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (reviewed_by) REFERENCES users (id)
    )
    ''')

    # Create documents table
    cursor.execute('''
    CREATE TABLE documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id INTEGER NOT NULL,
        document_type TEXT CHECK(document_type IN ('death_certificate', 'id_front', 'id_back', 'beneficiary_form')) NOT NULL,
        filename TEXT NOT NULL,
        file_path TEXT NOT NULL,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (case_id) REFERENCES cases (id)
    )
    ''')

    # Create activity log table
    cursor.execute('''
    CREATE TABLE activity_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id INTEGER NOT NULL,
        user_id INTEGER,
        action TEXT NOT NULL,
        details TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (case_id) REFERENCES cases (id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')

    print("✅ Database schema created successfully")

    # Seed with demo user (password: demo123)
    # In production, use proper password hashing (werkzeug.security.generate_password_hash)
    cursor.execute('''
    INSERT INTO users (email, password_hash, full_name, role)
    VALUES (?, ?, ?, ?)
    ''', ('admin@communitynationalbank.com', 'demo123', 'Admin User', 'admin'))

    print("✅ Demo user created: admin@communitynationalbank.com / demo123")

    # Load synthetic case data
    with open('synthetic_case.json', 'r') as f:
        case_data = json.load(f)

    # Insert synthetic case
    cursor.execute('''
    INSERT INTO cases (
        case_number, deceased_name, deceased_ssn, date_of_death,
        beneficiary_name, beneficiary_ssn, beneficiary_address,
        beneficiary_phone, beneficiary_email,
        account_number, account_type, account_balance, financial_institution,
        death_cert_type, blockchain_hash, death_certificate_number,
        status, submission_date
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        case_data['case_number'],
        case_data['deceased_name'],
        case_data['deceased_ssn'],
        case_data['date_of_death'],
        case_data['beneficiary_name'],
        case_data['beneficiary_ssn'],
        case_data['beneficiary_address'],
        case_data['beneficiary_phone'],
        case_data['beneficiary_email'],
        case_data['account_number'],
        case_data['account_type'],
        case_data['account_balance'],
        case_data['financial_institution'],
        case_data['death_cert_type'],
        case_data.get('blockchain_hash'),
        case_data['death_certificate_number'],
        case_data['status'],
        case_data['submission_date']
    ))

    case_id = cursor.lastrowid
    print(f"✅ Synthetic case created: {case_data['case_number']}")

    # Insert document records
    for doc_type, filename in case_data['documents'].items():
        cursor.execute('''
        INSERT INTO documents (case_id, document_type, filename, file_path)
        VALUES (?, ?, ?, ?)
        ''', (case_id, doc_type, filename, filename))

    print(f"✅ {len(case_data['documents'])} documents linked to case")

    # Insert initial activity log
    cursor.execute('''
    INSERT INTO activity_log (case_id, action, details)
    VALUES (?, ?, ?)
    ''', (case_id, 'Case Submitted', f'Case {case_data["case_number"]} submitted by beneficiary {case_data["beneficiary_name"]}'))

    # Commit changes and close
    conn.commit()
    conn.close()

    print("\n🎉 Database setup complete! Ready to run POC.")

if __name__ == '__main__':
    setup_database()
