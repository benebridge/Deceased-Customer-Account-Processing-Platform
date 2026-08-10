from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file
from flask_cors import CORS
import sqlite3
from datetime import datetime
import os
from notification_service import get_notification_service

app = Flask(__name__)
app.secret_key = 'dev-secret-key-change-in-production'
CORS(app)

# Initialize notification service
notifications = get_notification_service()

# Database helper
def get_db():
    conn = sqlite3.connect('benebridge.db')
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
        # TODO: Call document verification API (Onfido, Jumio, etc.)
        # This checks: image quality, authenticity, tampering detection
        api_quality_score = 85  # Mock API response (0-100)
        api_points = int((api_quality_score / 100) * 40)
        score += api_points
        print(f"  📸 Document Quality API: {api_quality_score}/100 → {api_points}/40 points")

        # STEP 2: Rule-Based Validation (60 points max)
        rule_points = 0

        # Rule 1: Certificate number format (20 points)
        cert_number = case['death_certificate_number']
        if cert_number and len(cert_number) > 0:
            # Check format: YYYY-CA-XX-NNNNN (California format)
            if cert_number.startswith('2026-CA-'):
                rule_points += 20
                print(f"  ✅ Certificate number format valid: +20 points")
            else:
                rule_points += 10
                print(f"  ⚠️  Certificate number format unusual: +10 points")

        # Rule 2: Required fields present (20 points)
        # TODO: OCR extract fields from PDF and validate
        required_fields_present = True  # Mock for now
        if required_fields_present:
            rule_points += 20
            print(f"  ✅ Required fields present: +20 points")

        # Rule 3: Name matching (20 points)
        # TODO: OCR extract deceased name and compare to case data
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
    """
    Verifies blockchain hash with Titan Seal API

    TODO: Replace with actual Titan Seal API call when available
    Example:
    response = requests.post('https://api.titanseal.io/verify',
        json={'hash': blockchain_hash, 'certificate_type': 'death_certificate'},
        headers={'Authorization': f'Bearer {TITAN_SEAL_API_KEY}'}
    )
    return response.json()['verified']
    """
    # MOCK: Assume blockchain hash is valid for demo
    return True

def verify_id(case_id):
    """
    Verifies ID documents via third-party API

    TODO: Integrate with Onfido, Jumio, or similar ID verification service
    """
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
    """
    Verifies beneficiary information against bank's internal POD/TOD records

    TODO: Query bank's core banking system API
    """
    print(f"🏦 Verifying beneficiary info against bank records...")

    conn = get_db()
    cursor = conn.cursor()
    case = cursor.execute('SELECT * FROM cases WHERE id = ?', (case_id,)).fetchone()

    # MOCK: Check if beneficiary name matches POD designation in bank system
    # In production: query bank's API with account_number and deceased_name
    # Return: Does beneficiary_name match POD designation?
    info_matches = True

    cursor.execute('UPDATE cases SET beneficiary_info_verified = ? WHERE id = ?', (info_matches, case_id))
    conn.commit()
    conn.close()

    print(f"  ✅ Beneficiary info verified: {info_matches}")
    return info_matches

def run_verifications(case_id):
    """
    Orchestrates all verification checks and updates case status
    """
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

    new_status = 'pending'

    if death_cert_score == 100:  # Blockchain verified
        if id_verified and beneficiary_verified:
            new_status = 'under_review'  # All checks passed, ready for manual review
        else:
            new_status = 'pending'  # Blockchain good, but other checks failed
    elif death_cert_score >= 85:  # High confidence physical certificate
        if id_verified and beneficiary_verified:
            new_status = 'under_review'
        else:
            new_status = 'pending'
    elif death_cert_score >= 60:  # Medium confidence
        new_status = 'under_review'  # Manual review required
    else:  # Low confidence
        new_status = 'rejected'  # Automatic rejection

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
def beneficiary_portal():
    """Beneficiary portal - redirects to login if not authenticated"""
    if 'case_id' in session:
        return redirect(url_for('beneficiary_dashboard'))
    return redirect(url_for('beneficiary_login'))

