from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file
from flask_cors import CORS
import sqlite3
from datetime import datetime
import os
import sys

# Add parent directory to path to import core banking mock
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core_banking_mock import get_core_banking_api
from reconciliation_engine import get_reconciliation_engine
from notification_service import get_notification_service
from tax_engine import get_tax_engine
from payment_system import get_payment_system
from institution_portal.permissions import (
    ROLES, PERMISSIONS, has_permission, get_user_permissions,
    require_permission, require_role, get_role_info, can_approve_amount
)

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = 'institution-secret-key-change-in-production'
CORS(app)

# Initialize core banking API connection
core_api = get_core_banking_api()

# Initialize reconciliation engine
reconciliation = get_reconciliation_engine()

# Initialize notification service
notifications = get_notification_service()

# Initialize tax engine
tax_engine = get_tax_engine()

# Initialize payment system
payment_system = get_payment_system()

# Database helper - points to shared database
def get_db():
    db_path = os.path.join(os.path.dirname(__file__), '..', 'benebridge.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# =====================================
# VERIFICATION FUNCTIONS
# =====================================

def verify_death_certificate(case_id):
    """
    UNIVERSAL DEATH CERTIFICATE VERIFICATION

    Handles TWO verification paths:
    1. BLOCKCHAIN CERTIFICATES: Verify via Titan Seal API
    2. PHYSICAL/SCANNED CERTIFICATES: Verify via document quality API + rule-based validation

    Returns: Confidence score 0-100
    """
    conn = get_db()
    cursor = conn.cursor()

    # Get case details
    case = cursor.execute('SELECT * FROM cases WHERE id = ?', (case_id,)).fetchone()

    if not case:
        return 0

    score = 0

    # PATH 1: BLOCKCHAIN DEATH CERTIFICATE
    if case['death_cert_type'] == 'blockchain' and case['blockchain_hash']:
        print(f"🔗 Verifying BLOCKCHAIN death certificate via Titan Seal...")

        # TODO: Call Titan Seal API
        blockchain_verified = verify_titan_seal_hash(case['blockchain_hash'])

        if blockchain_verified:
            score = 100  # Blockchain verification = 100% confidence
            print(f"✅ Blockchain verified: {score}/100")
        else:
            score = 0
            print(f"❌ Blockchain verification failed: {score}/100")

    # PATH 2: PHYSICAL/SCANNED DEATH CERTIFICATE
    else:
        print(f"📄 Verifying PHYSICAL death certificate...")

        # STEP 1: Document Quality API Check (40 points max)
        api_quality_score = 85  # Mock API response (0-100)
        api_points = int((api_quality_score / 100) * 40)
        score += api_points
        print(f"  📸 Document Quality API: {api_quality_score}/100 → {api_points}/40 points")

        # STEP 2: Rule-Based Validation (60 points max)
        rule_points = 0

        # Rule 1: Certificate number format (20 points)
        cert_number = case['death_certificate_number']
        if cert_number and len(cert_number) > 0:
            if cert_number.startswith('2026-CA-'):
                rule_points += 20
                print(f"  ✅ Certificate number format valid: +20 points")
            else:
                rule_points += 10
                print(f"  ⚠️  Certificate number format unusual: +10 points")

        # Rule 2: Required fields present (20 points)
        required_fields_present = True  # Mock for now
        if required_fields_present:
            rule_points += 20
            print(f"  ✅ Required fields present: +20 points")

        # Rule 3: Name matching (20 points)
        name_match_confidence = 95  # Mock (0-100)
        name_points = int((name_match_confidence / 100) * 20)
        rule_points += name_points
        print(f"  ✅ Name matching: {name_match_confidence}% → {name_points}/20 points")

        score += rule_points
        print(f"  📋 Rule-based validation: {rule_points}/60 points")
        print(f"  🎯 TOTAL SCORE: {score}/100")

    # Update database
    cursor.execute('''
        UPDATE cases
        SET death_cert_verification_score = ?
        WHERE id = ?
    ''', (score, case_id))
    conn.commit()
    conn.close()

    return score

def verify_titan_seal_hash(blockchain_hash):
    """Verifies blockchain hash with Titan Seal API"""
    # MOCK: Assume blockchain hash is valid for demo
    return True

def verify_id(case_id):
    """Verifies ID documents via third-party API"""
    print(f"🆔 Verifying ID documents via API...")

    # MOCK: Assume ID is verified for demo
    id_verified = True

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE cases SET id_verified = ? WHERE id = ?', (id_verified, case_id))
    conn.commit()
    conn.close()

    print(f"  ✅ ID verified: {id_verified}")
    return id_verified

def verify_beneficiary_info(case_id):
    """Verifies beneficiary information against bank's internal POD/TOD records"""
    print(f"🏦 Verifying beneficiary info against bank records...")

    conn = get_db()
    cursor = conn.cursor()
    case = cursor.execute('SELECT * FROM cases WHERE id = ?', (case_id,)).fetchone()

    # MOCK: Check if beneficiary name matches POD designation in bank system
    info_matches = True

    cursor.execute('UPDATE cases SET beneficiary_info_verified = ? WHERE id = ?', (info_matches, case_id))
    conn.commit()
    conn.close()

    print(f"  ✅ Beneficiary info verified: {info_matches}")
    return info_matches

def run_verifications(case_id):
    """Orchestrates all verification checks and updates case status"""
    print(f"\n{'='*60}")
    print(f"RUNNING VERIFICATIONS FOR CASE ID: {case_id}")
    print(f"{'='*60}\n")

    # Run all verifications
    death_cert_score = verify_death_certificate(case_id)
    id_verified = verify_id(case_id)
    beneficiary_verified = verify_beneficiary_info(case_id)

    # Decision logic
    conn = get_db()
    cursor = conn.cursor()

    # Get old status
    case = cursor.execute('SELECT status FROM cases WHERE id = ?', (case_id,)).fetchone()
    old_status = case['status'] if case else 'pending'

    new_status = 'pending'

    if death_cert_score == 100:  # Blockchain verified
        if id_verified and beneficiary_verified:
            new_status = 'under_review'
        else:
            new_status = 'pending'
    elif death_cert_score >= 85:  # High confidence physical certificate
        if id_verified and beneficiary_verified:
            new_status = 'under_review'
        else:
            new_status = 'pending'
    elif death_cert_score >= 60:  # Medium confidence
        new_status = 'under_review'
    else:  # Low confidence
        new_status = 'rejected'

    # Update case status
    cursor.execute('UPDATE cases SET status = ? WHERE id = ?', (new_status, case_id))

    # Log activity
    cursor.execute('''
        INSERT INTO activity_log (case_id, action, details)
        VALUES (?, ?, ?)
    ''', (case_id, 'Verification Complete',
          f'Death cert: {death_cert_score}/100, ID: {id_verified}, Beneficiary: {beneficiary_verified}, Status: {new_status}'))

    conn.commit()
    conn.close()

    # Send notification if status changed
    if old_status != new_status:
        notifications.notify_status_change(case_id, old_status, new_status)

    print(f"\n{'='*60}")
    print(f"VERIFICATION SUMMARY:")
    print(f"  Death Certificate: {death_cert_score}/100")
    print(f"  ID Verified: {id_verified}")
    print(f"  Beneficiary Info: {beneficiary_verified}")
    print(f"  New Status: {new_status}")
    print(f"{'='*60}\n")

    return {
        'death_cert_score': death_cert_score,
        'id_verified': id_verified,
        'beneficiary_verified': beneficiary_verified,
        'status': new_status
    }

# =====================================
# ROUTES
# =====================================

@app.route('/')
def institution_login_redirect():
    """Redirect root to login"""
    return redirect(url_for('institution_login'))

@app.route('/institution/login', methods=['GET', 'POST'])
def institution_login():
    """Institution employee login"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        conn = get_db()
        cursor = conn.cursor()
        user = cursor.execute('SELECT * FROM users WHERE email = ? AND password_hash = ?',
                            (email, password)).fetchone()
        conn.close()

        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['full_name']
            session['user_role'] = user['role']
            return redirect(url_for('institution_dashboard'))
        else:
            return render_template('institution_login.html', error='Invalid credentials')

    return render_template('institution_login.html')

@app.route('/institution/dashboard')
def institution_dashboard():
    """CRM dashboard showing all cases with workflow info"""
    if 'user_id' not in session:
        return redirect(url_for('institution_login'))

    conn = get_db()
    cursor = conn.cursor()

    # Get all cases with workflow info
    cases = cursor.execute('SELECT * FROM cases ORDER BY submission_date DESC').fetchall()

    # Calculate age in days and add workflow name
    from datetime import datetime
    cases_with_workflow = []
    for case in cases:
        case_dict = dict(case)
        submission_date = datetime.fromisoformat(case['submission_date'])
        age_days = (datetime.now() - submission_date).days
        case_dict['age_days'] = age_days

        # Get workflow name based on account type
        workflow_names = {
            'IRA': 'IRA Transfer',
            '401K': '401(k) Claim',
            'TOD': 'TOD Transfer',
            'POD': 'POD Payout',
            'Trust': 'Trust Distribution'
        }
        case_dict['workflow_name'] = workflow_names.get(case['account_type'], 'Standard Process')

        cases_with_workflow.append(case_dict)

    # Get stats
    total_cases = len(cases)
    under_review = len([c for c in cases if c['status'] == 'under_review'])
    pending = len([c for c in cases if c['status'] == 'pending'])
    approved = len([c for c in cases if c['status'] == 'approved'])

    conn.close()

    return render_template('institution_dashboard_crm.html',
                         cases_with_workflow=cases_with_workflow,
                         total_cases=total_cases,
                         under_review=under_review,
                         pending=pending,
                         approved=approved,
                         user_name=session.get('user_name'),
                         user_role=session.get('user_role'))

@app.route('/institution/create-case', methods=['GET', 'POST'])
def create_case():
    """Manually create a new case when death notification received (traditional method)"""
    if 'user_id' not in session:
        return redirect(url_for('institution_login'))

    if request.method == 'POST':
        from datetime import datetime
        import random

        # Get form data
        deceased_name = request.form.get('deceased_name')
        deceased_ssn = request.form.get('deceased_ssn')
        date_of_death = request.form.get('date_of_death')
        account_number = request.form.get('account_number')
        account_type = request.form.get('account_type')
        account_balance = float(request.form.get('account_balance', 0))
        beneficiary_name = request.form.get('beneficiary_name', '')
        beneficiary_ssn = request.form.get('beneficiary_ssn', '')
        beneficiary_phone = request.form.get('beneficiary_phone', '')
        beneficiary_email = request.form.get('beneficiary_email', '')
        notification_method = request.form.get('notification_method', 'phone')  # phone, mail, in-person, email

        # Check for duplicates BEFORE creating
        case_data = {
            'deceased_name': deceased_name,
            'deceased_ssn': deceased_ssn,
            'account_number': account_number,
            'beneficiary_name': beneficiary_name,
            'beneficiary_ssn': beneficiary_ssn
        }

        potential_duplicates = reconciliation.find_potential_duplicates(case_data)

        # If high-confidence duplicates found, handle merge instead of creating new case
        if potential_duplicates:
            high_confidence = [d for d in potential_duplicates if d['confidence'] >= 95]

            if high_confidence:
                # Merge into existing case
                existing_case = high_confidence[0]

                conn = get_db()
                cursor = conn.cursor()

                merge_result = reconciliation.merge_case_data(
                    existing_case['id'],
                    {
                        'account_balance': account_balance,
                        'beneficiary_phone': beneficiary_phone,
                        'beneficiary_email': beneficiary_email,
                        'date_of_death': date_of_death
                    },
                    session.get('user_id')
                )

                # Log duplicate detection
                cursor.execute('''
                    INSERT INTO activity_log (case_id, user_id, action, details)
                    VALUES (?, ?, ?, ?)
                ''', (
                    existing_case['id'],
                    session.get('user_id'),
                    'duplicate_merged',
                    f"Merged duplicate submission. Confidence: {existing_case['confidence']}%. Match type: {existing_case['match_type']}"
                ))

                conn.commit()
                conn.close()

                # Redirect to existing case with merge notification
                return redirect(url_for('case_detail', case_id=existing_case['id'], merged=1))

        conn = get_db()
        cursor = conn.cursor()

        # Generate case number
        case_number = f"DC-{datetime.now().year}-{random.randint(1000, 9999)}"

        # Generate secure access code for beneficiary portal
        import secrets
        import string
        access_code = 'ACCESS-' + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))

        # Create case
        cursor.execute('''
            INSERT INTO cases (
                case_number, deceased_name, deceased_ssn, date_of_death,
                beneficiary_name, beneficiary_ssn, beneficiary_phone, beneficiary_email,
                account_number, account_type, account_balance,
                submission_date, status, workflow_stage,
                death_cert_type, death_cert_verification_score,
                id_verified, beneficiary_info_verified, access_code
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            case_number, deceased_name, deceased_ssn, date_of_death,
            beneficiary_name, beneficiary_ssn, beneficiary_phone, beneficiary_email,
            account_number, account_type, account_balance,
            datetime.now().isoformat(), 'pending', 1,
            'physical', 0,  # No death cert yet, score = 0
            0, 0,  # Not verified yet
            access_code
        ))

        case_id = cursor.lastrowid

        # Create initial workflow tasks based on account type
        create_workflow_tasks(cursor, case_id, account_type)

        conn.commit()
        conn.close()

        # Send welcome notification to beneficiary
        notifications.notify_case_created(case_id)

        return redirect(url_for('case_detail', case_id=case_id))

    return render_template('create_case.html', user_name=session.get('user_name'))

@app.route('/institution/api/lookup-account/<account_number>')
def lookup_account(account_number):
    """
    Look up account details from core banking system.
    This endpoint pulls real-time data from the bank's core system.
    """
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    # Query core banking system
    account = core_api.lookup_account(account_number)

    if not account:
        return jsonify({
            'found': False,
            'message': f'Account {account_number} not found in core system'
        }), 404

    # Get beneficiary designations
    beneficiaries = core_api.get_beneficiary_designations(account_number)

    # Get account restrictions
    restrictions = core_api.check_account_restrictions(account_number)

    # Verify account holder status
    holder_verification = core_api.verify_account_holder(
        account['primary_holder']['name'],
        account['primary_holder']['ssn']
    )

    # Check for existing cases with this account
    conn = get_db()
    cursor = conn.cursor()
    existing_cases = cursor.execute(
        'SELECT case_number, status FROM cases WHERE account_number = ?',
        (account_number,)
    ).fetchall()
    conn.close()

    return jsonify({
        'found': True,
        'account': {
            'account_number': account['account_number'],
            'account_type': account['account_type'],
            'current_balance': account['current_balance'],
            'account_status': account['account_status'],
            'primary_holder': account['primary_holder'],
        },
        'beneficiaries': beneficiaries,
        'restrictions': restrictions,
        'holder_verification': holder_verification,
        'existing_cases': [dict(c) for c in existing_cases],
        'has_existing_cases': len(existing_cases) > 0
    })

@app.route('/institution/api/verify-deceased', methods=['POST'])
def verify_deceased():
    """
    Verify deceased identity against core banking system.
    """
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    data = request.json
    name = data.get('name')
    ssn = data.get('ssn')

    if not name or not ssn:
        return jsonify({'error': 'Name and SSN required'}), 400

    # Verify against core system
    verification = core_api.verify_account_holder(name, ssn)

    return jsonify(verification)

def create_workflow_tasks(cursor, case_id, account_type):
    """Create workflow tasks for a new case"""
    # Standard tasks for IRA (can expand for other account types)
    # Format: (case_id, task_name, task_description, stage, completed, requires_documents, requires_data, verification_checks, assigned_role)
    tasks = [
        # Stage 1: Beneficiary Claim Form Review - operations
        (case_id, 'Review Beneficiary Claim Form', 'Review beneficiary claim form for completeness and accuracy', 1, 0,
         '["beneficiary_form"]', '["beneficiary_name", "beneficiary_ssn", "account_number"]',
         '["All required fields completed", "Signature present and legible", "Distribution method clearly specified", "Form matches beneficiary on file", "Date is current and valid"]',
         'operations'),

        (case_id, 'Verify Claim Form Signatures', 'Verify all required signatures on the claim form', 1, 0,
         '["beneficiary_form", "id_front"]', '["beneficiary_name"]',
         '["Signature matches government ID", "Date of signature is valid", "Notarization present if required", "No alterations or corrections present"]',
         'operations'),

        # Stage 2: Account Records Verification - operations
        (case_id, 'Match Beneficiary to Account Records', 'Confirm claimant matches designated beneficiary on file', 2, 0,
         '[]', '["beneficiary_name", "beneficiary_ssn", "account_number", "deceased_name"]',
         '["Claimant is designated beneficiary", "No recent beneficiary changes (within 12 months)", "Percentage allocation confirmed if multiple beneficiaries", "Relationship to deceased validated"]',
         'operations'),

        (case_id, 'Review Beneficiary Designation History', 'Review complete beneficiary designation history for this account', 2, 0,
         '[]', '["account_number", "beneficiary_name"]',
         '["No conflicting designations exist", "All amendments properly authorized", "Primary/contingent beneficiaries clearly defined", "No per stirpes complications"]',
         'operations'),

        # Stage 3: Account & Tax Review - operations
        (case_id, 'Calculate Tax Withholding', 'Calculate required federal and state tax withholding', 3, 0,
         '[]', '["account_balance", "account_type", "beneficiary_name"]',
         '["Federal withholding calculated per IRS guidelines", "State withholding determined", "10-year rule vs spousal rollover eligibility documented", "Beneficiary tax election recorded"]',
         'operations'),

        (case_id, 'Review Account Standing', 'Verify account is in good standing with no restrictions', 3, 0,
         '[]', '["account_number", "account_balance"]',
         '["No liens or levies present", "No pending legal actions", "No compliance holds or restrictions", "No outstanding loans or advances"]',
         'operations'),

        (case_id, 'Verify Account Balance', 'Confirm current account balance and calculate distribution', 3, 0,
         '[]', '["account_balance", "account_number"]',
         '["Balance matches latest statement", "No pending transactions affecting value", "Valuation date documented", "Final distribution amount calculated with fees/withholding"]',
         'operations'),

        # Stage 4: Compliance & Approval - compliance
        (case_id, 'Final Compliance Review', 'Perform final regulatory compliance verification', 4, 0,
         '[]', '["account_type", "account_balance"]',
         '["IRS Form 1099-R requirements verified", "State escheatment compliance confirmed", "ERISA adherence validated if applicable", "All institutional policies satisfied"]',
         'compliance'),

        (case_id, 'AML/KYC Verification', 'Complete anti-money laundering and identity verification', 4, 0,
         '[]', '["beneficiary_name", "beneficiary_ssn"]',
         '["Beneficiary identity verified through multiple sources", "OFAC and sanctions list check completed", "No suspicious activity identified", "Source of funds documented if applicable"]',
         'compliance'),

        (case_id, 'Management Approval', 'Obtain required management approval for disbursement', 4, 0,
         '[]', '["account_balance", "beneficiary_name"]',
         '["All prior stages completed and verified", "Approval level appropriate for distribution amount", "Any special considerations documented", "Approval chain properly recorded"]',
         'manager'),

        # Stage 5: Disbursement - manager
        (case_id, 'Prepare Disbursement Authorization', 'Generate disbursement authorization documentation', 5, 0,
         '[]', '["account_balance", "beneficiary_name", "account_number"]',
         '["Death certificate details included", "Beneficiary verification confirmed", "Tax calculations documented", "All compliance approvals attached"]',
         'manager'),

        (case_id, 'Execute Payment', 'Process final payment to beneficiary', 5, 0,
         '[]', '["beneficiary_name", "account_balance"]',
         '["Payment method verified (direct deposit or check)", "Routing and account details confirmed if ACH", "Payment authorization signed", "Beneficiary confirmation generated"]',
         'manager')
    ]

    for task in tasks:
        cursor.execute('''
            INSERT INTO workflow_tasks (
                case_id, task_name, task_description, stage, completed,
                requires_documents, requires_data, verification_checks, assigned_role
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', task)

@app.route('/institution/case/<int:case_id>')
def case_detail(case_id):
    """Detailed case view - information only (clean version)"""
    if 'user_id' not in session:
        return redirect(url_for('institution_login'))

    conn = get_db()
    cursor = conn.cursor()

    # Get case
    case = cursor.execute('SELECT * FROM cases WHERE id = ?', (case_id,)).fetchone()

    # Get documents
    documents = cursor.execute('SELECT * FROM documents WHERE case_id = ?', (case_id,)).fetchall()

    # Get activity log
    activity = cursor.execute('''
        SELECT a.*, u.full_name as user_name
        FROM activity_log a
        LEFT JOIN users u ON a.user_id = u.id
        WHERE a.case_id = ?
        ORDER BY a.timestamp DESC
    ''', (case_id,)).fetchall()

    # Get task counts for workflow status box
    task_count_pending = cursor.execute('''
        SELECT COUNT(*) as count FROM workflow_tasks
        WHERE case_id = ? AND completed = 0
    ''', (case_id,)).fetchone()['count']

    task_count_completed = cursor.execute('''
        SELECT COUNT(*) as count FROM workflow_tasks
        WHERE case_id = ? AND completed = 1
    ''', (case_id,)).fetchone()['count']

    # Get tax calculation if it exists
    tax_calculation = tax_engine.get_calculation_for_case(case_id)

    conn.close()

    return render_template('case_detail_clean.html',
                         case=case,
                         documents=documents,
                         activity=activity,
                         task_count_pending=task_count_pending,
                         task_count_completed=task_count_completed,
                         tax_calculation=tax_calculation,
                         user_name=session.get('user_name'))

@app.route('/institution/case/<int:case_id>/upload-document', methods=['POST'])
def upload_document(case_id):
    """Upload documents to a case (for mail-in, fax, in-person submissions)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    import os
    from datetime import datetime
    from werkzeug.utils import secure_filename

    # Get form data
    document_type = request.form.get('document_type')
    file = request.files.get('file')

    if not file or not document_type:
        return jsonify({'error': 'File and document type required'}), 400

    # Save file
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_filename = f"{timestamp}_{filename}"
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'documents')
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, unique_filename)
    file.save(file_path)

    # Add document to database
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO documents (case_id, document_type, filename, upload_date)
        VALUES (?, ?, ?, ?)
    ''', (case_id, document_type, unique_filename, datetime.now().isoformat()))

    # Log activity
    cursor.execute('''
        INSERT INTO activity_log (case_id, user_id, action, details, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (case_id, session['user_id'], 'document_uploaded',
          f'Uploaded {document_type} document: {filename}', datetime.now().isoformat()))

    conn.commit()

    # Trigger auto-verification if this is a death certificate or ID
    if document_type in ['death_certificate', 'id_front', 'id_back']:
        run_verifications(case_id)

    conn.close()

    return jsonify({'success': True, 'message': 'Document uploaded successfully'})

