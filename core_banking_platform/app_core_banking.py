#!/usr/bin/env python3
"""
BeneBridge Core Banking Platform
Port: 5007
Based on Chapters 4 & 5 system design specifications
"""

from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from flask_cors import CORS
import sqlite3
import json
import time
from datetime import datetime, timedelta
from collections import defaultdict
import random
import hashlib

app = Flask(__name__)
app.secret_key = 'benebridge-core-banking-secret-key-2026'
CORS(app)

# Database connection
def get_db():
    conn = sqlite3.connect('../benebridge.db')
    conn.row_factory = sqlite3.Row
    return conn

# Performance metrics database
def init_metrics_db():
    conn = sqlite3.connect('core_banking_metrics.db')
    c = conn.cursor()

    # Performance metrics table
    c.execute('''CREATE TABLE IF NOT EXISTS processing_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_number TEXT,
        stage TEXT,
        start_time TIMESTAMP,
        end_time TIMESTAMP,
        duration_seconds REAL,
        status TEXT,
        automated BOOLEAN,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Verification accuracy table
    c.execute('''CREATE TABLE IF NOT EXISTS verification_accuracy (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_number TEXT,
        verification_type TEXT,
        confidence_score REAL,
        result TEXT,
        processing_time_ms REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Fraud detection metrics
    c.execute('''CREATE TABLE IF NOT EXISTS fraud_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_number TEXT,
        fraud_score REAL,
        detection_layers TEXT,
        true_positive BOOLEAN,
        false_positive BOOLEAN,
        processing_time_ms REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # SLA tracking
    c.execute('''CREATE TABLE IF NOT EXISTS sla_tracking (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_number TEXT,
        target_completion_date TIMESTAMP,
        actual_completion_date TIMESTAMP,
        sla_hours INTEGER,
        elapsed_hours REAL,
        sla_percentage REAL,
        status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # API endpoint performance
    c.execute('''CREATE TABLE IF NOT EXISTS api_performance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        endpoint TEXT,
        method TEXT,
        response_time_ms REAL,
        status_code INTEGER,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Task management for CRM workflow
    c.execute('''CREATE TABLE IF NOT EXISTS case_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_number TEXT,
        task_name TEXT,
        task_type TEXT,
        task_order INTEGER,
        status TEXT DEFAULT 'pending',
        assigned_to TEXT,
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        verification_status TEXT,
        verification_score REAL,
        verification_details TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Document uploads tracking
    c.execute('''CREATE TABLE IF NOT EXISTS document_uploads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_number TEXT,
        task_id INTEGER,
        document_type TEXT,
        file_name TEXT,
        file_size INTEGER,
        upload_status TEXT,
        verification_status TEXT,
        confidence_score REAL,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (task_id) REFERENCES case_tasks (id)
    )''')

    # Real-time verification updates
    c.execute('''CREATE TABLE IF NOT EXISTS verification_updates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_number TEXT,
        task_id INTEGER,
        update_type TEXT,
        message TEXT,
        status TEXT,
        details TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    conn.commit()
    conn.close()

# Initialize metrics database
init_metrics_db()

#=============================================================================
# DASHBOARD & MAIN VIEWS
#=============================================================================

@app.route('/')
def index():
    """Employee Workspace - CRM Style Task-Based Interface"""
    return redirect(url_for('employee_workspace'))

@app.route('/workspace')
def employee_workspace():
    """Employee Workspace - My Tasks"""
    conn = get_db()
    c = conn.cursor()

    # Get my active tasks
    metrics_conn = sqlite3.connect('core_banking_metrics.db')
    metrics_conn.row_factory = sqlite3.Row
    m = metrics_conn.cursor()

    # Get pending tasks assigned to current employee
    m.execute('''SELECT * FROM case_tasks
                 WHERE status IN ('pending', 'in_progress')
                 ORDER BY task_order, created_at LIMIT 20''')
    my_tasks = m.fetchall()

    # Get recently completed tasks
    m.execute('''SELECT * FROM case_tasks
                 WHERE status = 'completed'
                 ORDER BY completed_at DESC LIMIT 10''')
    completed_tasks = m.fetchall()

    # Get cases needing attention
    c.execute('''SELECT * FROM cases
                 WHERE status IN ('pending', 'under_review')
                 ORDER BY submission_date DESC LIMIT 10''')
    active_cases = c.fetchall()

    conn.close()
    metrics_conn.close()

    return render_template('employee_workspace.html',
                         my_tasks=my_tasks,
                         completed_tasks=completed_tasks,
                         active_cases=active_cases)

@app.route('/dashboard')
def dashboard():
    """Core Banking Platform Dashboard"""
    conn = get_db()
    c = conn.cursor()

    # Get key statistics
    c.execute('SELECT COUNT(*) as total FROM cases')
    total_cases = c.fetchone()['total']

    c.execute("SELECT COUNT(*) as pending FROM cases WHERE status = 'pending'")
    pending_cases = c.fetchone()['pending']

    c.execute("SELECT COUNT(*) as under_review FROM cases WHERE status = 'under_review'")
    under_review = c.fetchone()['under_review']

    c.execute("SELECT COUNT(*) as approved FROM cases WHERE status = 'approved'")
    approved = c.fetchone()['approved']

    # Get recent cases
    c.execute('''SELECT case_number, deceased_name, beneficiary_name,
                 account_balance, status, submission_date, workflow_stage
                 FROM cases ORDER BY submission_date DESC LIMIT 10''')
    recent_cases = c.fetchall()

    conn.close()

    return render_template('core_banking_dashboard.html',
                         total_cases=total_cases,
                         pending_cases=pending_cases,
                         under_review=under_review,
                         approved=approved,
                         recent_cases=recent_cases)

@app.route('/analytics')
def analytics():
    """Analytics Dashboard - Performance Metrics"""
    return render_template('analytics_dashboard.html')

@app.route('/cases')
def cases_list():
    """Case Management View"""
    conn = get_db()
    c = conn.cursor()

    # Get filter parameters
    status_filter = request.args.get('status', '')

    query = '''SELECT case_number, deceased_name, beneficiary_name,
               account_type, account_balance, status, submission_date,
               workflow_stage, priority
               FROM cases'''

    if status_filter:
        query += f" WHERE status = '{status_filter}'"

    query += ' ORDER BY submission_date DESC'

    c.execute(query)
    cases = c.fetchall()

    conn.close()

    return render_template('cases_list.html', cases=cases, status_filter=status_filter)

@app.route('/case/<case_number>')
def case_detail(case_number):
    """Detailed Case View"""
    conn = get_db()
    c = conn.cursor()

    c.execute('SELECT * FROM cases WHERE case_number = ?', (case_number,))
    case = c.fetchone()

    if not case:
        return "Case not found", 404

    conn.close()

    # No documents table - simplified for demo
    documents = []

    return render_template('case_detail_core.html', case=case, documents=documents)

@app.route('/process/<case_number>')
def process_case(case_number):
    """CRM-Style Case Processing Workflow"""
    conn = get_db()
    c = conn.cursor()

    c.execute('SELECT * FROM cases WHERE case_number = ?', (case_number,))
    case = c.fetchone()

    if not case:
        return "Case not found", 404

    # Get or create tasks for this case
    metrics_conn = sqlite3.connect('core_banking_metrics.db')
    metrics_conn.row_factory = sqlite3.Row
    m = metrics_conn.cursor()

    # Check if tasks exist
    m.execute('SELECT COUNT(*) as count FROM case_tasks WHERE case_number = ?', (case_number,))
    task_count = m.fetchone()['count']

    if task_count == 0:
        # Initialize workflow tasks based on account type
        initialize_case_tasks(case_number, case['account_type'], m)
        metrics_conn.commit()

    # Get all tasks for this case
    m.execute('''SELECT * FROM case_tasks
                 WHERE case_number = ?
                 ORDER BY task_order''', (case_number,))
    tasks = m.fetchall()

    # Get verification updates
    m.execute('''SELECT * FROM verification_updates
                 WHERE case_number = ?
                 ORDER BY timestamp DESC LIMIT 20''', (case_number,))
    verification_updates = m.fetchall()

    conn.close()
    metrics_conn.close()

    return render_template('case_processing.html',
                         case=case,
                         tasks=tasks,
                         verification_updates=verification_updates)

@app.route('/task/<int:task_id>')
def task_detail(task_id):
    """Individual Task Processing View"""
    metrics_conn = sqlite3.connect('core_banking_metrics.db')
    metrics_conn.row_factory = sqlite3.Row
    m = metrics_conn.cursor()

    m.execute('SELECT * FROM case_tasks WHERE id = ?', (task_id,))
    task = m.fetchone()

    if not task:
        return "Task not found", 404

    # Get case details
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM cases WHERE case_number = ?', (task['case_number'],))
    case = c.fetchone()

    # Get uploaded documents for this task
    m.execute('''SELECT * FROM document_uploads
                 WHERE task_id = ?
                 ORDER BY uploaded_at DESC''', (task_id,))
    documents = m.fetchall()

    # Get verification updates for this task
    m.execute('''SELECT * FROM verification_updates
                 WHERE task_id = ?
                 ORDER BY timestamp DESC''', (task_id,))
    updates = m.fetchall()

    conn.close()
    metrics_conn.close()

    return render_template('task_processing.html',
                         task=task,
                         case=case,
                         documents=documents,
                         updates=updates)

@app.route('/api/v1/task/<int:task_id>/start', methods=['POST'])
def start_task(task_id):
    """Start a task"""
    metrics_conn = sqlite3.connect('core_banking_metrics.db')
    m = metrics_conn.cursor()

    m.execute('''UPDATE case_tasks
                 SET status = 'in_progress', started_at = ?
                 WHERE id = ?''', (datetime.now(), task_id))

    metrics_conn.commit()
    metrics_conn.close()

    return jsonify({'success': True, 'status': 'in_progress'})

@app.route('/api/v1/task/<int:task_id>/upload', methods=['POST'])
def upload_document_to_task(task_id):
    """Upload document for a task and trigger verification"""
    start_time = time.time()

    try:
        data = request.get_json()
        document_type = data.get('document_type')
        file_name = data.get('file_name')
        file_size = data.get('file_size', 0)

        metrics_conn = sqlite3.connect('core_banking_metrics.db')
        m = metrics_conn.cursor()

        # Get task details
        m.execute('SELECT * FROM case_tasks WHERE id = ?', (task_id,))
        task = m.fetchone()

        if not task:
            return jsonify({'success': False, 'error': 'Task not found'}), 404

        case_number = task[1]  # case_number is second column

        # Insert document upload record
        m.execute('''INSERT INTO document_uploads
                     (case_number, task_id, document_type, file_name, file_size, upload_status, verification_status)
                     VALUES (?, ?, ?, ?, ?, 'uploaded', 'pending')''',
                  (case_number, task_id, document_type, file_name, file_size))

        doc_id = m.lastrowid

        # Add verification update
        m.execute('''INSERT INTO verification_updates
                     (case_number, task_id, update_type, message, status)
                     VALUES (?, ?, ?, ?, ?)''',
                  (case_number, task_id, 'upload', f'Document uploaded: {file_name}', 'success'))

        metrics_conn.commit()

        # Simulate background verification
        verification_result = simulate_document_verification(document_type)

        # Update document with verification results
        m.execute('''UPDATE document_uploads
                     SET verification_status = ?, confidence_score = ?
                     WHERE id = ?''',
                  (verification_result['status'], verification_result['confidence'], doc_id))

        # Add verification update
        m.execute('''INSERT INTO verification_updates
                     (case_number, task_id, update_type, message, status, details)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (case_number, task_id, 'verification',
                   f'{document_type} verification: {verification_result["status"]}',
                   verification_result['status'],
                   json.dumps(verification_result)))

        metrics_conn.commit()
        metrics_conn.close()

        response_time = (time.time() - start_time) * 1000

        return jsonify({
            'success': True,
            'document_id': doc_id,
            'verification': verification_result,
            'processing_time_ms': response_time
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/v1/task/<int:task_id>/complete', methods=['POST'])
def complete_task(task_id):
    """Mark task as completed"""
    data = request.get_json()

    metrics_conn = sqlite3.connect('core_banking_metrics.db')
    m = metrics_conn.cursor()

    m.execute('''UPDATE case_tasks
                 SET status = 'completed',
                     completed_at = ?,
                     notes = ?
                 WHERE id = ?''',
              (datetime.now(), data.get('notes', ''), task_id))

    # Get task to find case_number
    m.execute('SELECT case_number FROM case_tasks WHERE id = ?', (task_id,))
    task = m.fetchone()

    if task:
        m.execute('''INSERT INTO verification_updates
                     (case_number, task_id, update_type, message, status)
                     VALUES (?, ?, ?, ?, ?)''',
                  (task[0], task_id, 'task_complete', 'Task marked as completed', 'success'))

    metrics_conn.commit()
    metrics_conn.close()

    return jsonify({'success': True, 'status': 'completed'})

@app.route('/api/v1/case/<case_number>/updates')
def get_case_updates(case_number):
    """Get real-time verification updates for a case"""
    metrics_conn = sqlite3.connect('core_banking_metrics.db')
    metrics_conn.row_factory = sqlite3.Row
    m = metrics_conn.cursor()

    m.execute('''SELECT * FROM verification_updates
                 WHERE case_number = ?
                 ORDER BY timestamp DESC LIMIT 50''', (case_number,))

    updates = []
    for row in m.fetchall():
        updates.append({
            'id': row['id'],
            'update_type': row['update_type'],
            'message': row['message'],
            'status': row['status'],
            'details': row['details'],
            'timestamp': row['timestamp']
        })

    metrics_conn.close()

    return jsonify(updates)

@app.route('/case/new', methods=['GET', 'POST'])
def new_case():
    """Create a new case"""
    if request.method == 'GET':
        return render_template('new_case_form.html')

    # Handle POST - create new case
    try:
        data = request.form

        # Generate unique case number
        case_number = f"BC-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

        # Insert into cases table
        conn = get_db()
        c = conn.cursor()

        c.execute('''INSERT INTO cases (
            case_number, deceased_name, deceased_ssn, date_of_death,
            beneficiary_name, beneficiary_ssn, beneficiary_email, beneficiary_phone,
            account_type, account_number, account_balance, financial_institution,
            status, workflow_stage, priority, submission_date,
            id_verified, beneficiary_info_verified
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (case_number,
             data.get('deceased_name'),
             data.get('deceased_ssn'),
             data.get('date_of_death'),
             data.get('beneficiary_name'),
             data.get('beneficiary_ssn'),
             data.get('beneficiary_email'),
             data.get('beneficiary_phone'),
             data.get('account_type'),
             data.get('account_number'),
             float(data.get('account_balance', 0)),
             data.get('financial_institution', 'Internal'),
             'pending',  # status
             1,  # workflow_stage
             data.get('priority', 'medium'),
             datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
             False,  # id_verified
             False   # beneficiary_info_verified
            ))

        conn.commit()
        conn.close()

        # Initialize workflow tasks
        metrics_conn = sqlite3.connect('core_banking_metrics.db')
        m = metrics_conn.cursor()
        initialize_case_tasks(case_number, data.get('account_type'), m)

        # Add initial verification update
        m.execute('''INSERT INTO verification_updates
                     (case_number, task_id, update_type, message, status)
                     VALUES (?, NULL, ?, ?, ?)''',
                  (case_number, 'case_created',
                   f'New case {case_number} created successfully. Ready to begin processing.',
                   'success'))

        metrics_conn.commit()
        metrics_conn.close()

        # Redirect to case processing page
        return redirect(url_for('process_case', case_number=case_number))

    except Exception as e:
        return f"Error creating case: {str(e)}", 500

# Helper functions
def initialize_case_tasks(case_number, account_type, cursor):
    """Initialize workflow tasks for a case based on account type"""
    tasks = []

    if account_type == '401k':
        tasks = [
            ('Upload Death Certificate', 'document_upload', 1),
            ('Upload Beneficiary ID', 'document_upload', 2),
            ('Upload Account Statement', 'document_upload', 3),
            ('Verify Death Certificate', 'verification', 4),
            ('Verify Beneficiary Identity', 'verification', 5),
            ('Check Spousal Consent', 'review', 6),
            ('ERISA Compliance Review', 'compliance', 7),
            ('Calculate Tax Withholding', 'calculation', 8),
            ('Manager Approval', 'approval', 9),
            ('Compliance Officer Approval', 'approval', 10),
            ('Payment Processing', 'payment', 11)
        ]
    elif account_type == 'IRA':
        tasks = [
            ('Upload Death Certificate', 'document_upload', 1),
            ('Upload Beneficiary ID', 'document_upload', 2),
            ('Verify Death Certificate', 'verification', 3),
            ('Verify Beneficiary Identity', 'verification', 4),
            ('Calculate Tax Withholding', 'calculation', 5),
            ('Manager Approval', 'approval', 6),
            ('Payment Processing', 'payment', 7)
        ]
    else:
        tasks = [
            ('Upload Death Certificate', 'document_upload', 1),
            ('Upload Beneficiary ID', 'document_upload', 2),
            ('Verify Documents', 'verification', 3),
            ('Review & Approve', 'approval', 4),
            ('Payment Processing', 'payment', 5)
        ]

    for task_name, task_type, task_order in tasks:
        cursor.execute('''INSERT INTO case_tasks
                         (case_number, task_name, task_type, task_order, status, assigned_to)
                         VALUES (?, ?, ?, ?, 'pending', 'Employee')''',
                      (case_number, task_name, task_type, task_order))

def simulate_document_verification(document_type):
    """Simulate document verification process"""
    time.sleep(random.uniform(0.5, 2.0))  # Simulate processing time

    confidence = random.uniform(85, 99)

    if confidence >= 90:
        status = 'verified'
    elif confidence >= 75:
        status = 'needs_review'
    else:
        status = 'failed'

    return {
        'status': status,
        'confidence': round(confidence, 2),
        'method': 'blockchain' if document_type == 'death_certificate' and random.random() > 0.5 else 'traditional',
        'processing_time': round(random.uniform(0.5, 2.0), 2)
    }

#=============================================================================
# API ENDPOINTS - 8 Core Microservices (Chapter 5, Section 5.2.2)
#=============================================================================

@app.route('/api/v1/document/upload', methods=['POST'])
def api_document_upload():
    """Document Management Service - Upload endpoint"""
    start_time = time.time()

    try:
        data = request.get_json()
        case_number = data.get('case_number')
        document_type = data.get('document_type')
        file_data = data.get('file_data')  # Base64 encoded

        # Simulate document processing pipeline (Chapter 5, lines 165-168)
        # 1. Upload validation
        # 2. Virus scanning
        # 3. Storage to S3
        # 4. AI classification
        # 5. OCR extraction

        response_time = (time.time() - start_time) * 1000

        # Log API performance
        log_api_performance('/api/v1/document/upload', 'POST', response_time, 200)

        return jsonify({
            'success': True,
            'document_id': hashlib.sha256(f"{case_number}_{document_type}".encode()).hexdigest()[:16],
            'classification': document_type,
            'confidence': random.uniform(0.92, 0.99),
            'ocr_status': 'completed',
            'processing_time_ms': response_time
        })

    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        log_api_performance('/api/v1/document/upload', 'POST', response_time, 500)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/v1/verification/blockchain', methods=['POST'])
def api_blockchain_verification():
    """Verification Service - Blockchain verification (Chapter 5, lines 179-224)"""
    start_time = time.time()

    try:
        data = request.get_json()
        blockchain_hash = data.get('blockchain_hash')
        certificate_type = data.get('certificate_type', 'death_certificate')

        # Simulate Titan Seal API call (Chapter 5, lines 188-214)
        time.sleep(random.uniform(0.5, 2.0))  # API latency

        verified = random.choice([True, True, True, False])  # 75% success rate

        response_time = (time.time() - start_time) * 1000

        result = {
            'verified': verified,
            'confidence_score': 100 if verified else 0,
            'deceased_info': {
                'full_name': 'John Doe',
                'ssn': '123-45-6789',
                'date_of_death': '2024-06-15',
                'place_of_death': 'Los Angeles, CA'
            } if verified else None,
            'processing_time_ms': response_time,
            'verification_method': 'blockchain'
        }

        # Log verification accuracy
        log_verification_accuracy(
            data.get('case_number', 'TEST'),
            'blockchain',
            result['confidence_score'],
            'verified' if verified else 'failed',
            response_time
        )

        log_api_performance('/api/v1/verification/blockchain', 'POST', response_time, 200)

        return jsonify(result)

    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        log_api_performance('/api/v1/verification/blockchain', 'POST', response_time, 500)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/v1/verification/traditional', methods=['POST'])
def api_traditional_verification():
    """Verification Service - Traditional multi-layer verification (Chapter 5, lines 226-263)"""
    start_time = time.time()

    try:
        data = request.get_json()
        document_id = data.get('document_id')

        # Simulate 4-layer verification (Chapter 5, lines 229-249)
        # Layer 1: Document Quality Analysis
        quality_score = random.uniform(75, 98)

        # Layer 2: OCR and Field Extraction
        ocr_confidence = random.uniform(80, 98)

        # Layer 3: Rule-Based Validation
        validation_score = random.uniform(85, 100)

        # Layer 4: External Cross-Reference
        cross_ref_score = random.uniform(70, 95)

        # Composite confidence score (Chapter 5, lines 252-259)
        composite_score = (
            0.40 * quality_score +
            0.20 * ocr_confidence +
            0.20 * validation_score +
            0.20 * cross_ref_score
        )

        # Disposition rules (Chapter 5, lines 261-263)
        if composite_score >= 90:
            disposition = 'auto_verified'
        elif composite_score >= 70:
            disposition = 'expedited_review'
        else:
            disposition = 'full_manual_verification'

        response_time = (time.time() - start_time) * 1000

        result = {
            'composite_score': round(composite_score, 2),
            'disposition': disposition,
            'layer_scores': {
                'quality': round(quality_score, 2),
                'ocr': round(ocr_confidence, 2),
                'validation': round(validation_score, 2),
                'cross_reference': round(cross_ref_score, 2)
            },
            'processing_time_ms': response_time,
            'verification_method': 'traditional'
        }

        log_verification_accuracy(
            data.get('case_number', 'TEST'),
            'traditional',
            composite_score,
            disposition,
            response_time
        )

        log_api_performance('/api/v1/verification/traditional', 'POST', response_time, 200)

        return jsonify(result)

    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        log_api_performance('/api/v1/verification/traditional', 'POST', response_time, 500)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/v1/identity/verify', methods=['POST'])
def api_identity_verification():
    """Identity Verification Service (Chapter 5, lines 100-102)"""
    start_time = time.time()

    try:
        data = request.get_json()
        beneficiary_id = data.get('beneficiary_id')
        document_type = data.get('document_type', 'drivers_license')

        # Simulate biometric and document verification
        time.sleep(random.uniform(1.0, 3.0))

        # Biometric facial matching
        facial_similarity = random.uniform(0.75, 0.98)
        document_authentic = random.choice([True, True, True, False])

        # Integrated identity scoring
        identity_score = (facial_similarity * 0.6 + (1.0 if document_authentic else 0.0) * 0.4) * 100

        if identity_score >= 85:
            verification_status = 'verified'
        elif identity_score >= 70:
            verification_status = 'manual_review'
        else:
            verification_status = 'failed'

        response_time = (time.time() - start_time) * 1000

        result = {
            'verification_status': verification_status,
            'identity_score': round(identity_score, 2),
            'facial_similarity': round(facial_similarity, 4),
            'document_authentic': document_authentic,
            'processing_time_ms': response_time
        }

        log_api_performance('/api/v1/identity/verify', 'POST', response_time, 200)

        return jsonify(result)

    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        log_api_performance('/api/v1/identity/verify', 'POST', response_time, 500)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/v1/fraud/detect', methods=['POST'])
def api_fraud_detection():
    """Fraud Detection Service - 6-Layer Defense (Chapter 5, lines 103, 329-366)"""
    start_time = time.time()

    try:
        data = request.get_json()
        case_number = data.get('case_number')

        # Six-layer fraud detection (Chapter 5, lines 331-363)
        layers = {}

        # Layer 1: Duplicate Detection
        layers['duplicate_detection'] = random.uniform(0, 30)

        # Layer 2: Identity Fraud
        layers['identity_fraud'] = random.uniform(0, 25)

        # Layer 3: Document Fraud
        layers['document_fraud'] = random.uniform(0, 20)

        # Layer 4: Behavioral Pattern Analysis
        layers['behavioral_patterns'] = random.uniform(0, 35)

        # Layer 5: Network Analysis
        layers['network_analysis'] = random.uniform(0, 15)

        # Layer 6: Integrated Risk Scoring (Chapter 5, lines 364-366)
        integrated_risk_score = (
            layers['duplicate_detection'] * 0.20 +
            layers['identity_fraud'] * 0.25 +
            layers['document_fraud'] * 0.25 +
            layers['behavioral_patterns'] * 0.20 +
            layers['network_analysis'] * 0.10
        )

        # Disposition rules
        if integrated_risk_score < 20:
            action = 'auto_process'
        elif integrated_risk_score < 60:
            action = 'standard_review'
        elif integrated_risk_score < 80:
            action = 'enhanced_due_diligence'
        else:
            action = 'fraud_investigation'

        response_time = (time.time() - start_time) * 100  # Target < 100ms

        result = {
            'fraud_score': round(integrated_risk_score, 2),
            'action': action,
            'layer_scores': {k: round(v, 2) for k, v in layers.items()},
            'explainability': [
                f"Duplicate detection: {layers['duplicate_detection']:.1f}%",
                f"Identity fraud risk: {layers['identity_fraud']:.1f}%",
                f"Document fraud risk: {layers['document_fraud']:.1f}%"
            ],
            'processing_time_ms': response_time
        }

        # Log fraud metrics
        log_fraud_detection(case_number, integrated_risk_score, json.dumps(layers), response_time)

        log_api_performance('/api/v1/fraud/detect', 'POST', response_time, 200)

        return jsonify(result)

    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        log_api_performance('/api/v1/fraud/detect', 'POST', response_time, 500)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/v1/workflow/create', methods=['POST'])
def api_workflow_create():
    """Workflow Orchestration Service - Dynamic workflow generation (Chapter 5, lines 104-106, 267-293)"""
    start_time = time.time()

    try:
        data = request.get_json()
        case_number = data.get('case_number')
        account_type = data.get('account_type')

        # Dynamic workflow generation based on account type (Chapter 5, lines 270-293)
        if account_type == 'IRA':
            workflow_stages = [
                {'stage': 'document_receipt', 'automated': True, 'est_hours': 0.1},
                {'stage': 'death_cert_verification', 'automated': True, 'est_hours': 24},
                {'stage': 'identity_verification', 'automated': True, 'est_hours': 2},
                {'stage': 'tax_calculation', 'automated': True, 'est_hours': 0.5},
                {'stage': 'single_approval', 'automated': False, 'est_hours': 8},
                {'stage': 'payment_handoff', 'automated': True, 'est_hours': 0.1}
            ]
        elif account_type == '401k':
            workflow_stages = [
                {'stage': 'document_receipt', 'automated': True, 'est_hours': 0.1},
                {'stage': 'death_cert_verification', 'automated': True, 'est_hours': 24},
                {'stage': 'identity_verification', 'automated': True, 'est_hours': 2},
                {'stage': 'spousal_consent_check', 'automated': False, 'est_hours': 4},
                {'stage': 'erisa_compliance_review', 'automated': True, 'est_hours': 1},
                {'stage': 'tax_calculation', 'automated': True, 'est_hours': 0.5},
                {'stage': 'dual_approval', 'automated': False, 'est_hours': 16},
                {'stage': 'payment_handoff', 'automated': True, 'est_hours': 0.1}
            ]
        else:
            workflow_stages = [
                {'stage': 'document_receipt', 'automated': True, 'est_hours': 0.1},
                {'stage': 'verification', 'automated': True, 'est_hours': 24},
                {'stage': 'approval', 'automated': False, 'est_hours': 8},
                {'stage': 'payment_handoff', 'automated': True, 'est_hours': 0.1}
            ]

        response_time = (time.time() - start_time) * 1000

        result = {
            'workflow_id': hashlib.sha256(f"{case_number}_{account_type}".encode()).hexdigest()[:16],
            'account_type': account_type,
            'stages': workflow_stages,
            'estimated_total_hours': sum(s['est_hours'] for s in workflow_stages),
            'parallel_optimization': True,
            'processing_time_ms': response_time
        }

        log_api_performance('/api/v1/workflow/create', 'POST', response_time, 200)

        return jsonify(result)

    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        log_api_performance('/api/v1/workflow/create', 'POST', response_time, 500)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/v1/compliance/check', methods=['POST'])
def api_compliance_check():
    """Compliance Monitoring Service (Chapter 5, lines 106-108)"""
    start_time = time.time()

    try:
        data = request.get_json()
        case_number = data.get('case_number')
        account_type = data.get('account_type')

        # Regulatory rule engine checks
        compliance_checks = []

        if account_type == '401k':
            compliance_checks.append({'rule': 'ERISA Spousal Consent', 'status': 'pass', 'details': 'Spouse is primary beneficiary'})
            compliance_checks.append({'rule': 'SECURE Act RMD Rules', 'status': 'pass', 'details': 'Distribution within 10 years'})

        compliance_checks.append({'rule': 'IRC Tax Withholding', 'status': 'pass', 'details': '20% federal withholding applied'})
        compliance_checks.append({'rule': 'FinCEN CDD', 'status': 'pass', 'details': 'Beneficial owner verified'})
        compliance_checks.append({'rule': 'OFAC Sanctions Screen', 'status': 'pass', 'details': 'No match found'})

        response_time = (time.time() - start_time) * 1000

        result = {
            'compliance_status': 'compliant',
            'checks_performed': len(compliance_checks),
            'checks_passed': len([c for c in compliance_checks if c['status'] == 'pass']),
            'compliance_checks': compliance_checks,
            'processing_time_ms': response_time
        }

        log_api_performance('/api/v1/compliance/check', 'POST', response_time, 200)

        return jsonify(result)

    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        log_api_performance('/api/v1/compliance/check', 'POST', response_time, 500)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/v1/communication/notify', methods=['POST'])
def api_communication_notify():
    """Communication Service - Multi-channel notifications (Chapter 5, lines 108-110)"""
    start_time = time.time()

    try:
        data = request.get_json()
        case_number = data.get('case_number')
        event_type = data.get('event_type')
        channels = data.get('channels', ['email'])

        # Simulate multi-channel delivery
        delivery_status = {}
        for channel in channels:
            if channel == 'email':
                delivery_status['email'] = {'sent': True, 'provider': 'SendGrid', 'message_id': 'sg_' + hashlib.sha256(case_number.encode()).hexdigest()[:16]}
            elif channel == 'sms':
                delivery_status['sms'] = {'sent': True, 'provider': 'Twilio', 'message_sid': 'SM' + hashlib.sha256(case_number.encode()).hexdigest()[:16]}
            elif channel == 'push':
                delivery_status['push'] = {'sent': True, 'provider': 'Firebase', 'notification_id': 'fcm_' + hashlib.sha256(case_number.encode()).hexdigest()[:16]}

        response_time = (time.time() - start_time) * 1000

        result = {
            'notification_id': hashlib.sha256(f"{case_number}_{event_type}".encode()).hexdigest()[:16],
            'event_type': event_type,
            'delivery_status': delivery_status,
            'processing_time_ms': response_time
        }

        log_api_performance('/api/v1/communication/notify', 'POST', response_time, 200)

        return jsonify(result)

    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        log_api_performance('/api/v1/communication/notify', 'POST', response_time, 500)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/v1/integration/core-banking', methods=['POST'])
def api_core_banking_integration():
    """Integration Service - Core Banking Adapter (Chapter 5, lines 110-112, 460-495)"""
    start_time = time.time()

    try:
        data = request.get_json()
        operation = data.get('operation')
        account_number = data.get('account_number')

        # Simulate adapter pattern for different core banking platforms
        platform = data.get('platform', 'Fiserv')

        if operation == 'get_account_details':
            result_data = {
                'account_number': account_number,
                'account_type': '401k',
                'balance': 245000.00,
                'status': 'active',
                'owner_name': 'John Doe',
                'beneficiaries': [
                    {'name': 'Jane Doe', 'relationship': 'spouse', 'percentage': 100}
                ]
            }
        elif operation == 'freeze_account':
            result_data = {
                'account_number': account_number,
                'status': 'frozen',
                'reason': 'Death claim processing'
            }
        elif operation == 'trigger_payment':
            result_data = {
                'payment_id': 'PAY_' + hashlib.sha256(account_number.encode()).hexdigest()[:16],
                'status': 'queued',
                'estimated_processing': '1-2 business days'
            }
        else:
            result_data = {'error': 'Unknown operation'}

        response_time = (time.time() - start_time) * 1000

        result = {
            'platform': platform,
            'operation': operation,
            'data': result_data,
            'processing_time_ms': response_time
        }

        log_api_performance('/api/v1/integration/core-banking', 'POST', response_time, 200)

        return jsonify(result)

    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        log_api_performance('/api/v1/integration/core-banking', 'POST', response_time, 500)
        return jsonify({'success': False, 'error': str(e)}), 500

#=============================================================================
# PERFORMANCE METRICS API
#=============================================================================

@app.route('/api/v1/metrics/processing-times')
def api_metrics_processing_times():
    """Get processing time metrics"""
    conn = sqlite3.connect('core_banking_metrics.db')
    c = conn.cursor()

    c.execute('''SELECT stage, AVG(duration_seconds) as avg_duration,
                 MIN(duration_seconds) as min_duration,
                 MAX(duration_seconds) as max_duration,
                 COUNT(*) as count
                 FROM processing_metrics
                 WHERE end_time IS NOT NULL
                 GROUP BY stage''')

    results = []
    for row in c.fetchall():
        results.append({
            'stage': row[0],
            'avg_duration_hours': round(row[1] / 3600, 2),
            'min_duration_hours': round(row[2] / 3600, 2),
            'max_duration_hours': round(row[3] / 3600, 2),
            'count': row[4]
        })

    conn.close()
    return jsonify(results)

@app.route('/api/v1/metrics/verification-accuracy')
def api_metrics_verification_accuracy():
    """Get verification accuracy metrics"""
    conn = sqlite3.connect('core_banking_metrics.db')
    c = conn.cursor()

    c.execute('''SELECT verification_type,
                 AVG(confidence_score) as avg_confidence,
                 COUNT(CASE WHEN confidence_score >= 90 THEN 1 END) as auto_verified,
                 COUNT(*) as total
                 FROM verification_accuracy
                 GROUP BY verification_type''')

    results = []
    for row in c.fetchall():
        results.append({
            'verification_type': row[0],
            'avg_confidence': round(row[1], 2),
            'auto_verified': row[2],
            'total': row[3],
            'auto_verification_rate': round((row[2] / row[3]) * 100, 2) if row[3] > 0 else 0
        })

    conn.close()
    return jsonify(results)

@app.route('/api/v1/metrics/fraud-detection')
def api_metrics_fraud_detection():
    """Get fraud detection metrics"""
    conn = sqlite3.connect('core_banking_metrics.db')
    c = conn.cursor()

    c.execute('''SELECT
                 AVG(fraud_score) as avg_fraud_score,
                 COUNT(CASE WHEN fraud_score >= 80 THEN 1 END) as high_risk_cases,
                 COUNT(CASE WHEN fraud_score < 20 THEN 1 END) as low_risk_cases,
                 COUNT(*) as total_cases,
                 AVG(processing_time_ms) as avg_processing_time
                 FROM fraud_metrics''')

    row = c.fetchone()

    result = {
        'avg_fraud_score': round(row[0], 2) if row[0] else 0,
        'high_risk_cases': row[1],
        'low_risk_cases': row[2],
        'total_cases': row[3],
        'avg_processing_time_ms': round(row[4], 2) if row[4] else 0
    }

    conn.close()
    return jsonify(result)

@app.route('/api/v1/metrics/sla-performance')
def api_metrics_sla_performance():
    """Get SLA performance metrics"""
    conn = sqlite3.connect('core_banking_metrics.db')
    c = conn.cursor()

    c.execute('''SELECT
                 COUNT(CASE WHEN sla_percentage <= 100 THEN 1 END) as within_sla,
                 COUNT(CASE WHEN sla_percentage > 100 THEN 1 END) as breached_sla,
                 AVG(sla_percentage) as avg_sla_percentage,
                 COUNT(*) as total_cases
                 FROM sla_tracking
                 WHERE status = 'completed' ''')

    row = c.fetchone()

    result = {
        'within_sla': row[0],
        'breached_sla': row[1],
        'avg_sla_percentage': round(row[2], 2) if row[2] else 0,
        'total_cases': row[3],
        'sla_compliance_rate': round((row[0] / row[3]) * 100, 2) if row[3] > 0 else 0
    }

    conn.close()
    return jsonify(result)

@app.route('/api/v1/metrics/api-performance')
def api_metrics_api_performance():
    """Get API endpoint performance metrics"""
    conn = sqlite3.connect('core_banking_metrics.db')
    c = conn.cursor()

    c.execute('''SELECT endpoint, method,
                 AVG(response_time_ms) as avg_response_time,
                 MIN(response_time_ms) as min_response_time,
                 MAX(response_time_ms) as max_response_time,
                 COUNT(*) as request_count,
                 COUNT(CASE WHEN status_code >= 500 THEN 1 END) as error_count
                 FROM api_performance
                 WHERE timestamp >= datetime('now', '-1 day')
                 GROUP BY endpoint, method''')

    results = []
    for row in c.fetchall():
        results.append({
            'endpoint': row[0],
            'method': row[1],
            'avg_response_time_ms': round(row[2], 2),
            'min_response_time_ms': round(row[3], 2),
            'max_response_time_ms': round(row[4], 2),
            'request_count': row[5],
            'error_count': row[6],
            'success_rate': round(((row[5] - row[6]) / row[5]) * 100, 2) if row[5] > 0 else 0
        })

    conn.close()
    return jsonify(results)

#=============================================================================
# LOGGING FUNCTIONS
#=============================================================================

def log_api_performance(endpoint, method, response_time_ms, status_code):
    """Log API endpoint performance"""
    conn = sqlite3.connect('core_banking_metrics.db')
    c = conn.cursor()
    c.execute('''INSERT INTO api_performance (endpoint, method, response_time_ms, status_code)
                 VALUES (?, ?, ?, ?)''', (endpoint, method, response_time_ms, status_code))
    conn.commit()
    conn.close()

def log_verification_accuracy(case_number, verification_type, confidence_score, result, processing_time_ms):
    """Log verification accuracy metrics"""
    conn = sqlite3.connect('core_banking_metrics.db')
    c = conn.cursor()
    c.execute('''INSERT INTO verification_accuracy
                 (case_number, verification_type, confidence_score, result, processing_time_ms)
                 VALUES (?, ?, ?, ?, ?)''',
              (case_number, verification_type, confidence_score, result, processing_time_ms))
    conn.commit()
    conn.close()

def log_fraud_detection(case_number, fraud_score, detection_layers, processing_time_ms):
    """Log fraud detection metrics"""
    conn = sqlite3.connect('core_banking_metrics.db')
    c = conn.cursor()
    c.execute('''INSERT INTO fraud_metrics
                 (case_number, fraud_score, detection_layers, processing_time_ms)
                 VALUES (?, ?, ?, ?)''',
              (case_number, fraud_score, detection_layers, processing_time_ms))
    conn.commit()
    conn.close()

#=============================================================================
# VERIFICATION DEMO ENDPOINTS
#=============================================================================

@app.route('/case/<case_number>/verification-demo')
def verification_demo_page(case_number):
    """Show real-time verification demo page"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM cases WHERE case_number = ?', (case_number,))
    case = c.fetchone()
    conn.close()

    if not case:
        return "Case not found", 404

    return render_template('verification_demo.html', case=case)

@app.route('/api/case/<case_number>/run-verification', methods=['POST'])
def run_verification_api(case_number):
    """Run complete verification workflow and stream results"""
    from verification_demo import VerificationDemo

    # Get case data
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM cases WHERE case_number = ?', (case_number,))
    case_row = c.fetchone()
    conn.close()

    if not case_row:
        return jsonify({'error': 'Case not found'}), 404

    # Convert to dict (using correct column indices)
    case_data = {
        'case_number': case_row[1],
        'account_type': case_row[12],  # Column 12
        'account_balance': float(case_row[13]),  # Column 13 - convert to float
        'has_blockchain_cert': random.choice([True, False]),  # Random for demo
        'deceased_name': case_row[2],
        'date_of_death': case_row[5],  # Column 5
        'beneficiary_name': case_row[6],  # Column 6
        'beneficiary_dob': '1985-06-15',  # Simulated
        'beneficiary_state': 'CA',  # Simulated
        'beneficiary_relationship': 'child'  # Simulated
    }

    # Run verification
    demo = VerificationDemo()
    results = demo.run_complete_verification(case_data)

    return jsonify({
        'success': True,
        'results': results
    })

#=============================================================================
# MAIN
#=============================================================================

if __name__ == '__main__':
    print("=" * 80)
    print("BeneBridge Core Banking Platform")
    print("Based on Chapter 4 & 5 System Design Specifications")
    print("=" * 80)
    print("\nStarting server on http://localhost:5007")
    print("\nKey Features:")
    print("  - Three-Layer Architecture (Presentation, Verification, Data)")
    print("  - 8 Core Microservices with REST APIs")
    print("  - Performance Metrics & Analytics Dashboard")
    print("  - Real-time Processing Time Tracking")
    print("  - Accuracy Rate Monitoring")
    print("  - SLA Enforcement & Tracking")
    print("=" * 80)

    app.run(host='0.0.0.0', port=5007, debug=True)