@app.route('/login', methods=['GET', 'POST'])
def beneficiary_login():
    """Beneficiary login with case number + access code"""
    if request.method == 'POST':
        case_number = request.form.get('case_number', '').strip().upper()
        access_code = request.form.get('access_code', '').strip().upper()

        if not case_number or not access_code:
            return render_template('beneficiary_login.html', error='Please enter both case number and access code')

        conn = get_db()
        cursor = conn.cursor()

        # Verify credentials
        case = cursor.execute(
            'SELECT * FROM cases WHERE UPPER(case_number) = ? AND UPPER(access_code) = ?',
            (case_number, access_code)
        ).fetchone()

        conn.close()

        if case:
            # Successful login - create session
            session['case_id'] = case['id']
            session['case_number'] = case['case_number']
            session['beneficiary_name'] = case['beneficiary_name']
            return redirect(url_for('beneficiary_dashboard'))
        else:
            return render_template('beneficiary_login.html', error='Invalid case number or access code')

    return render_template('beneficiary_login.html')

@app.route('/logout')
def beneficiary_logout():
    """Logout beneficiary"""
    session.clear()
    return redirect(url_for('beneficiary_login'))

@app.route('/api/demo-credentials')
def demo_credentials():
    """Provide demo credentials for testing (development only)"""
    conn = get_db()
    cursor = conn.cursor()

    # Get the most recent case with an access code
    case = cursor.execute(
        'SELECT case_number, access_code FROM cases WHERE access_code IS NOT NULL ORDER BY id DESC LIMIT 1'
    ).fetchone()

    conn.close()

    if case:
        return jsonify({
            'case_number': case['case_number'],
            'access_code': case['access_code']
        })
    else:
        return jsonify({
            'case_number': 'No cases found',
            'access_code': 'N/A'
        })

@app.route('/dashboard')
def beneficiary_dashboard():
    """Beneficiary dashboard - shows their case status"""
    if 'case_id' not in session:
        return redirect(url_for('beneficiary_login'))

    conn = get_db()
    cursor = conn.cursor()

    # Get case details
    case = cursor.execute('SELECT * FROM cases WHERE id = ?', (session['case_id'],)).fetchone()

    # Get documents
    documents = cursor.execute('SELECT * FROM documents WHERE case_id = ?', (session['case_id'],)).fetchall()

    # Get notifications
    case_notifications = notifications.get_notifications_for_case(session['case_id'])
    unread_count = notifications.get_unread_count(session['case_id'])

    conn.close()

    return render_template('beneficiary_dashboard.html',
                         case=case,
                         documents=documents,
                         notifications=case_notifications,
                         unread_count=unread_count)

@app.route('/upload')
def beneficiary_upload_page():
    """Beneficiary upload page - redirects old route"""
    if 'case_id' not in session:
        return redirect(url_for('beneficiary_login'))
    return render_template('beneficiary_upload.html')

@app.route('/beneficiary/submit-case', methods=['POST'])
def submit_case():
    """Handle case submission from beneficiary portal"""
    # TODO: In production, handle actual file uploads
    # For now, this creates a new case in the database

    conn = get_db()
    cursor = conn.cursor()

    # For demo: get next case number
    last_case = cursor.execute('SELECT case_number FROM cases ORDER BY id DESC LIMIT 1').fetchone()
    if last_case:
        last_num = int(last_case['case_number'].split('-')[-1])
        new_case_number = f"SDC-2026-{str(last_num + 1).zfill(3)}"
    else:
        new_case_number = "SDC-2026-001"

    # Create new case (in production, this would come from form data)
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
        new_case_number,
        'Michael Motamed',
        'XXX-XX-1234',
        '2026-01-15',
        'Rosa Harms',
        'XXX-XX-5678',
        '0000 Meadow Street, Oakland, CA 00000',
        '(510) 555-0123',
        'rosa.harms@email.com',
        'IRA-2019-8821',
        'IRA',
        125000.00,
        'Community National Bank',
        'blockchain',
        'a3f5b8c2d1e9f7a4b3c8d2e1f9a7b5c3d4e6f8a1b2c3d4e5f6a7b8c9d0e1f2a3',
        '2026-CA-SU-00123',
        'pending',
        datetime.now()
    ))

    case_id = cursor.lastrowid

    # Add documents
    documents = [
        ('death_certificate', 'Michael-Motamed-DC.pdf'),
        ('id_front', 'California-Driving-License-Front.png'),
        ('id_back', 'California-Driving-License-Back.png'),
        ('beneficiary_form', 'Beneficiary-Claim-Form-IRA-After-2019-1.pdf')
    ]

    for doc_type, filename in documents:
        cursor.execute('''
            INSERT INTO documents (case_id, document_type, filename, file_path)
            VALUES (?, ?, ?, ?)
        ''', (case_id, doc_type, filename, filename))

    # Log submission
    cursor.execute('''
        INSERT INTO activity_log (case_id, action, details)
        VALUES (?, ?, ?)
    ''', (case_id, 'Case Submitted', f'Case {new_case_number} submitted by beneficiary Rosa Harms'))

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'case_id': case_id, 'case_number': new_case_number})

