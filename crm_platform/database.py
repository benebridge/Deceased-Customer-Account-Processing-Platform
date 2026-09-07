#!/usr/bin/env python3
"""
BeneBridge CRM - Database Schema
Death Claim Workflow Management System
"""

import sqlite3
from datetime import datetime
import json

DATABASE_PATH = 'crm_workflow.db'

def init_database():
    """Initialize the CRM workflow database"""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()

    # Workflow Cases Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS workflow_cases (
            case_id TEXT PRIMARY KEY,
            created_date TEXT NOT NULL,
            last_updated TEXT NOT NULL,

            -- Death Event Information
            deceased_name TEXT NOT NULL,
            deceased_ssn TEXT,
            date_of_death TEXT,
            notification_source TEXT,
            notification_date TEXT,

            -- Case Status
            workflow_status TEXT NOT NULL,
            priority TEXT DEFAULT 'medium',
            complexity_score INTEGER DEFAULT 0,

            -- Assignment
            assigned_to TEXT,
            assigned_date TEXT,

            -- Account Information (JSON array)
            accounts_json TEXT,

            -- Beneficiary Information
            primary_beneficiary_name TEXT,
            primary_beneficiary_email TEXT,
            primary_beneficiary_phone TEXT,
            primary_beneficiary_address TEXT,

            -- Processing Metadata
            total_claim_amount REAL DEFAULT 0.0,
            estimated_completion_date TEXT,
            sla_deadline TEXT,
            sla_status TEXT DEFAULT 'on_track',

            -- Flags
            requires_probate INTEGER DEFAULT 0,
            fraud_alert INTEGER DEFAULT 0,
            manager_review_required INTEGER DEFAULT 0,

            -- Notes
            latest_note TEXT
        )
    ''')

    # Workflow History/Audit Trail
    c.execute('''
        CREATE TABLE IF NOT EXISTS workflow_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            action TEXT NOT NULL,
            old_status TEXT,
            new_status TEXT,
            performed_by TEXT,
            notes TEXT,
            FOREIGN KEY (case_id) REFERENCES workflow_cases(case_id)
        )
    ''')

    # Tasks Table (Employee action items)
    c.execute('''
        CREATE TABLE IF NOT EXISTS workflow_tasks (
            task_id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            created_date TEXT NOT NULL,
            due_date TEXT,
            task_type TEXT NOT NULL,
            task_description TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            assigned_to TEXT,
            completed_date TEXT,
            completed_by TEXT,
            FOREIGN KEY (case_id) REFERENCES workflow_cases(case_id)
        )
    ''')

    # Documents Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS case_documents (
            doc_id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            uploaded_date TEXT NOT NULL,
            document_type TEXT NOT NULL,
            file_path TEXT,
            verification_status TEXT DEFAULT 'pending',
            verification_results_json TEXT,
            uploaded_by TEXT,
            FOREIGN KEY (case_id) REFERENCES workflow_cases(case_id)
        )
    ''')

    # Communications Log
    c.execute('''
        CREATE TABLE IF NOT EXISTS communication_log (
            comm_id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            sent_date TEXT NOT NULL,
            comm_type TEXT NOT NULL,
            comm_channel TEXT NOT NULL,
            recipient TEXT,
            subject TEXT,
            message_body TEXT,
            template_used TEXT,
            status TEXT DEFAULT 'sent',
            FOREIGN KEY (case_id) REFERENCES workflow_cases(case_id)
        )
    ''')

    # Approvals Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS approvals (
            approval_id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            requested_date TEXT NOT NULL,
            approval_type TEXT NOT NULL,
            amount REAL,
            requested_by TEXT,
            approver_required TEXT,
            approved_by TEXT,
            approved_date TEXT,
            status TEXT DEFAULT 'pending',
            notes TEXT,
            FOREIGN KEY (case_id) REFERENCES workflow_cases(case_id)
        )
    ''')

    # Manual Overrides Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS manual_overrides (
            override_id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            override_date TEXT NOT NULL,
            override_type TEXT NOT NULL,
            original_value TEXT,
            new_value TEXT,
            justification TEXT NOT NULL,
            overridden_by TEXT NOT NULL,
            requires_approval INTEGER DEFAULT 0,
            approved_by TEXT,
            FOREIGN KEY (case_id) REFERENCES workflow_cases(case_id)
        )
    ''')

    # AI Communication Templates
    c.execute('''
        CREATE TABLE IF NOT EXISTS communication_templates (
            template_id TEXT PRIMARY KEY,
            template_name TEXT NOT NULL,
            template_description TEXT,
            account_types TEXT,
            probate_required INTEGER,
            channel TEXT,
            subject_template TEXT,
            body_template TEXT,
            variables_json TEXT
        )
    ''')

    conn.commit()
    conn.close()
    print("Database initialized successfully")

