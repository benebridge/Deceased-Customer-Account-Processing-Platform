import sqlite3
import json
from datetime import datetime, timedelta

# Smart workflow tasks with context
SMART_WORKFLOWS = {
    'IRA': [
        {
            'stage': 1,
            'task_name': 'Review Death Certificate',
            'task_description': 'Verify death certificate is complete and legible',
            'requires_documents': ['death_certificate'],
            'requires_data': ['deceased_name', 'date_of_death'],
            'verification_checks': ['Document quality check', 'Official seal present', 'State issued']
        },
        {
            'stage': 1,
            'task_name': 'Review Beneficiary ID',
            'task_description': 'Verify government-issued photo ID matches beneficiary name',
            'requires_documents': ['id_front', 'id_back'],
            'requires_data': ['beneficiary_name'],
            'verification_checks': ['ID not expired', 'Photo clear', 'All corners visible', 'Name matches']
        },
        {
            'stage': 1,
            'task_name': 'Review IRA Beneficiary Form',
            'task_description': 'Verify beneficiary claim form is complete and signed',
            'requires_documents': ['beneficiary_form'],
            'requires_data': ['account_number', 'beneficiary_name'],
            'verification_checks': ['Form signed', 'All fields complete', 'Account number matches']
        },
        {
            'stage': 2,
            'task_name': 'Verify Death Certificate Authenticity',
            'task_description': 'Run blockchain or document quality verification',
            'requires_documents': ['death_certificate'],
            'requires_data': ['death_cert_type', 'blockchain_hash'],
            'verification_checks': ['Blockchain hash verified' if True else 'Document quality API score > 85', 'Certificate number valid']
        },
        {
            'stage': 2,
            'task_name': 'Verify Beneficiary Identity',
            'task_description': 'Run ID verification through Onfido/Jumio',
            'requires_documents': ['id_front', 'id_back'],
            'requires_data': ['beneficiary_name', 'beneficiary_address'],
            'verification_checks': ['ID verification API passed', 'Liveness check (if applicable)']
        },
        {
            'stage': 3,
            'task_name': 'Verify IRA Beneficiary Designation',
            'task_description': 'Check beneficiary matches IRA account records',
            'requires_documents': ['beneficiary_form'],
            'requires_data': ['account_number', 'beneficiary_name', 'deceased_name'],
            'verification_checks': ['Beneficiary on file matches', 'No contingent beneficiaries', 'POD designation valid']
        },
        {
            'stage': 3,
            'task_name': 'Check SECURE Act 2.0 Requirements',
            'task_description': 'Verify distribution method complies with SECURE Act',
            'requires_documents': ['beneficiary_form'],
            'requires_data': ['date_of_death', 'account_type'],
            'verification_checks': ['Death after 2019', 'Non-spouse beneficiary rules', '10-year distribution period']
        },
        {
            'stage': 4,
            'task_name': 'Setup Tax Withholding',
            'task_description': 'Verify W-9 form and tax election',
            'requires_documents': ['beneficiary_form'],
            'requires_data': ['beneficiary_ssn', 'beneficiary_address'],
            'verification_checks': ['W-9 form present', 'SSN verified', 'Withholding election made']
        },
        {
            'stage': 4,
            'task_name': 'Confirm Distribution Method',
            'task_description': 'Verify beneficiary distribution election',
            'requires_documents': ['beneficiary_form'],
            'requires_data': ['account_balance'],
            'verification_checks': ['Lump sum or inherited IRA', 'Distribution form complete']
        },
        {
            'stage': 5,
            'task_name': 'Calculate Distribution Amount',
            'task_description': 'Calculate final payout amount after taxes',
            'requires_documents': [],
            'requires_data': ['account_balance'],
            'verification_checks': ['Balance verified', 'Tax withholding calculated', 'Fees deducted']
        },
        {
            'stage': 5,
            'task_name': 'Process Payout',
            'task_description': 'Initiate wire transfer or check',
            'requires_documents': ['beneficiary_form'],
            'requires_data': ['beneficiary_address', 'account_number'],
            'verification_checks': ['Payment method confirmed', 'Routing info verified']
        }
    ],
    '401K': [
        {
            'stage': 1,
            'task_name': 'Review Death Certificate',
            'task_description': 'Verify death certificate is complete and legible',
            'requires_documents': ['death_certificate'],
            'requires_data': ['deceased_name', 'date_of_death'],
            'verification_checks': ['Document quality check', 'Official seal present']
        },
        {
            'stage': 1,
            'task_name': 'Review Beneficiary ID',
            'task_description': 'Verify government-issued photo ID',
            'requires_documents': ['id_front', 'id_back'],
            'requires_data': ['beneficiary_name'],
            'verification_checks': ['ID not expired', 'Photo clear']
        },
        {
            'stage': 1,
            'task_name': 'Review 401(k) Claim Form',
            'task_description': 'Verify beneficiary claim form is complete',
            'requires_documents': ['beneficiary_form'],
            'requires_data': ['account_number'],
            'verification_checks': ['Form signed', 'All fields complete']
        },
        {
            'stage': 2,
            'task_name': 'Verify Death Certificate',
            'task_description': 'Run blockchain or document verification',
            'requires_documents': ['death_certificate'],
            'requires_data': ['death_cert_type'],
            'verification_checks': ['Certificate verified', 'Number valid']
        },
        {
            'stage': 2,
            'task_name': 'Verify Beneficiary Identity',
            'task_description': 'Run ID verification',
            'requires_documents': ['id_front', 'id_back'],
            'requires_data': ['beneficiary_name'],
            'verification_checks': ['ID verification passed']
        },
        {
            'stage': 3,
            'task_name': 'Check Spousal Rights',
            'task_description': 'Verify spousal consent if non-spouse beneficiary',
            'requires_documents': ['beneficiary_form'],
            'requires_data': ['beneficiary_name', 'deceased_name'],
            'verification_checks': ['Spouse vs non-spouse', 'Spousal waiver if needed', 'ERISA compliance']
        },
        {
            'stage': 3,
            'task_name': 'Verify Beneficiary Designation',
            'task_description': 'Check beneficiary matches 401(k) plan records',
            'requires_documents': ['beneficiary_form'],
            'requires_data': ['account_number', 'beneficiary_name'],
            'verification_checks': ['Beneficiary on file', 'Plan document compliance']
        },
        {
            'stage': 4,
            'task_name': 'Plan Administrator Review',
            'task_description': 'Submit to plan administrator for approval',
            'requires_documents': ['beneficiary_form', 'death_certificate'],
            'requires_data': ['account_number'],
            'verification_checks': ['Plan admin notified', 'Vesting confirmed', 'Outstanding loans checked']
        },
        {
            'stage': 5,
            'task_name': 'Process Distribution',
            'task_description': 'Initiate payout per plan rules',
            'requires_documents': ['beneficiary_form'],
            'requires_data': ['account_balance'],
            'verification_checks': ['Distribution method confirmed', 'Tax withholding setup']
        }
    ],
    # Simplified for other types
    'TOD': [
        {'stage': 1, 'task_name': 'Review Death Certificate', 'task_description': 'Verify death certificate', 'requires_documents': ['death_certificate'], 'requires_data': ['deceased_name'], 'verification_checks': ['Certificate valid']},
        {'stage': 1, 'task_name': 'Review Beneficiary ID', 'task_description': 'Verify ID', 'requires_documents': ['id_front', 'id_back'], 'requires_data': ['beneficiary_name'], 'verification_checks': ['ID valid']},
        {'stage': 2, 'task_name': 'Verify Death Certificate', 'task_description': 'Run verification', 'requires_documents': ['death_certificate'], 'requires_data': ['death_cert_type'], 'verification_checks': ['Verified']},
        {'stage': 3, 'task_name': 'Verify TOD Designation', 'task_description': 'Check TOD registration', 'requires_documents': ['beneficiary_form'], 'requires_data': ['account_number'], 'verification_checks': ['TOD on file']},
        {'stage': 4, 'task_name': 'Final Approval', 'task_description': 'Approve transfer', 'requires_documents': [], 'requires_data': [], 'verification_checks': ['No liens', 'No claims']},
        {'stage': 5, 'task_name': 'Process Transfer', 'task_description': 'Transfer account', 'requires_documents': [], 'requires_data': ['account_number'], 'verification_checks': ['Transfer complete']}
    ],
    'POD': [
        {'stage': 1, 'task_name': 'Review Documents', 'task_description': 'Review all documents', 'requires_documents': ['death_certificate', 'id_front'], 'requires_data': [], 'verification_checks': ['Complete']},
        {'stage': 2, 'task_name': 'Verify Death Certificate', 'task_description': 'Verify certificate', 'requires_documents': ['death_certificate'], 'requires_data': [], 'verification_checks': ['Valid']},
        {'stage': 3, 'task_name': 'Verify POD Designation', 'task_description': 'Check POD on file', 'requires_documents': [], 'requires_data': ['account_number'], 'verification_checks': ['POD matches']},
        {'stage': 4, 'task_name': 'Final Approval', 'task_description': 'Approve payout', 'requires_documents': [], 'requires_data': [], 'verification_checks': ['Approved']},
        {'stage': 5, 'task_name': 'Process Payout', 'task_description': 'Issue payment', 'requires_documents': [], 'requires_data': ['account_balance'], 'verification_checks': ['Paid']}
    ],
    'Trust': [
        {'stage': 1, 'task_name': 'Review Death Certificate', 'task_description': 'Verify death certificate', 'requires_documents': ['death_certificate'], 'requires_data': [], 'verification_checks': ['Valid']},
        {'stage': 2, 'task_name': 'Verify Death Certificate', 'task_description': 'Run verification', 'requires_documents': ['death_certificate'], 'requires_data': [], 'verification_checks': ['Verified']},
        {'stage': 3, 'task_name': 'Review Trust Documents', 'task_description': 'Verify trust validity', 'requires_documents': ['beneficiary_form'], 'requires_data': [], 'verification_checks': ['Trust valid', 'Distribution provisions']},
        {'stage': 4, 'task_name': 'Verify Trustee Authority', 'task_description': 'Confirm trustee authorization', 'requires_documents': ['id_front'], 'requires_data': [], 'verification_checks': ['Trustee authorized', 'Tax ID verified']},
        {'stage': 5, 'task_name': 'Process Distribution', 'task_description': 'Distribute to trust', 'requires_documents': [], 'requires_data': ['account_balance'], 'verification_checks': ['AML check', 'Distribution complete']}
    ]
}