@app.route('/beneficiary/status')
def beneficiary_status():
    """Beneficiary-facing portal showing case status after submission"""
    conn = get_db()
    cursor = conn.cursor()

    # Get the most recent case (for demo)
    case = cursor.execute('SELECT * FROM cases ORDER BY id DESC LIMIT 1').fetchone()

    # If no case exists, redirect to home page
    if not case:
        conn.close()
        return redirect(url_for('beneficiary_portal'))

    # Get documents
    documents = cursor.execute('''
        SELECT * FROM documents WHERE case_id = ?
    ''', (case['id'],)).fetchall()

    conn.close()

    return render_template('beneficiary_status_tracker.html', case=case, documents=documents)

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
    """Institution dashboard showing all cases"""
    if 'user_id' not in session:
        return redirect(url_for('institution_login'))

    conn = get_db()
    cursor = conn.cursor()

    # Get all cases
    cases = cursor.execute('SELECT * FROM cases ORDER BY submission_date DESC').fetchall()

    # Get stats
    total_cases = len(cases)
    under_review = len([c for c in cases if c['status'] == 'under_review'])
    pending = len([c for c in cases if c['status'] == 'pending'])
    approved = len([c for c in cases if c['status'] == 'approved'])

    conn.close()

    return render_template('institution_dashboard.html',
                         cases=cases,
                         total_cases=total_cases,
                         under_review=under_review,
                         pending=pending,
                         approved=approved,
                         user_name=session.get('user_name'))

@app.route('/institution/case/<int:case_id>')
def case_detail(case_id):
    """Detailed case view"""
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

    conn.close()

    return render_template('case_detail.html',
                         case=case,
                         documents=documents,
                         activity=activity,
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
    file_path = os.path.join(os.getcwd(), filename)
    if os.path.exists(file_path):
        return send_file(file_path)
    return "File not found", 404

@app.route('/institution/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect(url_for('institution_login'))

# =====================================
# NOTIFICATION ENDPOINTS
# =====================================

@app.route('/api/notifications/mark-read/<int:notification_id>', methods=['POST'])
def mark_notification_read(notification_id):
    """Mark a notification as read"""
    if 'case_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    notifications.mark_as_read(notification_id)
    return jsonify({'success': True})

@app.route('/api/notifications/mark-all-read', methods=['POST'])
def mark_all_notifications_read():
    """Mark all notifications for current case as read"""
    if 'case_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    notifications.mark_all_as_read(session['case_id'])
    return jsonify({'success': True})

@app.route('/api/notifications/unread-count')
def get_unread_notification_count():
    """Get count of unread notifications"""
    if 'case_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    count = notifications.get_unread_count(session['case_id'])
    return jsonify({'count': count})

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🌉 BeneBridge POC Starting...")
    print("="*60)
    print("\n📍 Access Points:")
    print("   Beneficiary Portal: http://localhost:5004/")
    print("   Institution Login:  http://localhost:5004/institution/login")
    print("\n🔑 Demo Credentials:")
    print("   Email: admin@communitynationalbank.com")
    print("   Password: demo123")
    print("\n" + "="*60 + "\n")

    app.run(debug=True, port=5004)
