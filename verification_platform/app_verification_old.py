"""
BeneBridge Document Verification Platform
Simple upload and verify interface for death certificates and IDs
Runs on localhost:5008
"""

import os
import sys
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
from werkzeug.utils import secure_filename
import sqlite3
from datetime import datetime
import json
import hashlib
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add verification services to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'verification_services'))

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'death_certs'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'ids'), exist_ok=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db():
    """Get database connection"""
    conn = sqlite3.connect('verification_platform.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database"""
    conn = get_db()
    c = conn.cursor()

    # Verification sessions table
    c.execute('''CREATE TABLE IF NOT EXISTS verification_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        death_cert_uploaded BOOLEAN DEFAULT 0,
        id_uploaded BOOLEAN DEFAULT 0,
        blockchain_hash TEXT,
        status TEXT DEFAULT 'pending',
        results TEXT
    )''')

    # Uploaded documents table
    c.execute('''CREATE TABLE IF NOT EXISTS uploaded_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        document_type TEXT,
        filename TEXT,
        filepath TEXT,
        upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        file_hash TEXT,
        FOREIGN KEY (session_id) REFERENCES verification_sessions(session_id)
    )''')

    # Verification results table
    c.execute('''CREATE TABLE IF NOT EXISTS verification_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        document_type TEXT,
        verification_method TEXT,
        confidence_score REAL,
        status TEXT,
        details TEXT,
        verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES verification_sessions(session_id)
    )''')

    conn.commit()
    conn.close()

@app.route('/')
def index():
    """Main upload page"""
    return render_template('verification_upload.html')

@app.route('/create-session', methods=['POST'])
def create_session():
    """Create a new verification session"""
    session_id = hashlib.sha256(str(datetime.now()).encode()).hexdigest()[:16]

    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT INTO verification_sessions (session_id) VALUES (?)', (session_id,))
    conn.commit()
    conn.close()

    return jsonify({'session_id': session_id})

@app.route('/upload-death-cert', methods=['POST'])
def upload_death_cert():
    """Upload death certificate for verification"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    session_id = request.form.get('session_id')
    blockchain_hash = request.form.get('blockchain_hash', '')

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Allowed: PDF, PNG, JPG'}), 400

    # Save file
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{timestamp}_{filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'death_certs', filename)
    file.save(filepath)

    # Calculate file hash
    with open(filepath, 'rb') as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()

    # Update database
    conn = get_db()
    c = conn.cursor()

    c.execute('''INSERT INTO uploaded_documents
                 (session_id, document_type, filename, filepath, file_hash)
                 VALUES (?, ?, ?, ?, ?)''',
              (session_id, 'death_certificate', filename, filepath, file_hash))

    c.execute('''UPDATE verification_sessions
                 SET death_cert_uploaded = 1, blockchain_hash = ?
                 WHERE session_id = ?''',
              (blockchain_hash if blockchain_hash else None, session_id))

    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'filename': filename,
        'file_hash': file_hash,
        'message': 'Death certificate uploaded successfully'
    })

@app.route('/upload-id', methods=['POST'])
def upload_id():
    """Upload ID for verification"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    session_id = request.form.get('session_id')

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Allowed: PDF, PNG, JPG'}), 400

    # Save file
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{timestamp}_{filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'ids', filename)
    file.save(filepath)

    # Calculate file hash
    with open(filepath, 'rb') as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()

    # Update database
    conn = get_db()
    c = conn.cursor()

    c.execute('''INSERT INTO uploaded_documents
                 (session_id, document_type, filename, filepath, file_hash)
                 VALUES (?, ?, ?, ?, ?)''',
              (session_id, 'id_document', filename, filepath, file_hash))

    c.execute('''UPDATE verification_sessions
                 SET id_uploaded = 1
                 WHERE session_id = ?''',
              (session_id,))

    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'filename': filename,
        'file_hash': file_hash,
        'message': 'ID uploaded successfully'
    })

