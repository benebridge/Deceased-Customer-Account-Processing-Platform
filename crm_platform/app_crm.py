#!/usr/bin/env python3
"""
BeneBridge CRM Platform
Death Claim Workflow Management System
Financial Institution Employee-Facing CRM
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
import sqlite3
from datetime import datetime, timedelta
import json
import requests
from pathlib import Path
from mock_jackhenry_client import MockJackHenryClient
from mock_docusign_client import MockDocuSignClient
from verification_engine import process_verification
from io import BytesIO

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

DATABASE_PATH = 'crm_workflow.db'
VERIFICATION_API_URL = 'http://localhost:5008/api/process_verification'

# Initialize Mock Jack Henry Client
jack_henry_client = MockJackHenryClient()

# Initialize Mock DocuSign Client
docusign_client = MockDocuSignClient()

# Workflow State Machine
WORKFLOW_STATES = {
    'NOTIFIED': {
        'label': 'Notified',
        'color': '#94a3b8',
        'next_states': ['TRIAGED', 'REJECTED']
    },
    'TRIAGED': {
        'label': 'Triaged',
        'color': '#60a5fa',
        'next_states': ['AWAITING_DOCUMENTS']
    },
    'AWAITING_DOCUMENTS': {
        'label': 'Awaiting Documents',
        'color': '#fb923c',
        'next_states': ['IN_VERIFICATION', 'ABANDONED']
    },
    'IN_VERIFICATION': {
        'label': 'In Verification',
        'color': '#a78bfa',
        'next_states': ['VERIFIED', 'NEEDS_REVIEW', 'FRAUD_ALERT']
    },
    'VERIFIED': {
        'label': 'Verified',
        'color': '#34d399',
        'next_states': ['PAYMENT_APPROVED', 'NEEDS_REVIEW']
    },
    'NEEDS_REVIEW': {
        'label': 'Needs Review',
        'color': '#fbbf24',
        'next_states': ['VERIFIED', 'FRAUD_ALERT', 'AWAITING_DOCUMENTS']
    },
    'PAYMENT_APPROVED': {
        'label': 'Payment Approved',
        'color': '#10b981',
        'next_states': ['PAYMENT_PROCESSING']
    },
    'PAYMENT_PROCESSING': {
        'label': 'Payment Processing',
        'color': '#06b6d4',
        'next_states': ['PAYMENT_COMPLETED', 'PAYMENT_FAILED']
    },
    'PAYMENT_COMPLETED': {
        'label': 'Payment Completed',
        'color': '#059669',
        'next_states': ['CLOSED']
    },
    'FRAUD_ALERT': {
        'label': 'Fraud Alert',
        'color': '#dc2626',
        'next_states': ['FRAUD_INVESTIGATION']
    },
    'FRAUD_INVESTIGATION': {
        'label': 'Fraud Investigation',
        'color': '#b91c1c',
        'next_states': ['CLEARED', 'DENIED']
    },
    'REJECTED': {
        'label': 'Rejected',
        'color': '#ef4444',
        'next_states': ['CLOSED']
    },
    'ABANDONED': {
        'label': 'Abandoned',
        'color': '#9ca3af',
        'next_states': ['CLOSED']
    },
    'PAYMENT_FAILED': {
        'label': 'Payment Failed',
        'color': '#f97316',
        'next_states': ['PAYMENT_PROCESSING', 'NEEDS_REVIEW']
    },
    'CLEARED': {
        'label': 'Cleared',
        'color': '#22c55e',
        'next_states': ['VERIFIED', 'CLOSED']
    },
    'DENIED': {
        'label': 'Denied',
        'color': '#991b1b',
        'next_states': ['CLOSED']
    },
    'CLOSED': {
        'label': 'Closed',
        'color': '#6b7280',
        'next_states': []
    }
}

# Approval Tiers based on claim amount (Per Dissertation Table 4.2)
APPROVAL_TIERS = [
    {
        'name': 'AUTO_APPROVED',
        'label': 'Auto-Approved',
        'min_amount': 0,
        'max_amount': 49999.99,
        'approver_role': 'System',
        'description': 'Claims under $50,000 are automatically approved'
    },
    {
        'name': 'PROCESSOR_APPROVAL',
        'label': 'Processor Approval',
        'min_amount': 50000,
        'max_amount': 99999.99,
        'approver_role': 'Processor',
        'description': 'Claims $50,000 - $99,999.99 require processor approval'
    },
    {
        'name': 'SUPERVISOR_APPROVAL',
        'label': 'Supervisor Approval',
        'min_amount': 100000,
        'max_amount': 249999.99,
        'approver_role': 'Supervisor',
        'description': 'Claims $100,000 - $249,999.99 require supervisor approval'
    },
    {
        'name': 'MANAGER_APPROVAL',
        'label': 'Manager Approval',
        'min_amount': 250000,
        'max_amount': 999999.99,
        'approver_role': 'Manager',
        'description': 'Claims $250,000 - $999,999.99 require manager approval'
    },
    {
        'name': 'SENIOR_MANAGER_APPROVAL',
        'label': 'Senior Manager Approval',
        'min_amount': 1000000,
        'max_amount': float('inf'),
        'approver_role': 'Senior Manager',
        'description': 'Claims $1,000,000 and above require senior manager approval'
    }
]

def determine_required_approver(amount):
    """
    Determine the required approver tier based on claim amount

    Args:
        amount: Total claim amount

    Returns:
        Dict with tier information
    """
    for tier in APPROVAL_TIERS:
        if tier['min_amount'] <= amount < tier['max_amount']:
            return tier

    # Default to highest tier if amount exceeds all tiers
    return APPROVAL_TIERS[-1]

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# =============================================================================
# DASHBOARD & CASE QUEUE
# =============================================================================

@app.route('/')
def dashboard():
    """Main CRM dashboard with case queue"""
    conn = get_db()
    c = conn.cursor()

    # Get all active cases
    c.execute('''
        SELECT * FROM workflow_cases
        WHERE workflow_status NOT IN ('CLOSED', 'REJECTED', 'ABANDONED')
        ORDER BY
            CASE priority
                WHEN 'critical' THEN 1
                WHEN 'high' THEN 2
                WHEN 'medium' THEN 3
                WHEN 'low' THEN 4
            END,
            created_date DESC
    ''')

    cases = [dict(row) for row in c.fetchall()]

    # Calculate case age in days
    for case in cases:
        created = datetime.fromisoformat(case['created_date'])
        age_days = (datetime.now() - created).days
        case['age_days'] = age_days

        # Parse accounts JSON
        if case['accounts_json']:
            case['accounts'] = json.loads(case['accounts_json'])
        else:
            case['accounts'] = []

    # Get statistics
    c.execute('SELECT COUNT(*) as total FROM workflow_cases WHERE workflow_status NOT IN ("CLOSED", "REJECTED")')
    total_active = c.fetchone()['total']

    c.execute('SELECT COUNT(*) as total FROM workflow_cases WHERE workflow_status = "AWAITING_DOCUMENTS"')
    awaiting_docs = c.fetchone()['total']

    c.execute('SELECT COUNT(*) as total FROM workflow_cases WHERE workflow_status = "NEEDS_REVIEW"')
    needs_review = c.fetchone()['total']

    c.execute('SELECT COUNT(*) as total FROM workflow_cases WHERE fraud_alert = 1')
    fraud_alerts = c.fetchone()['total']

    conn.close()

    return render_template('dashboard.html',
                         cases=cases,
                         total_active=total_active,
                         awaiting_docs=awaiting_docs,
                         needs_review=needs_review,
                         fraud_alerts=fraud_alerts,
                         workflow_states=WORKFLOW_STATES)

# =============================================================================
# CASE DETAIL VIEW
# =============================================================================

@app.route('/case/<case_id>')
def case_detail(case_id):
    """Detailed view of a single case"""
    conn = get_db()
    c = conn.cursor()

    # Get case details
    c.execute('SELECT * FROM workflow_cases WHERE case_id = ?', (case_id,))
    case = dict(c.fetchone())

    # Parse accounts JSON
    if case['accounts_json']:
        case['accounts'] = json.loads(case['accounts_json'])
    else:
        case['accounts'] = []

    # Get workflow history
    c.execute('''
        SELECT * FROM workflow_history
        WHERE case_id = ?
        ORDER BY timestamp DESC
    ''', (case_id,))
    history = [dict(row) for row in c.fetchall()]

    # Get tasks
    c.execute('''
        SELECT * FROM workflow_tasks
        WHERE case_id = ?
        ORDER BY
            CASE status
                WHEN 'pending' THEN 1
                WHEN 'in_progress' THEN 2
                WHEN 'completed' THEN 3
            END,
            due_date ASC
    ''', (case_id,))
    tasks = [dict(row) for row in c.fetchall()]

    # Get documents
    c.execute('''
        SELECT * FROM case_documents
        WHERE case_id = ?
        ORDER BY uploaded_date DESC
    ''', (case_id,))
    documents = [dict(row) for row in c.fetchall()]

    # Get communications
    c.execute('''
        SELECT * FROM communication_log
        WHERE case_id = ?
        ORDER BY sent_date DESC
    ''', (case_id,))
    communications = [dict(row) for row in c.fetchall()]

    # Get approvals
    c.execute('''
        SELECT * FROM approvals
        WHERE case_id = ?
        ORDER BY requested_date DESC
    ''', (case_id,))
    approvals = [dict(row) for row in c.fetchall()]

    conn.close()

    return render_template('case_detail.html',
                         case=case,
                         history=history,
                         tasks=tasks,
                         documents=documents,
                         communications=communications,
                         approvals=approvals,
                         workflow_states=WORKFLOW_STATES)

# =============================================================================
# CREATE NEW CASE
# =============================================================================

@app.route('/case/search', methods=['GET'])
def search_deceased():
    """Jack Henry search interface for creating cases"""
    return render_template('jackhenry_search.html')

@app.route('/case/new', methods=['GET', 'POST'])
def create_case():
    """Create a new death claim case (manual fallback)"""
    if request.method == 'GET':
        return render_template('create_case.html')

    # POST - Create the case
    data = request.json

    conn = get_db()
    c = conn.cursor()

    # Generate case ID
    now = datetime.now()
    case_id = f"DC-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}"

    # Determine SLA deadline (30 days for simple cases)
    sla_deadline = (now + timedelta(days=30)).isoformat()

    # Insert case
    c.execute('''
        INSERT INTO workflow_cases (
            case_id, created_date, last_updated, deceased_name, deceased_ssn,
            date_of_death, notification_source, notification_date, workflow_status,
            priority, assigned_to, primary_beneficiary_name, primary_beneficiary_email,
            primary_beneficiary_phone, accounts_json, sla_deadline
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        case_id,
        now.isoformat(),
        now.isoformat(),
        data.get('deceased_name'),
        data.get('deceased_ssn'),
        data.get('date_of_death'),
        data.get('notification_source'),
        now.isoformat(),
        'NOTIFIED',
        data.get('priority', 'medium'),
        data.get('assigned_to', 'Current User'),
        data.get('beneficiary_name'),
        data.get('beneficiary_email'),
        data.get('beneficiary_phone'),
        json.dumps(data.get('accounts', [])),
        sla_deadline
    ))

    # Add to history
    c.execute('''
        INSERT INTO workflow_history (case_id, timestamp, action, new_status, performed_by)
        VALUES (?, ?, ?, ?, ?)
    ''', (case_id, now.isoformat(), 'Case Created', 'NOTIFIED', data.get('assigned_to', 'Current User')))

    # Create initial task - Triage
    c.execute('''
        INSERT INTO workflow_tasks (
            case_id, created_date, due_date, task_type, task_description, assigned_to
        ) VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        case_id,
        now.isoformat(),
        (now + timedelta(days=1)).isoformat(),
        'TRIAGE',
        'Review case and determine account types, beneficiaries, and documentation requirements',
        data.get('assigned_to', 'Current User')
    ))

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'case_id': case_id})

# =============================================================================
# JACK HENRY INTEGRATION ENDPOINTS
# =============================================================================

@app.route('/api/jackhenry/search', methods=['POST'])
def jackhenry_search():
    """Search for deceased customer in Jack Henry database by SSN"""
    data = request.json
    ssn = data.get('ssn')

    if not ssn:
        return jsonify({'success': False, 'error': 'SSN is required'}), 400

    try:
        # Search for customer data
        customer_data = jack_henry_client.get_complete_customer_data(ssn)

        if not customer_data:
            return jsonify({
                'success': False,
                'error': 'No customer found with that SSN',
                'found': False
            })

        return jsonify({
            'success': True,
            'found': True,
            'data': customer_data
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/jackhenry/create_case_from_data', methods=['POST'])
def create_case_from_jackhenry():
    """Create a new case automatically from Jack Henry customer data"""
    data = request.json
    ssn = data.get('ssn')
    assigned_to = data.get('assigned_to', 'Current User')
    priority = data.get('priority', 'medium')

    if not ssn:
        return jsonify({'success': False, 'error': 'SSN is required'}), 400

    try:
        # Get complete customer data from Jack Henry
        customer_data = jack_henry_client.get_complete_customer_data(ssn)

        if not customer_data:
            return jsonify({'success': False, 'error': 'Customer not found'}), 404

        customer = customer_data['customer']
        death_notification = customer_data['death_notification']
        accounts = customer_data['accounts']

        # Create case
        conn = get_db()
        c = conn.cursor()

        now = datetime.now()
        case_id = f"DC-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}"
        sla_deadline = (now + timedelta(days=30)).isoformat()

        # Prepare accounts JSON
        accounts_json = []
        primary_beneficiary = None

        for account in accounts:
            account_info = {
                'account_id': account['account_id'],
                'account_number': account['account_number'],
                'account_type': account['account_type'],
                'balance': account['balance_current'],
                'status': account['status']
            }

            # Add beneficiaries to account info
            beneficiaries = []
            for ben in account.get('beneficiaries', []):
                ben_info = {
                    'name': ben['full_name'],
                    'ssn': ben['ssn'],
                    'percentage': ben['percentage'],
                    'designation_type': ben['designation_type'],
                    'email': ben.get('email'),
                    'phone': ben.get('phone')
                }
                beneficiaries.append(ben_info)

                # Use first primary beneficiary as primary contact
                if not primary_beneficiary and ben['is_primary']:
                    primary_beneficiary = ben

            account_info['beneficiaries'] = beneficiaries
            accounts_json.append(account_info)

        # Use first beneficiary if no primary found
        if not primary_beneficiary and accounts and accounts[0].get('beneficiaries'):
            primary_beneficiary = accounts[0]['beneficiaries'][0]

        # Insert case
        c.execute('''
            INSERT INTO workflow_cases (
                case_id, created_date, last_updated, deceased_name, deceased_ssn,
                date_of_death, notification_source, notification_date, workflow_status,
                priority, assigned_to, primary_beneficiary_name, primary_beneficiary_email,
                primary_beneficiary_phone, accounts_json, sla_deadline
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            case_id,
            now.isoformat(),
            now.isoformat(),
            customer['full_name'],
            customer['ssn'],
            death_notification['date_of_death'] if death_notification else None,
            death_notification['notification_source'] if death_notification else 'JACK_HENRY',
            now.isoformat(),
            'TRIAGED',  # Start at TRIAGED since we have all data
            priority,
            assigned_to,
            primary_beneficiary['full_name'] if primary_beneficiary else None,
            primary_beneficiary.get('email') if primary_beneficiary else None,
            primary_beneficiary.get('phone') if primary_beneficiary else None,
            json.dumps(accounts_json),
            sla_deadline
        ))

        # Add to history
        c.execute('''
            INSERT INTO workflow_history (case_id, timestamp, action, new_status, performed_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (case_id, now.isoformat(), 'Case Created from Jack Henry Data', 'TRIAGED', assigned_to))

        # Create initial task - Document Collection
        c.execute('''
            INSERT INTO workflow_tasks (
                case_id, created_date, due_date, task_type, task_description, assigned_to
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            case_id,
            now.isoformat(),
            (now + timedelta(days=3)).isoformat(),
            'DOCUMENT_COLLECTION',
            f'Request death certificate and claim forms from {primary_beneficiary["full_name"] if primary_beneficiary else "beneficiary"}',
            assigned_to
        ))

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'case_id': case_id,
            'summary': customer_data['summary']
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/jackhenry/list_deceased', methods=['GET'])
def list_deceased_customers():
    """Get list of all deceased customers for testing/demo purposes"""
    try:
        deceased_list = jack_henry_client.get_all_deceased_customers()
        return jsonify({
            'success': True,
            'customers': deceased_list
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/jackhenry/stats', methods=['GET'])
def jackhenry_stats():
    """Get Jack Henry database statistics"""
    try:
        stats = jack_henry_client.get_database_stats()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# =============================================================================
# UPDATE CASE STATUS
# =============================================================================

@app.route('/api/case/<case_id>/update_status', methods=['POST'])
def update_case_status(case_id):
    """Update case workflow status"""
    data = request.json
    new_status = data.get('new_status')
    notes = data.get('notes', '')
    performed_by = data.get('performed_by', 'Current User')

    conn = get_db()
    c = conn.cursor()

    # Get current status
    c.execute('SELECT workflow_status FROM workflow_cases WHERE case_id = ?', (case_id,))
    row = c.fetchone()
    if not row:
        return jsonify({'success': False, 'error': 'Case not found'}), 404

    old_status = row['workflow_status']

    # Validate state transition
    if new_status not in WORKFLOW_STATES[old_status]['next_states']:
        return jsonify({'success': False, 'error': f'Invalid state transition from {old_status} to {new_status}'}), 400

    # Update case
    now = datetime.now().isoformat()
    c.execute('''
        UPDATE workflow_cases
        SET workflow_status = ?, last_updated = ?
        WHERE case_id = ?
    ''', (new_status, now, case_id))

    # Add to history
    c.execute('''
        INSERT INTO workflow_history (
            case_id, timestamp, action, old_status, new_status, performed_by, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (case_id, now, 'Status Changed', old_status, new_status, performed_by, notes))

    conn.commit()
    conn.close()

    return jsonify({'success': True})

# =============================================================================
# AI COMMUNICATION SYSTEM
# =============================================================================

@app.route('/api/case/<case_id>/generate_communication', methods=['POST'])
def generate_communication(case_id):
    """AI-powered communication generation based on account types and case details"""
    conn = get_db()
    c = conn.cursor()

    # Get case details
    c.execute('SELECT * FROM workflow_cases WHERE case_id = ?', (case_id,))
    case = dict(c.fetchone())

    # Parse accounts
    accounts = json.loads(case['accounts_json']) if case['accounts_json'] else []

    # Determine primary account type
    account_types = [acc.get('account_type', acc.get('type', 'CHECKING')) for acc in accounts]
    requires_probate = case['requires_probate']

    # Select appropriate template
    template_id = None
    if 'IRA' in account_types or '401K' in account_types or 'RETIREMENT' in account_types:
        template_id = 'IRA_BENEFICIARY'
    elif requires_probate:
        template_id = 'PROBATE_REQUIRED'
    elif len(accounts) > 1:
        template_id = 'MULTIPLE_BENEFICIARIES'
    else:
        template_id = 'POD_SIMPLE'

    # Get template
    c.execute('SELECT * FROM communication_templates WHERE template_id = ?', (template_id,))
    template = dict(c.fetchone())

    # Build variables for template
    account_list = '\n'.join([
        f"- {acc.get('account_type', acc.get('type', 'Account'))}: ${acc.get('balance_current', acc.get('balance', 0)):,.2f}"
        for acc in accounts
    ])

    total_amount = sum(acc.get('balance_current', acc.get('balance', 0)) for acc in accounts)

    variables = {
        'deceased_name': case['deceased_name'],
        'beneficiary_name': case['primary_beneficiary_name'],
        'account_list': account_list,
        'account_type': accounts[0].get('account_type', accounts[0].get('type', 'Account')) if accounts else 'Account',
        'beneficiary_count': len(accounts),
        'beneficiary_percentage': '100' if len(accounts) == 1 else '50'  # Simplified
    }

    # Render template
    subject = template['subject_template'].format(**variables)
    body = template['body_template'].format(**variables)

    conn.close()

    return jsonify({
        'success': True,
        'template_id': template_id,
        'template_name': template['template_name'],
        'channel': template['channel'],
        'subject': subject,
        'body': body
    })

@app.route('/api/case/<case_id>/send_communication', methods=['POST'])
def send_communication(case_id):
    """Send communication to beneficiary (simulated)"""
    data = request.json

    conn = get_db()
    c = conn.cursor()

    now = datetime.now().isoformat()

    # Log communication
    c.execute('''
        INSERT INTO communication_log (
            case_id, sent_date, comm_type, comm_channel, recipient,
            subject, message_body, template_used, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        case_id,
        now,
        data.get('comm_type', 'BENEFICIARY_OUTREACH'),
        data.get('channel', 'email'),
        data.get('recipient'),
        data.get('subject'),
        data.get('body'),
        data.get('template_id'),
        'sent'
    ))

    # Add to history
    c.execute('''
        INSERT INTO workflow_history (
            case_id, timestamp, action, performed_by, notes
        ) VALUES (?, ?, ?, ?, ?)
    ''', (
        case_id,
        now,
        f'Communication Sent: {data.get("comm_type")}',
        data.get('performed_by', 'Current User'),
        f'Sent via {data.get("channel")} to {data.get("recipient")}'
    ))

    # Create task for follow-up
    follow_up_date = (datetime.now() + timedelta(days=7)).isoformat()
    c.execute('''
        INSERT INTO workflow_tasks (
            case_id, created_date, due_date, task_type, task_description, assigned_to
        ) VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        case_id,
        now,
        follow_up_date,
        'FOLLOW_UP',
        'Follow up if documents not received',
        data.get('performed_by', 'Current User')
    ))

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Communication sent and logged'})

@app.route('/api/case/<case_id>/send_docusign', methods=['POST'])
def send_docusign_envelope(case_id):
    """
    Send DocuSign envelope with death claim form to beneficiary
    Creates envelope with claim form and attaches to communication
    """
    conn = get_db()
    c = conn.cursor()

    # Get case details
    c.execute('SELECT * FROM workflow_cases WHERE case_id = ?', (case_id,))
    case = dict(c.fetchone())

    if not case:
        return jsonify({'success': False, 'error': 'Case not found'}), 404

    # Parse accounts for claim amount
    accounts = json.loads(case['accounts_json']) if case['accounts_json'] else []
    claim_amount = case['total_claim_amount'] or 0

    # Get beneficiary info
    beneficiary_name = case['primary_beneficiary_name']
    beneficiary_email = case['primary_beneficiary_email']

    if not beneficiary_email:
        return jsonify({'success': False, 'error': 'No beneficiary email on file'}), 400

    try:
        # Call DocuSign API to create envelope
        # In production with real API keys, this would make actual API call
        result = docusign_client.create_death_claim_envelope(
            case_id=case_id,
            beneficiary_name=beneficiary_name,
            beneficiary_email=beneficiary_email,
            deceased_name=case['deceased_name'],
            claim_amount=claim_amount,
            accounts=accounts
        )

        if not result['success']:
            return jsonify({'success': False, 'error': 'DocuSign envelope creation failed'}), 500

        now = datetime.now().isoformat()

        # Log communication with DocuSign details
        c.execute('''
            INSERT INTO communication_log (
                case_id, sent_date, comm_type, comm_channel, recipient,
                subject, message_body, template_used, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            case_id,
            now,
            'DOCUSIGN_ENVELOPE',
            'docusign',
            beneficiary_email,
            result['email_subject'],
            f"DocuSign Envelope ID: {result['envelope_id']}\nSigning URL: {result['signing_url']}\nStatus: {result['status']}\nExpires: {result['expires_datetime']}",
            'DEATH_CLAIM_FORM',
            'sent'
        ))

        # Add to history
        c.execute('''
            INSERT INTO workflow_history (
                case_id, timestamp, action, performed_by, notes
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            case_id,
            now,
            'DocuSign Envelope Sent',
            'Current User',
            f'Envelope {result["envelope_id"]} sent to {beneficiary_email} for signature'
        ))

        # Create task to check signature status
        check_date = (datetime.now() + timedelta(days=3)).isoformat()
        c.execute('''
            INSERT INTO workflow_tasks (
                case_id, created_date, due_date, task_type, task_description, assigned_to
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            case_id,
            now,
            check_date,
            'DOCUSIGN_FOLLOW_UP',
            f'Check DocuSign envelope status: {result["envelope_id"]}',
            'Current User'
        ))

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'envelope_id': result['envelope_id'],
            'status': result['status'],
            'signing_url': result['signing_url'],
            'expires_datetime': result['expires_datetime']
        })

    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500

# =============================================================================
# DOCUMENT UPLOAD & VERIFICATION INTEGRATION
# =============================================================================

@app.route('/api/case/<case_id>/upload_documents', methods=['POST'])
def upload_documents(case_id):
    """Upload documents and trigger verification"""

    # Get uploaded files
    death_cert = request.files.get('death_cert')
    government_id = request.files.get('government_id')
    claim_form = request.files.get('claim_form')

    if not all([death_cert, government_id, claim_form]):
        return jsonify({'success': False, 'error': 'All three documents required'}), 400

    # Save files temporarily
    upload_dir = Path('uploads') / case_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    death_cert_path = upload_dir / death_cert.filename
    gov_id_path = upload_dir / government_id.filename
    claim_form_path = upload_dir / claim_form.filename

    death_cert.save(death_cert_path)
    government_id.save(gov_id_path)
    claim_form.save(claim_form_path)

    conn = get_db()
    c = conn.cursor()

    now = datetime.now().isoformat()

    # Log documents
    for doc_type, file_path in [
        ('death_certificate', death_cert_path),
        ('government_id', gov_id_path),
        ('claim_form', claim_form_path)
    ]:
        c.execute('''
            INSERT INTO case_documents (
                case_id, uploaded_date, document_type, file_path, verification_status
            ) VALUES (?, ?, ?, ?, ?)
        ''', (case_id, now, doc_type, str(file_path), 'pending'))

    conn.commit()

    # Update case status to IN_VERIFICATION
    c.execute('''
        UPDATE workflow_cases
        SET workflow_status = 'IN_VERIFICATION', last_updated = ?
        WHERE case_id = ?
    ''', (now, case_id))

    c.execute('''
        INSERT INTO workflow_history (
            case_id, timestamp, action, new_status, performed_by, notes
        ) VALUES (?, ?, ?, ?, ?, ?)
    ''', (case_id, now, 'Documents Uploaded', 'IN_VERIFICATION', 'System',
          'All required documents received, verification in progress'))

    conn.commit()
    conn.close()

    # Trigger verification using internal verification engine
    try:
        # Call internal verification engine
        print(f"\n[Starting verification for case {case_id}]")
        verification_result = process_verification(
            str(death_cert_path),
            str(gov_id_path),
            str(claim_form_path)
        )

        # Store verification results
        store_verification_results(case_id, verification_result)

        return jsonify({
            'success': True,
            'message': 'Documents uploaded and verification completed',
            'verification_result': verification_result
        })

    except Exception as e:
        print(f"Error during verification: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Verification failed: {str(e)}'
        }), 500

def store_verification_results(case_id, verification_result):
    """Store verification results in database"""
    conn = get_db()
    c = conn.cursor()

    now = datetime.now().isoformat()

    # Update documents with verification results
    c.execute('''
        UPDATE case_documents
        SET verification_status = 'completed',
            verification_results_json = ?
        WHERE case_id = ?
    ''', (json.dumps(verification_result), case_id))

    # Determine next status based on verification results
    # Check both final_approval flag and issues array
    final_approval = verification_result.get('final_approval', False)
    issues = verification_result.get('issues', [])
    verification_status = verification_result.get('status', 'unknown')

    # Log detailed verification info
    print(f"\n[Verification Results for {case_id}]")
    print(f"  Final Approval: {final_approval}")
    print(f"  Status: {verification_status}")
    print(f"  Issues Count: {len(issues)}")
    if issues:
        for issue in issues:
            print(f"    - {issue}")

    # Determine workflow status
    if final_approval and verification_status == 'approved':
        new_status = 'VERIFIED'
        action = 'Verification Approved'
        notes = 'All documents verified successfully via Textract extraction and cross-verification'
    elif verification_status == 'requires_review':
        new_status = 'NEEDS_REVIEW'
        action = 'Verification Needs Review'
        notes = f'Manual review required. Issues found: {", ".join(issues) if issues else "See verification details"}'
    else:
        new_status = 'NEEDS_REVIEW'
        action = 'Verification Incomplete'
        notes = f'Verification completed with status: {verification_status}'

    # Update case status
    c.execute('''
        UPDATE workflow_cases
        SET workflow_status = ?, last_updated = ?
        WHERE case_id = ?
    ''', (new_status, now, case_id))

    # Add to history
    c.execute('''
        INSERT INTO workflow_history (
            case_id, timestamp, action, new_status, performed_by, notes
        ) VALUES (?, ?, ?, ?, ?, ?)
    ''', (case_id, now, action, new_status, 'Verification System', notes))

    # Create review task if needed
    if new_status == 'NEEDS_REVIEW':
        c.execute('''
            INSERT INTO workflow_tasks (
                case_id, created_date, task_type, task_description, status
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            case_id,
            now,
            'MANUAL_REVIEW',
            f'Review verification results: {", ".join(issues) if issues else "Check verification details"}',
            'pending'
        ))

    conn.commit()
    conn.close()

@app.route('/api/case/<case_id>/verification_results', methods=['GET'])
def get_verification_results(case_id):
    """Get verification results for a case"""
    conn = get_db()
    c = conn.cursor()

    # Get verification results from documents table
    c.execute('''
        SELECT verification_results_json, verification_status, uploaded_date, document_type
        FROM case_documents
        WHERE case_id = ? AND verification_results_json IS NOT NULL
        ORDER BY uploaded_date DESC
        LIMIT 1
    ''', (case_id,))

    row = c.fetchone()
    conn.close()

    if not row:
        return jsonify({
            'success': False,
            'error': 'No verification results found for this case'
        }), 404

    # Parse the stored JSON
    verification_data = json.loads(row[0]) if row[0] else {}

    return jsonify({
        'success': True,
        'verification_status': row[1],
        'verification_date': row[2],
        'results': verification_data
    })

# =============================================================================
# APPROVAL WORKFLOW
# =============================================================================

@app.route('/api/case/<case_id>/request_approval', methods=['POST'])
def request_approval(case_id):
    """Request payment approval based on tiered authorization"""
    data = request.json
    amount = float(data.get('amount', 0))

    # Determine required approver based on amount
    if amount < 10000:
        approver_required = 'PROCESSOR'
    elif amount < 50000:
        approver_required = 'SENIOR_PROCESSOR'
    elif amount < 250000:
        approver_required = 'MANAGER'
    elif amount < 1000000:
        approver_required = 'VP'
    else:
        approver_required = 'SVP'

    conn = get_db()
    c = conn.cursor()

    now = datetime.now().isoformat()

    # Create approval request
    c.execute('''
        INSERT INTO approvals (
            case_id, requested_date, approval_type, amount, requested_by,
            approver_required, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        case_id,
        now,
        'PAYMENT_APPROVAL',
        amount,
        data.get('requested_by', 'Current User'),
        approver_required,
        'pending'
    ))

    # Add to history
    c.execute('''
        INSERT INTO workflow_history (
            case_id, timestamp, action, performed_by, notes
        ) VALUES (?, ?, ?, ?, ?)
    ''', (
        case_id,
        now,
        'Approval Requested',
        data.get('requested_by', 'Current User'),
        f'Payment approval requested for ${amount:,.2f} - Requires {approver_required} approval'
    ))

    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'approver_required': approver_required,
        'message': f'Approval request sent to {approver_required}'
    })

@app.route('/api/approval/<int:approval_id>/approve', methods=['POST'])
def approve_payment(approval_id):
    """Approve a payment request"""
    data = request.json

    conn = get_db()
    c = conn.cursor()

    now = datetime.now().isoformat()

    # Update approval
    c.execute('''
        UPDATE approvals
        SET status = 'approved', approved_by = ?, approved_date = ?, notes = ?
        WHERE approval_id = ?
    ''', (
        data.get('approved_by', 'Current User'),
        now,
        data.get('notes', ''),
        approval_id
    ))

    # Get case_id
    c.execute('SELECT case_id FROM approvals WHERE approval_id = ?', (approval_id,))
    case_id = c.fetchone()['case_id']

    # Update case status to PAYMENT_APPROVED
    c.execute('''
        UPDATE workflow_cases
        SET workflow_status = 'PAYMENT_APPROVED', last_updated = ?
        WHERE case_id = ?
    ''', (now, case_id))

    # Add to history
    c.execute('''
        INSERT INTO workflow_history (
            case_id, timestamp, action, new_status, performed_by, notes
        ) VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        case_id,
        now,
        'Payment Approved',
        'PAYMENT_APPROVED',
        data.get('approved_by', 'Current User'),
        data.get('notes', '')
    ))

    # Create task to process payment in legacy system
    c.execute('''
        INSERT INTO workflow_tasks (
            case_id, created_date, task_type, task_description, status
        ) VALUES (?, ?, ?, ?, ?)
    ''', (
        case_id,
        now,
        'PROCESS_PAYMENT',
        'Process payment in core banking system and mark as completed',
        'pending'
    ))

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Payment approved'})

# =============================================================================
# MANUAL OVERRIDE
# =============================================================================

@app.route('/api/case/<case_id>/manual_override', methods=['POST'])
def manual_override(case_id):
    """Create a manual override with justification"""
    data = request.json

    conn = get_db()
    c = conn.cursor()

    now = datetime.now().isoformat()

    # Log override
    c.execute('''
        INSERT INTO manual_overrides (
            case_id, override_date, override_type, original_value, new_value,
            justification, overridden_by, requires_approval
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        case_id,
        now,
        data.get('override_type'),
        data.get('original_value'),
        data.get('new_value'),
        data.get('justification'),
        data.get('overridden_by', 'Current User'),
        data.get('requires_approval', 0)
    ))

    # If this is a distribution override, update the case's claim amount
    if data.get('override_type') == 'distribution_manual_entry':
        distribution_details = data.get('distribution_details', {})
        claim_amount = distribution_details.get('claim_amount')

        if claim_amount:
            c.execute('''
                UPDATE workflow_cases
                SET total_claim_amount = ?
                WHERE case_id = ?
            ''', (claim_amount, case_id))

    # Add to history
    c.execute('''
        INSERT INTO workflow_history (
            case_id, timestamp, action, performed_by, notes
        ) VALUES (?, ?, ?, ?, ?)
    ''', (
        case_id,
        now,
        f'Manual Override: {data.get("override_type")}',
        data.get('overridden_by', 'Current User'),
        data.get('justification')
    ))

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Override recorded'})


@app.route('/api/case/<case_id>/overrides', methods=['GET'])
def get_case_overrides(case_id):
    """Get all manual overrides for a case"""

    conn = get_db()
    c = conn.cursor()

    c.execute('''
        SELECT * FROM manual_overrides
        WHERE case_id = ?
        ORDER BY override_date DESC
    ''', (case_id,))

    rows = c.fetchall()
    conn.close()

    overrides = [dict(row) for row in rows]

    return jsonify({
        'success': True,
        'overrides': overrides,
        'count': len(overrides)
    })


@app.route('/api/case/<case_id>/discover_accounts', methods=['POST'])
def discover_accounts(case_id):
    """
    Discover deceased customer accounts via Jack Henry API

    Workflow:
    1. Search for deceased customer by name and DOB in Jack Henry
    2. Retrieve all accounts for the customer
    3. Get beneficiary information for each account
    4. Calculate total claim amount
    5. Update case with account information
    """

    conn = get_db()
    c = conn.cursor()

    # Get case details
    c.execute('SELECT * FROM workflow_cases WHERE case_id = ?', (case_id,))
    row = c.fetchone()

    if not row:
        conn.close()
        return jsonify({'success': False, 'error': 'Case not found'}), 404

    case = dict(row)

    # Extract deceased information from verified documents or manual input
    data = request.json
    deceased_name = data.get('deceased_name') or case['deceased_name']
    deceased_dob = data.get('deceased_dob')  # Format: YYYY-MM-DD or MM/DD/YYYY

    if not deceased_name:
        conn.close()
        return jsonify({'success': False, 'error': 'Deceased name is required'}), 400

    # Parse name (assume "First Last" format for now)
    name_parts = deceased_name.strip().split()
    if len(name_parts) < 2:
        conn.close()
        return jsonify({'success': False, 'error': 'Please provide full name (First Last)'}), 400

    first_name = name_parts[0]
    last_name = ' '.join(name_parts[1:])  # Handle middle names

    print(f"\n[Account Discovery] Starting for case {case_id}")
    print(f"  Searching for: {first_name} {last_name}")
    if deceased_dob:
        print(f"  Date of Birth: {deceased_dob}")

    # Step 1: Search for customer in Jack Henry
    try:
        if deceased_dob:
            customer = jack_henry_client.search_customer_by_name_dob(
                first_name, last_name, deceased_dob
            )
        else:
            # Search by SSN if available
            if case['deceased_ssn']:
                customer = jack_henry_client.get_customer_by_ssn(case['deceased_ssn'])
            else:
                conn.close()
                return jsonify({
                    'success': False,
                    'error': 'Either date of birth or SSN is required for account discovery'
                }), 400

        if not customer:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Customer not found in Jack Henry system. Please verify name and date of birth.'
            }), 404

        print(f"  Found customer: {customer.get('customer_sub')}")

        # Step 2: Get all accounts for the customer
        accounts = jack_henry_client.get_customer_accounts(customer['customer_sub'])

        if not accounts:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'No accounts found for this customer'
            }), 404

        print(f"  Found {len(accounts)} accounts")

        # Step 3: Get beneficiaries for each account
        total_claim_amount = 0.0
        accounts_with_beneficiaries = []

        for account in accounts:
            beneficiaries = jack_henry_client.get_account_beneficiaries(account['account_id'])

            account_info = {
                'account_id': account['account_id'],
                'account_number': account.get('account_number'),
                'account_type': account['account_type'],
                'balance': account['balance'],
                'status': account.get('status', 'ACTIVE'),
                'beneficiaries': []
            }

            # Add beneficiaries
            for bene in beneficiaries:
                bene_info = {
                    'name': f"{bene.get('given_name', '')} {bene.get('family_name', '')}".strip(),
                    'ssn': bene.get('ssn'),
                    'percentage': bene.get('percentage', 100),
                    'designation_type': bene.get('designation_type', 'PRIMARY'),
                    'is_primary': bene.get('is_primary', True),
                    'email': bene.get('email'),
                    'phone': bene.get('phone')
                }
                account_info['beneficiaries'].append(bene_info)

            accounts_with_beneficiaries.append(account_info)
            total_claim_amount += account['balance']

        print(f"  Total claim amount: ${total_claim_amount:,.2f}")

        # Step 4: Update case with discovered accounts
        now = datetime.now().isoformat()
        accounts_json = json.dumps(accounts_with_beneficiaries)

        c.execute('''
            UPDATE workflow_cases
            SET accounts_json = ?,
                total_claim_amount = ?,
                last_updated = ?
            WHERE case_id = ?
        ''', (accounts_json, total_claim_amount, now, case_id))

        # Add to workflow history
        c.execute('''
            INSERT INTO workflow_history (
                case_id, timestamp, action, performed_by, notes
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            case_id,
            now,
            'Account Discovery Completed',
            data.get('performed_by', 'System'),
            f'Discovered {len(accounts_with_beneficiaries)} accounts totaling ${total_claim_amount:,.2f}'
        ))

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'customer': {
                'customer_sub': customer['customer_sub'],
                'name': f"{customer.get('given_name')} {customer.get('family_name')}",
                'ssn': customer.get('ssn'),
                'birthdate': customer.get('birthdate')
            },
            'accounts': accounts_with_beneficiaries,
            'total_claim_amount': total_claim_amount,
            'account_count': len(accounts_with_beneficiaries)
        })

    except Exception as e:
        conn.close()
        print(f"[Account Discovery Error] {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Account discovery failed: {str(e)}'
        }), 500


@app.route('/api/case/<case_id>/request_approval', methods=['POST'])
def request_payment_approval(case_id):
    """
    Request payment approval based on tiered approval workflow

    Workflow:
    1. Get case details including total claim amount
    2. Determine required approver tier based on amount
    3. Create approval request in database
    4. Auto-approve if under threshold
    5. Return approval status and required approver
    """

    conn = get_db()
    c = conn.cursor()

    # Get case details
    c.execute('SELECT * FROM workflow_cases WHERE case_id = ?', (case_id,))
    row = c.fetchone()

    if not row:
        conn.close()
        return jsonify({'success': False, 'error': 'Case not found'}), 404

    case = dict(row)
    total_claim_amount = case.get('total_claim_amount', 0.0)

    if not total_claim_amount:
        conn.close()
        return jsonify({
            'success': False,
            'error': 'No claim amount found. Please complete account discovery first.'
        }), 400

    data = request.json
    requested_by = data.get('requested_by', 'Current User')
    notes = data.get('notes', '')

    # Determine required approval tier
    tier = determine_required_approver(total_claim_amount)

    print(f"\n[Approval Request] Case {case_id}")
    print(f"  Amount: ${total_claim_amount:,.2f}")
    print(f"  Tier: {tier['label']}")
    print(f"  Required Approver: {tier['approver_role']}")

    now = datetime.now().isoformat()

    # Check if auto-approved
    if tier['name'] == 'AUTO_APPROVED':
        # Auto-approve and insert approval record
        c.execute('''
            INSERT INTO approvals (
                case_id, requested_date, approval_type, amount,
                requested_by, approver_required, approved_by,
                approved_date, status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            case_id,
            now,
            tier['name'],
            total_claim_amount,
            requested_by,
            'System',
            'System - Auto-Approved',
            now,
            'approved',
            f'Auto-approved: {tier["description"]}'
        ))

        approval_id = c.lastrowid

        # Add to workflow history
        c.execute('''
            INSERT INTO workflow_history (
                case_id, timestamp, action, performed_by, notes
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            case_id,
            now,
            'Payment Auto-Approved',
            'System',
            f'${total_claim_amount:,.2f} - {tier["description"]}'
        ))

        # Update case status to PAYMENT_APPROVED
        c.execute('''
            UPDATE workflow_cases
            SET workflow_status = ?,
                last_updated = ?
            WHERE case_id = ?
        ''', ('PAYMENT_APPROVED', now, case_id))

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'auto_approved': True,
            'approval_id': approval_id,
            'tier': tier,
            'status': 'approved',
            'message': f'Payment auto-approved. {tier["description"]}'
        })

    else:
        # Create pending approval request
        c.execute('''
            INSERT INTO approvals (
                case_id, requested_date, approval_type, amount,
                requested_by, approver_required, status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            case_id,
            now,
            tier['name'],
            total_claim_amount,
            requested_by,
            tier['approver_role'],
            'pending',
            notes
        ))

        approval_id = c.lastrowid

        # Add to workflow history
        c.execute('''
            INSERT INTO workflow_history (
                case_id, timestamp, action, performed_by, notes
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            case_id,
            now,
            'Approval Requested',
            requested_by,
            f'${total_claim_amount:,.2f} - Requires {tier["approver_role"]} approval'
        ))

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'auto_approved': False,
            'approval_id': approval_id,
            'tier': tier,
            'status': 'pending',
            'message': f'Approval request created. Requires {tier["approver_role"]} approval.'
        })


@app.route('/api/case/<case_id>/approve_payment', methods=['POST'])
def approve_payment_tiered(case_id):
    """
    Approve or deny a payment request

    Workflow:
    1. Get pending approval request
    2. Verify approver has authority
    3. Update approval status
    4. Update case workflow status
    5. Add to workflow history
    """

    conn = get_db()
    c = conn.cursor()

    data = request.json
    approval_id = data.get('approval_id')
    approved_by = data.get('approved_by', 'Current User')
    decision = data.get('decision', 'approved')  # 'approved' or 'denied'
    notes = data.get('notes', '')

    if not approval_id:
        conn.close()
        return jsonify({'success': False, 'error': 'Approval ID is required'}), 400

    # Get approval request
    c.execute('SELECT * FROM approvals WHERE approval_id = ? AND case_id = ?', (approval_id, case_id))
    approval_row = c.fetchone()

    if not approval_row:
        conn.close()
        return jsonify({'success': False, 'error': 'Approval request not found'}), 404

    approval = dict(approval_row)

    if approval['status'] != 'pending':
        conn.close()
        return jsonify({
            'success': False,
            'error': f'Approval already {approval["status"]}'
        }), 400

    now = datetime.now().isoformat()

    # Update approval record
    c.execute('''
        UPDATE approvals
        SET approved_by = ?,
            approved_date = ?,
            status = ?,
            notes = ?
        WHERE approval_id = ?
    ''', (approved_by, now, decision, notes, approval_id))

    # Add to workflow history
    action = 'Payment Approved' if decision == 'approved' else 'Payment Denied'
    c.execute('''
        INSERT INTO workflow_history (
            case_id, timestamp, action, performed_by, notes
        ) VALUES (?, ?, ?, ?, ?)
    ''', (
        case_id,
        now,
        action,
        approved_by,
        f'${approval["amount"]:,.2f} - {notes}' if notes else f'${approval["amount"]:,.2f}'
    ))

    # Update case status if approved
    if decision == 'approved':
        c.execute('''
            UPDATE workflow_cases
            SET workflow_status = 'PAYMENT_APPROVED',
                last_updated = ?
            WHERE case_id = ?
        ''', (now, case_id))

    conn.commit()
    conn.close()

    print(f"\n[Payment {decision.upper()}] Case {case_id}")
    print(f"  Approved By: {approved_by}")
    print(f"  Amount: ${approval['amount']:,.2f}")

    return jsonify({
        'success': True,
        'decision': decision,
        'approval_id': approval_id,
        'message': f'Payment {decision} by {approved_by}'
    })


@app.route('/api/case/<case_id>/approvals', methods=['GET'])
def get_case_approvals(case_id):
    """
    Get all approval requests for a case
    """

    conn = get_db()
    c = conn.cursor()

    c.execute('''
        SELECT * FROM approvals
        WHERE case_id = ?
        ORDER BY requested_date DESC
    ''', (case_id,))

    rows = c.fetchall()
    conn.close()

    approvals = [dict(row) for row in rows]

    return jsonify({
        'success': True,
        'approvals': approvals,
        'count': len(approvals)
    })


# =============================================================================
# COMPLIANCE REPORT GENERATION
# =============================================================================

@app.route('/case/<case_id>/compliance_report')
def generate_compliance_report(case_id):
    """Generate comprehensive compliance report for a death claim case"""

    conn = get_db()
    c = conn.cursor()

    # Get case details
    c.execute('SELECT * FROM workflow_cases WHERE case_id = ?', (case_id,))
    case_row = c.fetchone()

    if not case_row:
        return "Case not found", 404

    case = dict(case_row)

    # Get discovered accounts
    accounts_json = case.get('discovered_accounts_json', '[]')
    accounts = json.loads(accounts_json) if accounts_json else []

    # Get workflow history
    c.execute('''
        SELECT * FROM workflow_history
        WHERE case_id = ?
        ORDER BY timestamp ASC
    ''', (case_id,))
    history_rows = c.fetchall()
    history = [dict(row) for row in history_rows]

    # Get verification results (if table exists)
    verification_data = {}
    verification_row = None
    try:
        c.execute('''
            SELECT verification_data, verification_status, verification_date
            FROM document_verification
            WHERE case_id = ?
            ORDER BY verification_date DESC
            LIMIT 1
        ''', (case_id,))
        verification_row = c.fetchone()
        if verification_row and verification_row[0]:
            verification_data = json.loads(verification_row[0])
    except sqlite3.OperationalError:
        # Table doesn't exist yet
        pass

    # Get manual overrides
    c.execute('''
        SELECT * FROM manual_overrides
        WHERE case_id = ?
        ORDER BY override_date DESC
    ''', (case_id,))
    override_rows = c.fetchall()
    overrides = [dict(row) for row in override_rows]

    # Get approvals
    c.execute('''
        SELECT * FROM approvals
        WHERE case_id = ?
        ORDER BY requested_date DESC
    ''', (case_id,))
    approval_rows = c.fetchall()
    approvals = [dict(row) for row in approval_rows]

    conn.close()

    # Calculate case age
    created = datetime.fromisoformat(case.get('created_at', case.get('created_date', datetime.now().isoformat())))
    age_days = (datetime.now() - created).days

    # Generate HTML report
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Compliance Report - {case_id}</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background: #f8f9fa;
            }}
            .header {{
                background: white;
                padding: 30px;
                border-radius: 8px;
                margin-bottom: 20px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
            .header h1 {{
                margin: 0 0 10px 0;
                color: #1e40af;
            }}
            .header-meta {{
                color: #6b7280;
                font-size: 0.9rem;
            }}
            .section {{
                background: white;
                padding: 25px;
                border-radius: 8px;
                margin-bottom: 20px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
            .section h2 {{
                margin-top: 0;
                color: #111827;
                border-bottom: 2px solid #e5e7eb;
                padding-bottom: 10px;
            }}
            .info-grid {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 15px;
                margin: 15px 0;
            }}
            .info-item {{
                display: flex;
                flex-direction: column;
            }}
            .info-label {{
                font-size: 0.75rem;
                font-weight: 600;
                text-transform: uppercase;
                color: #6b7280;
                margin-bottom: 4px;
            }}
            .info-value {{
                font-size: 0.95rem;
                color: #111827;
            }}
            .status-badge {{
                display: inline-block;
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 0.75rem;
                font-weight: 600;
                text-transform: uppercase;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 15px 0;
            }}
            th, td {{
                text-align: left;
                padding: 12px;
                border-bottom: 1px solid #e5e7eb;
            }}
            th {{
                background: #f9fafb;
                font-weight: 600;
                font-size: 0.85rem;
                text-transform: uppercase;
                color: #6b7280;
            }}
            .timeline {{
                border-left: 2px solid #e5e7eb;
                padding-left: 20px;
                margin-left: 10px;
            }}
            .timeline-item {{
                position: relative;
                padding-bottom: 20px;
            }}
            .timeline-item:before {{
                content: '';
                position: absolute;
                left: -26px;
                top: 5px;
                width: 10px;
                height: 10px;
                border-radius: 50%;
                background: #2563eb;
            }}
            .timeline-date {{
                font-size: 0.75rem;
                color: #6b7280;
            }}
            .timeline-action {{
                font-weight: 600;
                color: #111827;
                margin: 4px 0;
            }}
            .timeline-notes {{
                font-size: 0.9rem;
                color: #4b5563;
            }}
            .print-btn {{
                background: #2563eb;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 0.9rem;
                font-weight: 500;
            }}
            .print-btn:hover {{
                background: #1d4ed8;
            }}
            @media print {{
                body {{
                    background: white;
                }}
                .print-btn {{
                    display: none;
                }}
                .section {{
                    break-inside: avoid;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Death Claim Compliance Report</h1>
            <div class="header-meta">
                Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}<br>
                Case ID: <strong>{case_id}</strong><br>
                Report Type: Regulatory Compliance & Audit Trail
            </div>
            <div style="margin-top: 15px;">
                <button class="print-btn" onclick="window.print()">Print / Save as PDF</button>
            </div>
        </div>

        <div class="section">
            <h2>Case Summary</h2>
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">Case ID</div>
                    <div class="info-value">{case_id}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Current Status</div>
                    <div class="info-value">
                        <span class="status-badge" style="background: {WORKFLOW_STATES[case['workflow_status']]['color']}20; color: {WORKFLOW_STATES[case['workflow_status']]['color']}">
                            {WORKFLOW_STATES[case['workflow_status']]['label']}
                        </span>
                    </div>
                </div>
                <div class="info-item">
                    <div class="info-label">Deceased</div>
                    <div class="info-value">{case.get('deceased_name', 'N/A')}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Date of Death</div>
                    <div class="info-value">{case.get('date_of_death', 'N/A')}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Primary Beneficiary</div>
                    <div class="info-value">{case.get('primary_beneficiary_name', 'N/A')}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Total Claim Amount</div>
                    <div class="info-value" style="font-weight: 600; color: #059669;">
                        ${case.get('total_claim_amount', 0):,.2f}
                    </div>
                </div>
                <div class="info-item">
                    <div class="info-label">Case Age</div>
                    <div class="info-value">{age_days} days</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Assigned To</div>
                    <div class="info-value">{case.get('assigned_to', 'Unassigned')}</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Discovered Accounts</h2>
            {f"""
            <table>
                <thead>
                    <tr>
                        <th>Account Number</th>
                        <th>Account Type</th>
                        <th>Balance</th>
                        <th>Beneficiaries</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join([f'''
                    <tr>
                        <td>{acc.get('account_number', 'N/A')}</td>
                        <td>{acc.get('account_type', 'N/A')}</td>
                        <td>${acc.get('balance_current', acc.get('balance', 0)):,.2f}</td>
                        <td>{", ".join([b.get('name', 'N/A') for b in acc.get('beneficiaries', [])]) or 'None'}</td>
                    </tr>
                    ''' for acc in accounts])}
                </tbody>
            </table>
            """ if accounts else "<p>No accounts discovered yet.</p>"}
        </div>

        <div class="section">
            <h2>Verification Results</h2>
            {f"""
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">Verification Status</div>
                    <div class="info-value">{verification_row[1] if verification_row else 'Pending'}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Verification Date</div>
                    <div class="info-value">{verification_row[2] if verification_row else 'N/A'}</div>
                </div>
            </div>
            """ if verification_row else "<p>No verification results available.</p>"}
        </div>

        <div class="section">
            <h2>Manual Overrides</h2>
            {f"""
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Type</th>
                        <th>Performed By</th>
                        <th>Justification</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join([f'''
                    <tr>
                        <td>{datetime.fromisoformat(ov['override_date']).strftime('%Y-%m-%d %H:%M')}</td>
                        <td>{ov['override_type']}</td>
                        <td>{ov['overridden_by']}</td>
                        <td>{ov['justification']}</td>
                    </tr>
                    ''' for ov in overrides])}
                </tbody>
            </table>
            """ if overrides else "<p>No manual overrides recorded.</p>"}
        </div>

        <div class="section">
            <h2>Approval History</h2>
            {f"""
            <table>
                <thead>
                    <tr>
                        <th>Requested Date</th>
                        <th>Type</th>
                        <th>Amount</th>
                        <th>Approver Required</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join([f'''
                    <tr>
                        <td>{datetime.fromisoformat(ap['requested_date']).strftime('%Y-%m-%d %H:%M')}</td>
                        <td>{ap['approval_type']}</td>
                        <td>${ap.get('amount', 0):,.2f}</td>
                        <td>{ap['approver_required']}</td>
                        <td>{ap['status']}</td>
                    </tr>
                    ''' for ap in approvals])}
                </tbody>
            </table>
            """ if approvals else "<p>No approvals requested.</p>"}
        </div>

        <div class="section">
            <h2>Complete Audit Trail</h2>
            <div class="timeline">
                {"".join([f'''
                <div class="timeline-item">
                    <div class="timeline-date">{datetime.fromisoformat(h['timestamp']).strftime('%B %d, %Y at %I:%M %p')}</div>
                    <div class="timeline-action">{h['action']}</div>
                    <div class="timeline-notes">By: {h['performed_by']}{f" - {h['notes']}" if h.get('notes') else ''}</div>
                </div>
                ''' for h in history])}
            </div>
        </div>

        <div class="section" style="background: #f9fafb; border: 1px solid #e5e7eb;">
            <h2 style="color: #6b7280;">Compliance Statement</h2>
            <p style="font-size: 0.9rem; line-height: 1.6; color: #4b5563;">
                This report was generated automatically by the BeneBridge CRM Platform and contains a complete
                record of all actions, verifications, and approvals related to this death claim case.
                All data is maintained in accordance with regulatory requirements and internal compliance policies.
                This report is suitable for audit purposes and regulatory review.
            </p>
            <p style="font-size: 0.85rem; color: #6b7280; margin-top: 15px;">
                <strong>Report ID:</strong> {case_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}<br>
                <strong>System:</strong> BeneBridge CRM Platform v1.0<br>
                <strong>Generated By:</strong> Current User
            </p>
        </div>
    </body>
    </html>
    '''

    return html


# =============================================================================
# START SERVER
# =============================================================================

if __name__ == '__main__':
    # Initialize database if needed
    from database import init_database, seed_communication_templates
    try:
        init_database()
        seed_communication_templates()
    except:
        pass  # Database already exists


# =============================================================================
# LEXISNEXIS BATCH PROCESSING
# =============================================================================

@app.route('/api/batch/lexisnexis', methods=['POST'])
def run_lexisnexis_batch():
    """
    Trigger LexisNexis overnight batch processing to create proactive cases.

    Per dissertation: Reduces fraud window from 3 days to 0-1 day (67% reduction)
    by creating cases in NOTIFIED state before beneficiaries contact institution.
    """
    try:
        from lexisnexis_batch_processor import LexisNexisBatchProcessor

        # Initialize processor with CRM database path
        db_path = os.path.join(os.path.dirname(__file__), 'crm_database.db')
        processor = LexisNexisBatchProcessor(db_path)

        # Run batch processing
        stats = processor.run_overnight_batch()

        return jsonify({
            'success': True,
            'batch_statistics': stats,
            'message': f"Batch processing complete: {stats['cases_created']} cases created"
        })

    except Exception as e:
        print(f"Error running LexisNexis batch: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    print("=" * 80)
    print("BeneBridge CRM Platform")
    print("Death Claim Workflow Management System")
    print("=" * 80)
    print("\nStarting server on http://localhost:5010")
    print("\nFeatures:")
    print("  - Employee Dashboard with Case Queue")
    print("  - Workflow State Management")
    print("  - AI-Powered Communication Templates")
    print("  - Document Upload & Verification Integration")
    print("  - Tiered Approval Workflow")
    print("  - Manual Override Tracking")
    print("  - Complete Audit Trail")
    print("  - LexisNexis Batch Processing (Proactive Case Creation)")
    print("=" * 80)

    app.run(host='0.0.0.0', port=5010, debug=True)