def get_task_guidance(task_name, stage):
    """Return helpful guidance for each task type"""
    guidance_map = {
        # Stage 1: Beneficiary Claim Form Review
        'Review Beneficiary Claim Form': 'Review the beneficiary claim form for completeness and accuracy. Verify signature is present and legible, all required fields are completed, requested distribution method is clear, and form matches the beneficiary on file.',
        'Verify Claim Form Signatures': 'Verify all required signatures are present on the claim form. Ensure signatures match beneficiary ID and are properly dated. Check for notarization if required by account type.',

        # Stage 2: Account Records Verification
        'Match Beneficiary to Account Records': 'Confirm the claimant matches the designated beneficiary on file. Check beneficiary designation date, verify no recent amendments, confirm percentage allocation if multiple beneficiaries, and validate relationship to deceased.',
        'Review Beneficiary Designation History': 'Review complete history of beneficiary designations on this account. Check for any changes in the last 12 months, validate proper authorization for any amendments, and ensure no conflicting designations exist.',

        # Stage 3: Account & Tax Review
        'Calculate Tax Withholding': 'Calculate required federal and state tax withholding based on account type (IRA/401k), distribution amount, and beneficiary status. Determine if 10-year rule applies or if spousal rollover is elected. Document tax withholding election.',
        'Review Account Standing': 'Verify account has no liens, levies, or pending legal actions. Confirm account is in good standing with no compliance holds, overdrafts, or restrictions. Check for any outstanding loans or advances against the account.',
        'Verify Account Balance': 'Confirm current account balance and valuation date. Check for any pending transactions, recent deposits or withdrawals, and ensure balance matches latest statement. Calculate final distribution amount after fees and withholding.',

        # Stage 4: Compliance & Approval
        'Final Compliance Review': 'Perform final regulatory compliance check. Verify all IRS Form 1099-R requirements, state escheatment compliance, ERISA adherence (if applicable), and confirm all institutional policies are satisfied.',
        'AML/KYC Verification': 'Complete Anti-Money Laundering and Know Your Customer verification. Verify beneficiary identity through multiple sources, check against OFAC and sanctions lists, and document source of any large cash deposits.',
        'Management Approval': 'Obtain required management approval based on distribution amount. Ensure all prior stages are complete and verified. Document approval chain and any special considerations.',

        # Stage 5: Disbursement
        'Prepare Disbursement Authorization': 'Generate disbursement authorization with all verification confirmations. Include death certificate details, beneficiary verification, tax calculations, and compliance approvals. Prepare payment instructions.',
        'Execute Payment': 'Execute payment to beneficiary per their selected method. Verify routing and account details if direct deposit, or prepare check with proper payee information. Generate confirmation documentation for beneficiary.'
    }
    return guidance_map.get(task_name, 'Complete this task according to institutional procedures and regulatory requirements.')

