import sqlite3
import json
from datetime import datetime, timedelta

# Account type workflow definitions
ACCOUNT_WORKFLOWS = {
    'IRA': {
        'name': 'IRA Beneficiary Transfer',
        'stages': [
            'Document Review',
            'Death Cert Verification',
            'Beneficiary Designation Check',
            'Tax Withholding Setup',
            'Payout Processing'
        ],
        'requirements': [
            'Death certificate (blockchain or certified copy)',
            'Government-issued ID',
            'IRA beneficiary designation form',
            'W-9 tax form',
            'Distribution election form'
        ],
        'compliance_checks': [
            'Verify beneficiary matches IRA designation',
            'Check SECURE Act 2.0 requirements',
            'Confirm distribution method (lump sum vs. inherited IRA)',
            'Validate tax withholding elections'
        ],
        'avg_processing_days': 3
    },
    '401K': {
        'name': '401(k) Beneficiary Claim',
        'stages': [
            'Document Review',
            'Death Cert Verification',
            'Spousal Consent Check',
            'Plan Administrator Review',
            'Payout Processing'
        ],
        'requirements': [
            'Death certificate',
            'Government-issued ID',
            '401(k) beneficiary claim form',
            'Spousal consent (if non-spouse beneficiary)',
            'Plan distribution form'
        ],
        'compliance_checks': [
            'Verify beneficiary vs. spousal rights',
            'Check plan document requirements',
            'Confirm vesting status',
            'Review loan balances'
        ],
        'avg_processing_days': 5
    },
    'TOD': {
        'name': 'Transfer on Death Account',
        'stages': [
            'Document Review',
            'Death Cert Verification',
            'Account Verification',
            'Final Approval',
            'Transfer Processing'
        ],
        'requirements': [
            'Death certificate',
            'Government-issued ID',
            'TOD registration form',
            'Affidavit of domicile'
        ],
        'compliance_checks': [
            'Verify TOD designation on record',
            'Check for account liens',
            'Confirm no conflicting claims',
            'State probate requirements'
        ],
        'avg_processing_days': 2
    },
    'POD': {
        'name': 'Payable on Death Account',
        'stages': [
            'Document Review',
            'Death Cert Verification',
            'POD Verification',
            'Final Approval',
            'Payout Processing'
        ],
        'requirements': [
            'Death certificate',
            'Government-issued ID',
            'POD claim form',
            'Account closure form'
        ],
        'compliance_checks': [
            'Verify POD designation matches',
            'Check for joint account holders',
            'Confirm no legal holds',
            'State banking regulations'
        ],
        'avg_processing_days': 1
    },
    'Trust': {
        'name': 'Trust Account Distribution',
        'stages': [
            'Document Review',
            'Death Cert Verification',
            'Trust Document Review',
            'Trustee Authorization',
            'Distribution Processing'
        ],
        'requirements': [
            'Death certificate',
            'Trust agreement',
            'Trustee identification',
            'Trust certification',
            'Distribution authorization letter'
        ],
        'compliance_checks': [
            'Verify trust is valid',
            'Confirm trustee authority',
            'Review distribution provisions',
            'Tax ID verification',
            'Anti-money laundering check'
        ],
        'avg_processing_days': 7
    }
}

def get_priority(account_balance, account_type, age_days):
    """Calculate case priority based on balance, type, and age"""
    # High priority: >$500K OR age > 5 days
    if account_balance > 500000 or age_days > 5:
        return 'high'
    # Medium priority: $100K-$500K OR age 3-5 days
    elif account_balance > 100000 or age_days > 3:
        return 'medium'
    # Low priority: <$100K AND age < 3 days
    else:
        return 'low'