def setup_smart_workflow_db():
    """Setup database with smart context-aware workflow tasks"""
    conn = sqlite3.connect('benebridge.db')
    conn.row_factory = sqlite3.Row  # Enable dictionary access
    cursor = conn.cursor()

    # Drop and recreate workflow_tasks table with new fields
    cursor.execute('DROP TABLE IF EXISTS workflow_tasks')
    cursor.execute('''
    CREATE TABLE workflow_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id INTEGER NOT NULL,
        task_name TEXT NOT NULL,
        task_description TEXT,
        stage INTEGER NOT NULL,
        requires_documents TEXT,
        requires_data TEXT,
        verification_checks TEXT,
        completed BOOLEAN DEFAULT 0,
        completed_by INTEGER,
        completed_at TIMESTAMP,
        due_date DATE,
        FOREIGN KEY (case_id) REFERENCES cases (id),
        FOREIGN KEY (completed_by) REFERENCES users (id)
    )
    ''')

    # Get all cases
    cases = cursor.execute('SELECT * FROM cases').fetchall()

    for case in cases:
        account_type = case['account_type']
        workflow_tasks = SMART_WORKFLOWS.get(account_type, SMART_WORKFLOWS['IRA'])

        # Delete old tasks for this case
        cursor.execute('DELETE FROM workflow_tasks WHERE case_id = ?', (case['id'],))

        # Insert smart workflow tasks
        for task in workflow_tasks:
            cursor.execute('''
            INSERT INTO workflow_tasks (
                case_id, task_name, task_description, stage,
                requires_documents, requires_data, verification_checks, due_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                case['id'],
                task['task_name'],
                task['task_description'],
                task['stage'],
                json.dumps(task.get('requires_documents', [])),
                json.dumps(task.get('requires_data', [])),
                json.dumps(task.get('verification_checks', [])),
                datetime.now() + timedelta(days=task['stage'])
            ))

    conn.commit()
    conn.close()

    print("✅ Smart workflow tasks created for all cases")
    print(f"   IRA: {len(SMART_WORKFLOWS['IRA'])} context-aware tasks")
    print(f"   401K: {len(SMART_WORKFLOWS['401K'])} context-aware tasks")

if __name__ == '__main__':
    setup_smart_workflow_db()