@app.route('/institution/workflow/<int:case_id>')
def workflow_work_queue(case_id):
    """Smart context-aware workflow work queue for a specific case"""
    if 'user_id' not in session:
        return redirect(url_for('institution_login'))

    conn = get_db()
    cursor = conn.cursor()

    # Get case
    case = cursor.execute('SELECT * FROM cases WHERE id = ?', (case_id,)).fetchone()

    # Get workflow tasks with smart context
    tasks = cursor.execute('''
        SELECT t.*, u.full_name as completed_by_name
        FROM workflow_tasks t
        LEFT JOIN users u ON t.completed_by = u.id
        WHERE t.case_id = ?
        ORDER BY t.stage, t.id
    ''', (case_id,)).fetchall()

    # Get documents
    documents = cursor.execute('SELECT * FROM documents WHERE case_id = ?', (case_id,)).fetchall()

    # Parse smart task context (requires_documents, requires_data, verification_checks are JSON strings)
    import json
    tasks_with_context = []

    # Document type display names
    doc_type_names = {
        'death_certificate': 'Death Certificate',
        'id_front': 'ID (Front)',
        'id_back': 'ID (Back)',
        'beneficiary_form': 'Beneficiary Claim Form',
        'additional': 'Additional Documents'
    }

    for task in tasks:
        task_dict = dict(task)
        task_dict['requires_documents'] = json.loads(task['requires_documents']) if task['requires_documents'] else []
        task_dict['requires_data'] = json.loads(task['requires_data']) if task['requires_data'] else []
        task_dict['verification_checks'] = json.loads(task['verification_checks']) if task['verification_checks'] else []

        # Match documents to this task with friendly names
        task_dict['matched_documents'] = []
        for doc_type in task_dict['requires_documents']:
            for doc in documents:
                if doc['document_type'] == doc_type:
                    doc_dict = dict(doc)
                    doc_dict['display_name'] = doc_type_names.get(doc_type, doc_type.replace('_', ' ').title())
                    task_dict['matched_documents'].append(doc_dict)

        # Extract relevant case data with friendly display
        task_dict['relevant_data'] = {}
        field_names = {
            'deceased_name': 'Deceased Name',
            'deceased_ssn': 'Deceased SSN',
            'date_of_death': 'Date of Death',
            'beneficiary_name': 'Beneficiary Name',
            'beneficiary_ssn': 'Beneficiary SSN',
            'account_number': 'Account Number',
            'account_balance': 'Account Balance',
            'blockchain_hash': 'Blockchain Hash',
            'death_certificate_number': 'Death Certificate Number'
        }
        for field in task_dict['requires_data']:
            if field in case.keys():
                display_name = field_names.get(field, field.replace('_', ' ').title())
                value = case[field]

                # Format specific fields
                if field == 'account_balance':
                    value = f"${value:,.2f}"
                elif field == 'date_of_death':
                    value = str(value)[:10]

                task_dict['relevant_data'][display_name] = value

        # Add verification status indicators ONLY for relevant stages
        death_cert_score = case['death_cert_verification_score'] if case['death_cert_verification_score'] else 0
        all_verified = (death_cert_score >= 95 and case['id_verified'] and case['beneficiary_info_verified'])

        # Add helpful action guidance
        task_dict['action_guidance'] = get_task_guidance(task_dict['task_name'], task_dict['stage'])

        tasks_with_context.append(task_dict)

    # Build auto-verification summary (shown at case level, not per-task)
    # Convert case Row to dict to use .get()
    case_dict = dict(case)

    auto_verification_summary = {
        'death_cert': {
            'score': death_cert_score,
            'verified': death_cert_score >= 95,
            'type': case['death_cert_type'],
            'deceased_name': case['deceased_name'],
            'date_of_death': case['date_of_death'],
            'certificate_number': case['death_certificate_number'] if case['death_certificate_number'] else 'N/A',
            'recommendation': 'AUTO-VERIFIED' if death_cert_score >= 95 else 'REQUIRES MANUAL REVIEW' if death_cert_score >= 70 else 'FAILED VERIFICATION'
        },
        'id_verification': {
            'verified': case['id_verified'],
            'status': 'AUTO-VERIFIED' if case['id_verified'] else 'REQUIRES MANUAL REVIEW'
        },
        'beneficiary_info': {
            'verified': case['beneficiary_info_verified'],
            'beneficiary_name': case['beneficiary_name'],
            'beneficiary_ssn': case['beneficiary_ssn'][-4:] if case['beneficiary_ssn'] else 'N/A',  # Last 4 digits only
            'relationship': case_dict.get('beneficiary_relationship', 'N/A'),
            'status': 'AUTO-VERIFIED' if case['beneficiary_info_verified'] else 'REQUIRES MANUAL REVIEW'
        },
        'all_auto_verified': (death_cert_score >= 95 and case['id_verified'] and case['beneficiary_info_verified'])
    }

    # Get workflow stage names - redesigned for logical, non-redundant flow
    workflow_stages = {
        'IRA': ['Beneficiary Claim Form Review', 'Account Records Verification', 'Account & Tax Review', 'Compliance & Approval', 'Disbursement'],
        '401K': ['Beneficiary Claim Form Review', 'Account Records Verification', 'Plan & Tax Review', 'Compliance & Approval', 'Disbursement'],
        'TOD': ['Beneficiary Claim Form Review', 'TOD Records Verification', 'Account Review', 'Compliance & Approval', 'Transfer Execution'],
        'POD': ['Beneficiary Claim Form Review', 'POD Records Verification', 'Account Review', 'Compliance & Approval', 'Payment Processing'],
        'Trust': ['Beneficiary Claim Form Review', 'Trust Records Verification', 'Trust Review', 'Compliance & Approval', 'Distribution']
    }
    stages = workflow_stages.get(case['account_type'], workflow_stages['IRA'])

    conn.close()

    return render_template('workflow_work_queue.html',
                         case=case,
                         tasks=tasks_with_context,
                         workflow_stages=stages,
                         auto_verifications=auto_verification_summary,
                         enumerate=enumerate,
                         user_name=session.get('user_name'))