def seed_communication_templates():
    """Seed AI-driven communication templates"""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()

    templates = [
        {
            'template_id': 'POD_SIMPLE',
            'template_name': 'POD/TOD Simple Claim',
            'template_description': 'For simple payable-on-death accounts',
            'account_types': 'POD,TOD',
            'probate_required': 0,
            'channel': 'email',
            'subject_template': 'Important: Beneficiary Claim Process for {deceased_name}',
            'body_template': '''Dear {beneficiary_name},

We extend our deepest condolences on the loss of {deceased_name}.

You have been designated as a beneficiary on the following account(s):
{account_list}

This is a {account_type} account, which means funds can be released directly to you without probate once we verify the required documentation.

NEXT STEPS:
1. Complete the attached beneficiary claim form
2. Provide a certified copy of the death certificate
3. Provide a government-issued photo ID

TIMELINE: Typically 5-10 business days after receiving complete documentation

You can submit documents digitally through our secure portal or by mail. We will send you a separate email with the secure upload link.

If you have any questions, please contact our Estate Services team at 1-800-XXX-XXXX.

With sympathy,
Estate Services Department''',
            'variables_json': json.dumps(['deceased_name', 'beneficiary_name', 'account_list', 'account_type'])
        },
        {
            'template_id': 'PROBATE_REQUIRED',
            'template_name': 'Probate Required Notice',
            'template_description': 'For accounts requiring probate',
            'account_types': 'CHECKING,SAVINGS',
            'probate_required': 1,
            'channel': 'mail',
            'subject_template': 'Estate Settlement Requirements for {deceased_name}',
            'body_template': '''Dear {beneficiary_name},

Please accept our sincere condolences regarding the passing of {deceased_name}.

We have identified the following account(s) in the name of the deceased:
{account_list}

IMPORTANT: These accounts require probate court proceedings before funds can be released.

REQUIRED DOCUMENTATION:
1. Certified copy of death certificate
2. Court-issued Letters Testamentary or Letters of Administration
3. Court order authorizing distribution (if applicable)
4. Completed beneficiary claim form
5. Government-issued photo ID

TIMELINE: Estate settlement typically takes 60-180 days depending on your state's probate process.

We recommend consulting with an estate attorney to guide you through the probate process. Once you have obtained the required court documents, please contact our Estate Services team at 1-800-XXX-XXXX to proceed with the claim.

Our thoughts are with you during this difficult time.

Sincerely,
Estate Services Department''',
            'variables_json': json.dumps(['deceased_name', 'beneficiary_name', 'account_list'])
        },
        {
            'template_id': 'IRA_BENEFICIARY',
            'template_name': 'IRA Beneficiary Notice',
            'template_description': 'For retirement account beneficiaries',
            'account_types': 'IRA,401K,ROTH_IRA',
            'probate_required': 0,
            'channel': 'email',
            'subject_template': 'Retirement Account Beneficiary Information - {deceased_name}',
            'body_template': '''Dear {beneficiary_name},

Our condolences on the passing of {deceased_name}.

You have been named as beneficiary on the following retirement account(s):
{account_list}

IMPORTANT TAX CONSIDERATIONS:
Retirement accounts have specific tax implications and distribution requirements. We strongly recommend consulting with a tax advisor before proceeding.

REQUIRED DOCUMENTATION:
1. Certified copy of death certificate
2. Government-issued photo ID
3. Completed IRA beneficiary distribution form
4. IRS Form W-9 (Taxpayer Identification)
5. Distribution election (inherited IRA, lump sum, etc.)

DISTRIBUTION OPTIONS:
- Establish an Inherited IRA (recommended for tax deferral)
- Lump sum distribution (subject to immediate taxation)
- 5-year distribution plan

We will schedule a consultation with our retirement specialists to discuss your options and tax implications.

Please contact us at 1-800-XXX-XXXX to schedule your consultation.

Sincerely,
Retirement Services Department''',
            'variables_json': json.dumps(['deceased_name', 'beneficiary_name', 'account_list'])
        },
        {
            'template_id': 'MULTIPLE_BENEFICIARIES',
            'template_name': 'Multiple Beneficiaries Coordination',
            'template_description': 'When multiple beneficiaries exist',
            'account_types': 'ALL',
            'probate_required': 0,
            'channel': 'email',
            'subject_template': 'Co-Beneficiary Claim Process for {deceased_name}',
            'body_template': '''Dear {beneficiary_name},

Please accept our condolences regarding {deceased_name}.

You have been named as one of {beneficiary_count} beneficiaries on the following account(s):
{account_list}

Your share: {beneficiary_percentage}%

COORDINATION REQUIRED:
All beneficiaries must submit their documentation before we can process distributions. We will keep you informed of the overall claim status.

REQUIRED FROM YOU:
1. Certified copy of death certificate
2. Government-issued photo ID
3. Completed beneficiary claim form

We are coordinating with the other beneficiaries. You will receive updates as documentation is collected from all parties.

Thank you for your patience during this process.

Sincerely,
Estate Services Department''',
            'variables_json': json.dumps(['deceased_name', 'beneficiary_name', 'beneficiary_count', 'account_list', 'beneficiary_percentage'])
        }
    ]

    for template in templates:
        c.execute('''
            INSERT OR REPLACE INTO communication_templates
            (template_id, template_name, template_description, account_types, probate_required,
             channel, subject_template, body_template, variables_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            template['template_id'],
            template['template_name'],
            template['template_description'],
            template['account_types'],
            template['probate_required'],
            template['channel'],
            template['subject_template'],
            template['body_template'],
            template['variables_json']
        ))

    conn.commit()
    conn.close()
    print(f"Seeded {len(templates)} communication templates")

if __name__ == '__main__':
    init_database()
    seed_communication_templates()