@app.route('/verify/<session_id>', methods=['POST'])
def run_verification(session_id):
    """Run verification on uploaded documents using Tesseract OCR (fallback) & Persona APIs"""
    try:
        from death_cert_verifier import verify_death_certificate_textract
        textract_available = True
    except:
        textract_available = False

    # Always import Tesseract fallback
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'verification_services', 'death_cert_verification'))
    from tesseract_verifier import verify_death_certificate_tesseract

    from id_verifier_persona import verify_id_document

    conn = get_db()
    c = conn.cursor()

    # Get uploaded documents
    c.execute('''SELECT * FROM uploaded_documents
                 WHERE session_id = ?''', (session_id,))
    documents = c.fetchall()

    print(f"\n{'='*80}")
    print(f"DEBUG: Found {len(documents)} uploaded documents for session {session_id}")
    for doc in documents:
        print(f"  - Document type: {doc['document_type']}, file: {doc['filename']}")
    print(f"{'='*80}\n")

    results = {
        'session_id': session_id,
        'death_cert_result': None,
        'id_result': None,
        'overall_status': 'pending'
    }

    # Verify death certificate with AWS Textract
    death_cert = next((d for d in documents if d['document_type'] == 'death_certificate'), None)
    print(f"DEBUG: death_cert object: {death_cert}")
    if death_cert:
        print(f"\n{'='*80}")
        print(f"DEBUG: Starting death certificate verification")
        print(f"File path: {death_cert['filepath']}")
        print(f"{'='*80}\n")
        try:
            # Try Textract first, fallback to Tesseract if unavailable
            ocr_result = None

            if textract_available:
                try:
                    print("DEBUG: Attempting AWS Textract verification...")
                    ocr_result = verify_death_certificate_textract(
                        file_path=death_cert['filepath'],
                        expected_deceased_name='Unknown',  # TODO: Get from form
                        expected_ssn=None,
                        expected_date_of_death=None
                    )
                    print(f"DEBUG: Textract result: {ocr_result.status.value}")
                except Exception as textract_error:
                    print(f"⚠️  Textract failed: {textract_error}")
                    print("DEBUG: Falling back to Tesseract OCR...")

            # Fallback to Tesseract if Textract failed or unavailable
            if ocr_result is None or ocr_result.status.value == 'failed':
                print("DEBUG: Using Tesseract OCR verification...")
                ocr_result = verify_death_certificate_tesseract(
                    file_path=death_cert['filepath'],
                    expected_deceased_name='Unknown',  # TODO: Get from form
                    expected_ssn=None,
                    expected_date_of_death=None
                )
                print(f"DEBUG: Tesseract result: {ocr_result.status.value}")

            death_cert_result = {
                'method': ocr_result.method.value,
                'confidence': ocr_result.confidence_score,
                'status': ocr_result.status.value,
                'details': ocr_result.details,
                'processing_time_ms': ocr_result.processing_time_ms
            }
            results['death_cert_result'] = death_cert_result

            # Store result
            c.execute('''INSERT INTO verification_results
                         (session_id, document_type, verification_method, confidence_score, status, details)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (session_id, 'death_certificate', death_cert_result['method'],
                       death_cert_result['confidence'], death_cert_result['status'],
                       json.dumps(death_cert_result['details'])))

        except Exception as e:
            import traceback
            error_details = {
                'error': str(e),
                'error_type': type(e).__name__,
                'traceback': traceback.format_exc()
            }
            print(f"\n{'='*80}")
            print(f"ERROR: Death certificate verification failed")
            print(f"{'='*80}")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print(f"Traceback:\n{traceback.format_exc()}")
            print(f"{'='*80}\n")

            results['death_cert_result'] = {
                'method': 'textract',
                'confidence': 0,
                'status': 'failed',
                'details': error_details,
                'processing_time_ms': 0
            }

    # Verify ID document with Persona (direct upload)
    id_doc = next((d for d in documents if d['document_type'] == 'id_document'), None)
    if id_doc:
        try:
            # Run direct Persona verification
            persona_result = verify_id_document(
                file_path=id_doc['filepath'],
                reference_id=session_id,
                expected_name=None,  # TODO: Get from form
                expected_dob=None
            )

            # Add error_message to details if present
            details_dict = persona_result.details.copy() if persona_result.details else {}
            if persona_result.error_message:
                details_dict['error'] = persona_result.error_message

            id_result = {
                'method': persona_result.method.value,
                'confidence': persona_result.confidence_score,
                'status': persona_result.status.value,
                'details': details_dict,
                'processing_time_ms': persona_result.processing_time_ms
            }
            results['id_result'] = id_result

            print(f"Persona verification result: {persona_result.status.value}, details: {details_dict}")

            # Store result
            c.execute('''INSERT INTO verification_results
                         (session_id, document_type, verification_method, confidence_score, status, details)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (session_id, 'id_document', 'persona_api',
                       id_result['confidence'], id_result['status'],
                       json.dumps(id_result['details'])))

        except Exception as e:
            results['id_result'] = {
                'method': 'persona',
                'confidence': 0,
                'status': 'failed',
                'details': {'error': str(e)},
                'processing_time_ms': 0
            }

    # Determine overall status
    if results['death_cert_result'] and results['id_result']:
        dc_status = results['death_cert_result']['status']
        id_status = results['id_result']['status']

        if dc_status == 'verified' and id_status == 'verified':
            results['overall_status'] = 'verified'
        elif dc_status == 'failed' or id_status == 'failed':
            results['overall_status'] = 'failed'
        else:
            results['overall_status'] = 'needs_review'
    elif results['death_cert_result']:
        results['overall_status'] = results['death_cert_result']['status']
    elif results['id_result']:
        results['overall_status'] = results['id_result']['status']

    # Update session
    c.execute('''UPDATE verification_sessions
                 SET status = ?, results = ?
                 WHERE session_id = ?''',
              (results['overall_status'], json.dumps(results), session_id))

    conn.commit()
    conn.close()

    return jsonify(results)