@app.route('/institution/verify-case/<int:case_id>', methods=['POST'])
def verify_case(case_id):
    """Trigger verification for a case"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    result = run_verifications(case_id)

    return jsonify(result)

@app.route('/institution/approve-case/<int:case_id>', methods=['POST'])
def approve_case(case_id):
    """Approve a case"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE cases
        SET status = ?, reviewed_by = ?, reviewed_at = ?
        WHERE id = ?
    ''', ('approved', session['user_id'], datetime.now(), case_id))

    cursor.execute('''
        INSERT INTO activity_log (case_id, user_id, action, details)
        VALUES (?, ?, ?, ?)
    ''', (case_id, session['user_id'], 'Case Approved', f'Approved by {session["user_name"]}'))

    conn.commit()
    conn.close()

    return jsonify({'status': 'approved'})

@app.route('/institution/reject-case/<int:case_id>', methods=['POST'])
def reject_case(case_id):
    """Reject a case"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE cases
        SET status = ?, reviewed_by = ?, reviewed_at = ?
        WHERE id = ?
    ''', ('rejected', session['user_id'], datetime.now(), case_id))

    cursor.execute('''
        INSERT INTO activity_log (case_id, user_id, action, details)
        VALUES (?, ?, ?, ?)
    ''', (case_id, session['user_id'], 'Case Rejected', f'Rejected by {session["user_name"]}'))

    conn.commit()
    conn.close()

    return jsonify({'status': 'rejected'})