def setup_database():
    """Creates database schema with workflow support"""

    conn = sqlite3.connect('benebridge.db')
    cursor = conn.cursor()

    # Drop existing tables
    cursor.execute('DROP TABLE IF EXISTS workflow_tasks')
    cursor.execute('DROP TABLE IF EXISTS activity_log')
    cursor.execute('DROP TABLE IF EXISTS documents')
    cursor.execute('DROP TABLE IF EXISTS cases')
    cursor.execute('DROP TABLE IF EXISTS users')

    # Create users table
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

    # Create cases table with workflow fields
    cursor.execute('''
    CREATE TABLE cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_number TEXT UNIQUE NOT NULL,
        deceased_name TEXT NOT NULL,
        deceased_ssn TEXT,
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
        workflow_stage INTEGER DEFAULT 1,
        priority TEXT CHECK(priority IN ('high', 'medium', 'low')) DEFAULT 'medium',
        status TEXT CHECK(status IN ('pending', 'under_review', 'approved', 'paid', 'rejected')) DEFAULT 'pending',
        submission_date TIMESTAMP NOT NULL,
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
        document_type TEXT NOT NULL,
        filename TEXT NOT NULL,
        file_path TEXT NOT NULL,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (case_id) REFERENCES cases (id)
    )
    ''')

    # Create workflow tasks table
    cursor.execute('''
    CREATE TABLE workflow_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id INTEGER NOT NULL,
        task_name TEXT NOT NULL,
        task_description TEXT,
        stage INTEGER NOT NULL,
        completed BOOLEAN DEFAULT 0,
        completed_by INTEGER,
        completed_at TIMESTAMP,
        due_date DATE,
        FOREIGN KEY (case_id) REFERENCES cases (id),
        FOREIGN KEY (completed_by) REFERENCES users (id)
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

    print("✅ Database schema created with workflow support")

    # Seed users
    cursor.execute('''
    INSERT INTO users (email, password_hash, full_name, role)
    VALUES (?, ?, ?, ?)
    ''', ('admin@communitynationalbank.com', 'demo123', 'Admin User', 'admin'))

    print("✅ Demo user created: admin@communitynationalbank.com / demo123")

    # Load and seed synthetic case
    with open('synthetic_case.json', 'r') as f:
        case_data = json.load(f)

    submission_date = datetime.now() - timedelta(days=2)
    priority = get_priority(case_data['account_balance'], case_data['account_type'], 2)

    cursor.execute('''
    INSERT INTO cases (
        case_number, deceased_name, deceased_ssn, date_of_death,
        beneficiary_name, beneficiary_ssn, beneficiary_address,
        beneficiary_phone, beneficiary_email,
        account_number, account_type, account_balance, financial_institution,
        death_cert_type, blockchain_hash, death_certificate_number,
        workflow_stage, priority, status, submission_date
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        1,  # workflow_stage
        priority,
        'pending',
        submission_date
    ))

    case_id = cursor.lastrowid

    # Add documents
    for doc_type, filename in case_data['documents'].items():
        cursor.execute('''
        INSERT INTO documents (case_id, document_type, filename, file_path)
        VALUES (?, ?, ?, ?)
        ''', (case_id, doc_type, filename, filename))

    # Create workflow tasks for this case based on account type
    account_type = case_data['account_type']
    workflow = ACCOUNT_WORKFLOWS.get(account_type, ACCOUNT_WORKFLOWS['IRA'])

    for stage_num, stage_name in enumerate(workflow['stages'], 1):
        # Create task for each workflow stage
        cursor.execute('''
        INSERT INTO workflow_tasks (case_id, task_name, stage, due_date)
        VALUES (?, ?, ?, ?)
        ''', (
            case_id,
            stage_name,
            stage_num,
            datetime.now() + timedelta(days=stage_num)
        ))

    # Add activity log
    cursor.execute('''
    INSERT INTO activity_log (case_id, action, details)
    VALUES (?, ?, ?)
    ''', (case_id, 'Case Submitted', f'Case {case_data["case_number"]} submitted - {account_type} account'))

    # Create additional sample cases for demo
    sample_cases = [
        {
            'case_number': 'SDC-2026-002',
            'deceased_name': 'John Williams',
            'account_type': '401K',
            'account_balance': 385000,
            'beneficiary_name': 'Sarah Williams',
            'age_days': 1,
            'workflow_stage': 3,
            'status': 'under_review'
        },
        {
            'case_number': 'SDC-2026-003',
            'deceased_name': 'Linda Martinez',
            'account_type': 'TOD',
            'account_balance': 50000,
            'beneficiary_name': 'Carlos Martinez',
            'age_days': 4,
            'workflow_stage': 2,
            'status': 'pending'
        },
        {
            'case_number': 'SDC-2026-004',
            'deceased_name': 'Robert Chen',
            'account_type': 'Trust',
            'account_balance': 1200000,
            'beneficiary_name': 'Chen Family Trust',
            'age_days': 6,
            'workflow_stage': 2,
            'status': 'under_review'
        }
    ]

    for sample in sample_cases:
        submission_date = datetime.now() - timedelta(days=sample['age_days'])
        priority = get_priority(sample['account_balance'], sample['account_type'], sample['age_days'])

        cursor.execute('''
        INSERT INTO cases (
            case_number, deceased_name, date_of_death,
            beneficiary_name, beneficiary_address,
            account_number, account_type, account_balance, financial_institution,
            death_cert_type, death_certificate_number,
            workflow_stage, priority, status, submission_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            sample['case_number'],
            sample['deceased_name'],
            '2026-01-15',
            sample['beneficiary_name'],
            '123 Main St, Anytown, CA',
            f"{sample['account_type']}-2024-{sample['case_number'][-3:]}",
            sample['account_type'],
            sample['account_balance'],
            'Community National Bank',
            'blockchain',
            f"2026-CA-{sample['case_number'][-3:]}",
            sample['workflow_stage'],
            priority,
            sample['status'],
            submission_date
        ))

        sample_case_id = cursor.lastrowid

        # Create workflow tasks
        workflow = ACCOUNT_WORKFLOWS.get(sample['account_type'], ACCOUNT_WORKFLOWS['IRA'])
        for stage_num, stage_name in enumerate(workflow['stages'], 1):
            completed = stage_num < sample['workflow_stage']
            cursor.execute('''
            INSERT INTO workflow_tasks (case_id, task_name, stage, completed, due_date)
            VALUES (?, ?, ?, ?, ?)
            ''', (
                sample_case_id,
                stage_name,
                stage_num,
                completed,
                datetime.now() + timedelta(days=stage_num)
            ))

    conn.commit()
    conn.close()

    print(f"✅ Created {len(sample_cases) + 1} sample cases with workflows")
    print("\n🎉 CRM database setup complete!")
    print("\nAccount Type Workflows Configured:")
    for acc_type, workflow in ACCOUNT_WORKFLOWS.items():
        print(f"  • {acc_type}: {workflow['name']} ({len(workflow['stages'])} stages)")

if __name__ == '__main__':
    setup_database()