@app.route('/results/<session_id>')
def show_results(session_id):
    """Show verification results"""
    conn = get_db()
    c = conn.cursor()

    c.execute('SELECT * FROM verification_sessions WHERE session_id = ?', (session_id,))
    session = c.fetchone()

    if not session:
        return "Session not found", 404

    c.execute('''SELECT * FROM verification_results
                 WHERE session_id = ?
                 ORDER BY verified_at DESC''', (session_id,))
    results_raw = c.fetchall()

    conn.close()

    # Parse JSON details for each result
    results = []
    for result in results_raw:
        result_dict = dict(result)
        # Parse the details JSON string into a Python dict
        if result_dict.get('details'):
            try:
                result_dict['details'] = json.loads(result_dict['details'])
            except (json.JSONDecodeError, TypeError):
                result_dict['details'] = {}
        results.append(result_dict)

    return render_template('verification_results.html',
                         session=session,
                         results=results)

@app.route('/check-persona-status/<session_id>', methods=['POST'])
def check_persona_status(session_id):
    """Check Persona inquiry status and update results"""
    from id_verifier_persona import check_verification_status

    conn = get_db()
    c = conn.cursor()

    # Get the inquiry ID from the verification results
    c.execute('''SELECT details FROM verification_results
                 WHERE session_id = ? AND document_type = 'id_document'
                 ORDER BY id DESC LIMIT 1''', (session_id,))

    result = c.fetchone()
    if not result:
        return jsonify({'error': 'No ID verification found for this session'}), 404

    details = json.loads(result['details'])
    inquiry_id = details.get('inquiry_id')

    if not inquiry_id:
        return jsonify({'error': 'No inquiry ID found'}), 404

    # Check status with Persona
    persona_result = check_verification_status(inquiry_id)

    # Add error_message to details if present
    details_dict = persona_result.details.copy() if persona_result.details else {}
    if persona_result.error_message:
        details_dict['error'] = persona_result.error_message

    # Update the verification result in database
    c.execute('''UPDATE verification_results
                 SET status = ?, confidence_score = ?, details = ?, verified_at = CURRENT_TIMESTAMP
                 WHERE session_id = ? AND document_type = 'id_document' ''',
              (persona_result.status.value, persona_result.confidence_score,
               json.dumps(details_dict), session_id))

    # Update session status if verification completed
    if persona_result.status.value in ['verified', 'failed']:
        c.execute('''UPDATE verification_sessions
                     SET status = ? WHERE session_id = ?''',
                  (persona_result.status.value, session_id))

    conn.commit()
    conn.close()

    return jsonify({
        'status': persona_result.status.value,
        'confidence': persona_result.confidence_score,
        'message': 'Status updated successfully'
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'verification_platform'})

if __name__ == '__main__':
    print("=" * 80)
    print("BeneBridge Document Verification Platform")
    print("=" * 80)
    print("\nInitializing database...")
    init_db()
    print("✓ Database ready")
    print("\nStarting server on http://localhost:5008")
    print("\nFeatures:")
    print("  - Death Certificate Verification (OCR + Rules + AWS Textract)")
    print("  - ID Verification (Persona API)")
    print("  - Blockchain Hash Verification (Titan Seal)")
    print("  - Real-time Results Dashboard")
    print("=" * 80)

    app.run(host='0.0.0.0', port=5008, debug=True)