@app.route('/view-document/<filename>')
def view_document(filename):
    """Serve document files"""
    file_path = os.path.join(os.path.dirname(__file__), '..', filename)
    if os.path.exists(file_path):
        return send_file(file_path)
    return "File not found", 404

@app.route('/institution/workflows')
def workflows():
    """Active work queue showing all pending tasks across all cases"""
    if 'user_id' not in session:
        return redirect(url_for('institution_login'))

    conn = get_db()
    cursor = conn.cursor()

    user_role = session.get('user_role')

    # Build query based on role permissions
    # Admin and Manager can see all tasks
    # Compliance sees compliance tasks
    # Operations sees operations tasks
    if user_role in ['admin', 'manager']:
        role_filter = ""
        params = []
    else:
        role_filter = "AND t.assigned_role = ?"
        params = [user_role]

    # Get all pending tasks (filtered by role)
    query = f'''
        SELECT
            t.*,
            c.case_number,
            c.account_type,
            c.account_balance,
            c.beneficiary_name,
            c.priority,
            c.status as case_status,
            u.full_name as completed_by_name
        FROM workflow_tasks t
        JOIN cases c ON t.case_id = c.id
        LEFT JOIN users u ON t.completed_by = u.id
        WHERE t.completed = 0 {role_filter}
        ORDER BY c.priority DESC, t.due_date ASC, t.stage ASC
    '''

    pending_tasks = cursor.execute(query, params).fetchall()

    # Get completed tasks for today (also filtered by role)
    from datetime import datetime, timedelta
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    completed_query = f'''
        SELECT
            t.*,
            c.case_number,
            c.account_type,
            u.full_name as completed_by_name
        FROM workflow_tasks t
        JOIN cases c ON t.case_id = c.id
        LEFT JOIN users u ON t.completed_by = u.id
        WHERE t.completed = 1 AND t.completed_at >= ? {role_filter}
        ORDER BY t.completed_at DESC
        LIMIT 10
    '''

    completed_params = [today_start] + params
    completed_today = cursor.execute(completed_query, completed_params).fetchall()

    # Get stats
    total_pending = len(pending_tasks)
    high_priority = len([t for t in pending_tasks if t['priority'] == 'high'])
    overdue = len([t for t in pending_tasks if t['due_date'] and datetime.fromisoformat(t['due_date']) < datetime.now()])

    conn.close()

    return render_template('workflows.html',
                         pending_tasks=pending_tasks,
                         completed_today=completed_today,
                         total_pending=total_pending,
                         high_priority=high_priority,
                         overdue=overdue,
                         user_name=session.get('user_name'),
                         user_role=user_role)

@app.route('/institution/reports')
def reports():
    """Reports and analytics page with real metrics"""
    if 'user_id' not in session:
        return redirect(url_for('institution_login'))

    conn = get_db()
    cursor = conn.cursor()

    # Get all cases
    cases = cursor.execute('SELECT * FROM cases').fetchall()

    # Calculate metrics
    from datetime import datetime, timedelta

    total_cases = len(cases)
    approved_cases = len([c for c in cases if c['status'] == 'approved'])
    rejected_cases = len([c for c in cases if c['status'] == 'rejected'])
    under_review = len([c for c in cases if c['status'] == 'under_review'])
    pending = len([c for c in cases if c['status'] == 'pending'])

    # Total value under management
    total_value = sum([c['account_balance'] for c in cases])

    # Processing time by account type
    processing_times = {}
    for case in cases:
        acc_type = case['account_type']
        if acc_type not in processing_times:
            processing_times[acc_type] = {'total_days': 0, 'count': 0, 'cases': []}

        # Calculate days since submission
        submission_date = datetime.fromisoformat(case['submission_date'])
        if case['reviewed_at']:
            review_date = datetime.fromisoformat(case['reviewed_at'])
            days = (review_date - submission_date).days
        else:
            # Still in progress
            days = (datetime.now() - submission_date).days

        processing_times[acc_type]['total_days'] += days
        processing_times[acc_type]['count'] += 1
        processing_times[acc_type]['cases'].append(days)

    # Calculate averages
    avg_processing_by_type = {}
    for acc_type, data in processing_times.items():
        avg_processing_by_type[acc_type] = {
            'avg_days': round(data['total_days'] / data['count'], 1) if data['count'] > 0 else 0,
            'case_count': data['count'],
            'fastest': min(data['cases']) if data['cases'] else 0,
            'slowest': max(data['cases']) if data['cases'] else 0
        }

    # Volume by account type
    volume_by_type = {}
    for case in cases:
        acc_type = case['account_type']
        if acc_type not in volume_by_type:
            volume_by_type[acc_type] = 0
        volume_by_type[acc_type] += 1

    # Value by account type
    value_by_type = {}
    for case in cases:
        acc_type = case['account_type']
        if acc_type not in value_by_type:
            value_by_type[acc_type] = 0
        value_by_type[acc_type] += case['account_balance']

    # Overall average processing time
    all_days = []
    for data in processing_times.values():
        all_days.extend(data['cases'])
    overall_avg = round(sum(all_days) / len(all_days), 1) if all_days else 0

    # Priority distribution
    high_priority = len([c for c in cases if c['priority'] == 'high'])
    medium_priority = len([c for c in cases if c['priority'] == 'medium'])
    low_priority = len([c for c in cases if c['priority'] == 'low'])

    # Task completion rate
    total_tasks = cursor.execute('SELECT COUNT(*) as count FROM workflow_tasks').fetchone()['count']
    completed_tasks = cursor.execute('SELECT COUNT(*) as count FROM workflow_tasks WHERE completed = 1').fetchone()['count']
    task_completion_rate = round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1)

    conn.close()

    report_data = {
        'total_cases': total_cases,
        'approved_cases': approved_cases,
        'rejected_cases': rejected_cases,
        'under_review': under_review,
        'pending': pending,
        'approval_rate': round((approved_cases / total_cases * 100) if total_cases > 0 else 0, 1),
        'total_value': total_value,
        'overall_avg_days': overall_avg,
        'avg_processing_by_type': avg_processing_by_type,
        'volume_by_type': volume_by_type,
        'value_by_type': value_by_type,
        'high_priority': high_priority,
        'medium_priority': medium_priority,
        'low_priority': low_priority,
        'task_completion_rate': task_completion_rate,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks
    }

    return render_template('reports.html', report_data=report_data, user_name=session.get('user_name'))

@app.route('/institution/settings')
def settings():
    """Settings and configuration page"""
    if 'user_id' not in session:
        return redirect(url_for('institution_login'))

    return render_template('settings.html', user_name=session.get('user_name'))

@app.route('/institution/toggle-task/<int:task_id>', methods=['POST'])
def toggle_task(task_id):
    """Toggle task completion status"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    data = request.get_json()
    completed = data.get('completed', False)

    conn = get_db()
    cursor = conn.cursor()

    if completed:
        cursor.execute('''
            UPDATE workflow_tasks
            SET completed = 1, completed_by = ?, completed_at = ?
            WHERE id = ?
        ''', (session['user_id'], datetime.now(), task_id))
    else:
        cursor.execute('''
            UPDATE workflow_tasks
            SET completed = 0, completed_by = NULL, completed_at = NULL
            WHERE id = ?
        ''', (task_id,))

    conn.commit()
    conn.close()

    return jsonify({'success': True})

@app.route('/institution/complete-stage/<int:case_id>', methods=['POST'])
def complete_stage(case_id):
    """Complete current stage and move to next"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    conn = get_db()
    cursor = conn.cursor()

    # Get current stage
    case = cursor.execute('SELECT workflow_stage FROM cases WHERE id = ?', (case_id,)).fetchone()
    current_stage = case['workflow_stage']
    next_stage = current_stage + 1

    # Update case workflow stage
    cursor.execute('''
        UPDATE cases
        SET workflow_stage = ?, status = 'under_review'
        WHERE id = ?
    ''', (next_stage, case_id))

    # Log activity
    cursor.execute('''
        INSERT INTO activity_log (case_id, user_id, action, details)
        VALUES (?, ?, ?, ?)
    ''', (case_id, session['user_id'], f'Stage {current_stage} Completed',
          f'Moved to stage {next_stage} by {session["user_name"]}'))

    conn.commit()
    conn.close()

    # Send notification about workflow milestone
    stage_names = {
        1: 'Claim Form Review',
        2: 'Record Verification',
        3: 'Account & Tax Review',
        4: 'Compliance & Approval',
        5: 'Disbursement Processing'
    }
    notifications.notify_workflow_milestone(case_id, next_stage, stage_names.get(next_stage, f'Stage {next_stage}'))

    return jsonify({'success': True, 'new_stage': next_stage})

@app.route('/institution/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect(url_for('institution_login'))

# =====================================
# RECONCILIATION & DEDUPLICATION
# =====================================

@app.route('/institution/api/check-duplicates', methods=['POST'])
def check_duplicates():
    """API endpoint to check for duplicate cases"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    case_data = request.json
    potential_duplicates = reconciliation.find_potential_duplicates(case_data)

    return jsonify({
        'duplicates_found': len(potential_duplicates),
        'duplicates': potential_duplicates
    })

@app.route('/institution/api/merge-cases', methods=['POST'])
def merge_cases():
    """Merge duplicate cases"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    data = request.json
    existing_case_id = data.get('existing_case_id')
    new_case_data = data.get('new_data')

    merge_result = reconciliation.merge_case_data(
        existing_case_id,
        new_case_data,
        session.get('user_id')
    )

    return jsonify(merge_result)

@app.route('/institution/reconciliation')
def reconciliation_dashboard():
    """Dashboard for managing duplicate cases and conflicts"""
    if 'user_id' not in session:
        return redirect(url_for('institution_login'))

    conn = get_db()
    cursor = conn.cursor()

    # Get all cases with duplicate markers
    duplicate_cases = cursor.execute('''
        SELECT
            c.*,
            a.details as duplicate_info,
            a.timestamp as detected_at
        FROM cases c
        JOIN activity_log a ON c.id = a.case_id
        WHERE a.action = 'duplicate_detected'
        ORDER BY a.timestamp DESC
    ''').fetchall()

    # Get unresolved conflicts
    unresolved_conflicts = reconciliation.get_unresolved_conflicts()

    conn.close()

    return render_template('reconciliation.html',
                         duplicate_cases=[dict(row) for row in duplicate_cases],
                         unresolved_conflicts=unresolved_conflicts,
                         user_name=session.get('user_name'),
                         user_role=session.get('user_role'))

@app.route('/institution/api/run-bulk-reconciliation', methods=['POST'])
def run_bulk_reconciliation():
    """Run bulk reconciliation across all cases"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    # Only admins and managers can run bulk reconciliation
    if session.get('user_role') not in ['admin', 'manager']:
        return jsonify({'error': 'Insufficient permissions'}), 403

    result = reconciliation.run_bulk_reconciliation()

    return jsonify(result)

# =====================================
# TAX WITHHOLDING CALCULATIONS
# =====================================

@app.route('/institution/api/calculate-tax/<int:case_id>', methods=['POST'])
def calculate_tax_withholding(case_id):
    """Calculate tax withholding for a case"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    conn = get_db()
    cursor = conn.cursor()

    # Get case details
    case = cursor.execute('SELECT * FROM cases WHERE id = ?', (case_id,)).fetchone()
    if not case:
        conn.close()
        return jsonify({'error': 'Case not found'}), 404

    conn.close()

    # Get optional parameters from request
    data = request.get_json() or {}

    # Parse beneficiary state from address (simplified)
    state = data.get('state', 'CA')  # Default to CA
    if case['beneficiary_address']:
        # Extract state from address (last 2 chars before zip)
        # In production, would use proper address parsing
        address_parts = case['beneficiary_address'].split(',')
        if len(address_parts) >= 2:
            state_zip = address_parts[-1].strip()
            state = state_zip.split()[0] if state_zip else 'CA'

    # Calculate beneficiary age (if DOB available)
    beneficiary_age = None
    if case['beneficiary_dob']:
        from datetime import datetime
        dob = datetime.fromisoformat(case['beneficiary_dob'])
        today = datetime.now()
        beneficiary_age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    # Calculate deceased age at death
    deceased_age_at_death = None
    if case['deceased_dob'] and case['date_of_death']:
        dob = datetime.fromisoformat(case['deceased_dob'])
        dod = datetime.fromisoformat(case['date_of_death'])
        deceased_age_at_death = dod.year - dob.year - ((dod.month, dod.day) < (dob.month, dob.day))

    # Perform calculation
    calculation = tax_engine.calculate_withholding(
        distribution_amount=case['account_balance'],
        account_type=case['account_type'],
        beneficiary_relationship=case['beneficiary_relationship'] or 'other',
        beneficiary_age=beneficiary_age,
        deceased_age_at_death=deceased_age_at_death,
        state=state,
        federal_withholding_election=data.get('federal_election'),
        state_withholding_election=data.get('state_election')
    )

    # Save calculation to database
    calc_id = tax_engine.save_calculation_to_case(case_id, calculation)
    calculation['calculation_id'] = calc_id

    # Log activity
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO activity_log (case_id, user_id, action, details)
        VALUES (?, ?, ?, ?)
    ''', (
        case_id,
        session.get('user_id'),
        'Tax Calculation',
        f'Calculated withholding: Federal ${calculation["federal_withholding"]["amount"]:,.2f}, '
        f'State ${calculation["state_withholding"]["amount"]:,.2f}, '
        f'Net: ${calculation["net_distribution"]:,.2f}'
    ))
    conn.commit()
    conn.close()

    return jsonify(calculation)

@app.route('/institution/case/<int:case_id>/tax-calculation')
def view_tax_calculation(case_id):
    """View tax calculation details for a case"""
    if 'user_id' not in session:
        return redirect(url_for('institution_login'))

    # Get case
    conn = get_db()
    cursor = conn.cursor()
    case = cursor.execute('SELECT * FROM cases WHERE id = ?', (case_id,)).fetchone()
    conn.close()

    if not case:
        return "Case not found", 404

    # Get existing calculation
    calculation = tax_engine.get_calculation_for_case(case_id)

    return render_template('tax_calculation.html',
                         case=dict(case),
                         calculation=calculation,
                         user_name=session.get('user_name'),
                         user_role=session.get('user_role'))

@app.route('/institution/api/10-year-rule/<int:case_id>')
def calculate_10_year_rule(case_id):
    """Calculate 10-year rule impact for a case"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    conn = get_db()
    cursor = conn.cursor()
    case = cursor.execute('SELECT * FROM cases WHERE id = ?', (case_id,)).fetchone()
    conn.close()

    if not case:
        return jsonify({'error': 'Case not found'}), 404

    # Calculate beneficiary age
    beneficiary_age = None
    if case['beneficiary_dob']:
        from datetime import datetime
        dob = datetime.fromisoformat(case['beneficiary_dob'])
        today = datetime.now()
        beneficiary_age = today.year - dob.year

    result = tax_engine.calculate_10_year_rule_impact(
        account_balance=case['account_balance'],
        beneficiary_relationship=case['beneficiary_relationship'] or 'other',
        beneficiary_age=beneficiary_age
    )

    return jsonify(result)

# =====================================
# PAYMENT PROCESSING
# =====================================

@app.route('/institution/api/validate-payment/<int:case_id>')
def validate_payment_eligibility(case_id):
    """Check if case is eligible for payment"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    validation = payment_system.validate_payment_eligibility(case_id)
    return jsonify(validation)

@app.route('/institution/api/initiate-payment/<int:case_id>', methods=['POST'])
def initiate_payment(case_id):
    """Initiate payment for a case"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    # Check permission
    if not has_permission('initiate_payment'):
        return jsonify({'error': 'Insufficient permissions to initiate payments'}), 403

    # Validate eligibility
    validation = payment_system.validate_payment_eligibility(case_id)
    if not validation['eligible']:
        return jsonify({
            'success': False,
            'error': 'Case not eligible for payment',
            'issues': validation['issues']
        }), 400

    # Get case and tax calculation
    conn = get_db()
    cursor = conn.cursor()
    case = cursor.execute('SELECT * FROM cases WHERE id = ?', (case_id,)).fetchone()
    conn.close()

    if not case:
        return jsonify({'error': 'Case not found'}), 404

    # Get tax calculation
    tax_calc = tax_engine.get_calculation_for_case(case_id)
    if not tax_calc:
        return jsonify({'error': 'Tax calculation required before payment'}), 400

    # Get payment details from request
    data = request.get_json() or {}
    payment_method = data.get('payment_method', 'ACH')

    # Initiate payment
    result = payment_system.initiate_payment(
        case_id=case_id,
        gross_amount=case['account_balance'],
        federal_withholding=tax_calc['federal_withholding']['amount'],
        state_withholding=tax_calc['state_withholding']['amount'],
        payment_method=payment_method,
        beneficiary_account_number=data.get('account_number'),
        beneficiary_routing_number=data.get('routing_number'),
        beneficiary_bank_name=data.get('bank_name'),
        initiated_by=session.get('user_id')
    )

    # Log activity
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO activity_log (case_id, user_id, action, details)
        VALUES (?, ?, ?, ?)
    ''', (
        case_id,
        session.get('user_id'),
        'Payment Initiated',
        f'Payment {result["payment_reference"]} initiated via {payment_method}. Net amount: ${result["net_amount"]:,.2f}'
    ))
    conn.commit()
    conn.close()

    # Send notification to beneficiary
    notifications.notify_payment_processed(
        case_id,
        result['net_amount'],
        payment_method
    )

    return jsonify(result)

@app.route('/institution/case/<int:case_id>/payment')
def case_payment_page(case_id):
    """Payment initiation page for a case"""
    if 'user_id' not in session:
        return redirect(url_for('institution_login'))

    # Check permission
    if not has_permission('initiate_payment'):
        return redirect(url_for('case_detail', case_id=case_id))

    conn = get_db()
    cursor = conn.cursor()

    case = cursor.execute('SELECT * FROM cases WHERE id = ?', (case_id,)).fetchone()
    if not case:
        conn.close()
        return "Case not found", 404

    # Get tax calculation
    tax_calc = tax_engine.get_calculation_for_case(case_id)

    # Get existing payments
    payments = payment_system.get_payments_for_case(case_id)

    # Validate eligibility
    validation = payment_system.validate_payment_eligibility(case_id)

    conn.close()

    return render_template('payment_initiation.html',
                         case=dict(case),
                         tax_calculation=tax_calc,
                         payments=payments,
                         validation=validation,
                         user_name=session.get('user_name'),
                         user_role=session.get('user_role'))

@app.route('/institution/payments/all')
def all_payments():
    """View all payments"""
    if 'user_id' not in session:
        return redirect(url_for('institution_login'))

    # Only managers and admins can view all payments
    if session.get('user_role') not in ['admin', 'manager']:
        return redirect(url_for('institution_dashboard'))

    stats = payment_system.get_payment_statistics()

    conn = get_db()
    cursor = conn.cursor()

    # Get all payments with case details
    all_payments = cursor.execute('''
        SELECT
            p.*,
            c.case_number,
            c.beneficiary_name,
            c.account_type,
            u.full_name as initiated_by_name
        FROM payments p
        JOIN cases c ON p.case_id = c.id
        LEFT JOIN users u ON p.initiated_by = u.id
        ORDER BY p.initiated_at DESC
    ''').fetchall()

    conn.close()

    return render_template('payments_dashboard.html',
                         payments=[dict(row) for row in all_payments],
                         stats=stats,
                         user_name=session.get('user_name'),
                         user_role=session.get('user_role'))

@app.route('/institution/redirect-to-bank-system/<payment_reference>')
def redirect_to_bank_system(payment_reference):
    """Redirect to bank's internal payment system"""
    if 'user_id' not in session:
        return redirect(url_for('institution_login'))

    payment = payment_system.get_payment_status(payment_reference)
    if not payment:
        return "Payment not found", 404

    # Update status to authorized
    payment_system.update_payment_status(payment_reference, 'authorized')

    # In production, this would redirect to actual bank system
    # For POC, show a placeholder page
    return render_template('bank_system_redirect.html',
                         payment=payment,
                         user_name=session.get('user_name'))

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🏦 Institution Portal Starting...")
    print("="*60)
    print("\n📍 Access Points:")
    print("   Institution Login:  http://localhost:5005/institution/login")
    print("   Institution Dashboard: http://localhost:5005/institution/dashboard")
    print("\n🔑 Demo Credentials:")
    print("   Email: admin@communitynationalbank.com")
    print("   Password: demo123")
    print("\n" + "="*60 + "\n")

    app.run(debug=True, port=5005)
