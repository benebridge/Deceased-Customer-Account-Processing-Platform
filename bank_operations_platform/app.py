#!/usr/bin/env python3
"""
Bank Operations Platform - Beneficiary Claim Processing System
Localhost: 5009
"""

from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
import sqlite3
from pathlib import Path
from datetime import datetime
import json
import re

# Import Textract extraction functions
from textract_extraction import (
    extract_death_certificate_textract,
    extract_drivers_license_textract,
    extract_claim_form_textract
)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/tmp/bank_operations_uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

# Create upload directory
Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)

# Database paths
BASE_DIR = Path(__file__).parent.parent / "mock_databases"
DMF_DB = BASE_DIR / "dmf_mock.db"
BENEFICIARY_DB = BASE_DIR / "beneficiary_registry.db"
FINANCIAL_DB = BASE_DIR / "financial_accounts.db"
IDENTITY_DB = BASE_DIR / "identity_verification.db"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate_approval_doc', methods=['POST'])
def generate_approval_doc():
    """Generate and download approval document PDF"""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        import io

        # Get the verification results from request
        results = request.json

        # Create PDF in memory
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                              rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=18)

        # Container for elements
        elements = []

        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a73e8'),
            spaceAfter=30,
            alignment=TA_CENTER
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#1a73e8'),
            spaceAfter=12,
            spaceBefore=12
        )

        # Title
        elements.append(Paragraph("BENEFICIARY CLAIM APPROVAL DOCUMENT", title_style))
        elements.append(Paragraph("Community National Bank", styles['Heading3']))
        elements.append(Spacer(1, 0.3*inch))

        # Approval Status
        if results.get('final_approval'):
            status_text = '<font color="green"><b>✓ APPROVED FOR PROCESSING</b></font>'
        else:
            status_text = '<font color="orange"><b>⚠ REQUIRES MANUAL REVIEW</b></font>'

        elements.append(Paragraph(status_text, styles['Heading2']))
        elements.append(Spacer(1, 0.2*inch))

        # Timestamp
        timestamp = datetime.now().strftime('%B %d, %Y at %I:%M %p')
        elements.append(Paragraph(f"<b>Processing Date:</b> {timestamp}", styles['Normal']))
        elements.append(Paragraph(f"<b>Case ID:</b> {results.get('timestamp', 'N/A')}", styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))

        # Section 1: Extracted Information
        elements.append(Paragraph("1. EXTRACTED INFORMATION", heading_style))

        # Death Certificate Info
        if results.get('verification_methods', {}).get('death_certificate', {}).get('extracted_data'):
            dc_data = results['verification_methods']['death_certificate']['extracted_data']
            elements.append(Paragraph("<b>Death Certificate:</b>", styles['Heading4']))
            dc_info = [
                ['Deceased Name:', dc_data.get('deceased_name', 'N/A')],
                ['Date of Death:', dc_data.get('death_date', 'N/A')],
                ['SSN:', dc_data.get('ssn', 'N/A')]
            ]
            dc_table = Table(dc_info, colWidths=[2*inch, 4*inch])
            dc_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey)
            ]))
            elements.append(dc_table)
            elements.append(Spacer(1, 0.2*inch))

        # Driver's License Info
        if results.get('verification_methods', {}).get('drivers_license', {}).get('extracted_data'):
            dl_data = results['verification_methods']['drivers_license']['extracted_data']
            elements.append(Paragraph("<b>Beneficiary Driver's License:</b>", styles['Heading4']))
            dl_info = [
                ['Name:', dl_data.get('name', 'N/A')],
                ['DL Number:', dl_data.get('dl_number', 'N/A')],
                ['Date of Birth:', dl_data.get('dob', 'N/A')],
                ['Address:', dl_data.get('address', 'N/A')]
            ]
            dl_table = Table(dl_info, colWidths=[2*inch, 4*inch])
            dl_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey)
            ]))
            elements.append(dl_table)
            elements.append(Spacer(1, 0.2*inch))

        # Claim Form Info
        if results.get('verification_methods', {}).get('claim_form', {}).get('data'):
            claim_data = results['verification_methods']['claim_form']['data']
            elements.append(Paragraph("<b>Beneficiary Claim Form:</b>", styles['Heading4']))
            claim_info = [
                ['Deceased Name:', claim_data.get('deceased_name', 'N/A')],
                ['Account Number:', claim_data.get('account_number', 'N/A')],
                ['Beneficiary Name:', claim_data.get('beneficiary_name', 'N/A')],
                ['Beneficiary SSN:', claim_data.get('beneficiary_ssn', 'N/A')]
            ]
            claim_table = Table(claim_info, colWidths=[2*inch, 4*inch])
            claim_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey)
            ]))
            elements.append(claim_table)
            elements.append(Spacer(1, 0.3*inch))

        # Section 2: Verification Steps
        elements.append(Paragraph("2. VERIFICATION STEPS", heading_style))

        for step in results.get('steps', []):
            step_status = '✓' if step['status'] == 'success' else '⚠' if step['status'] == 'warning' else '•'
            step_color = 'green' if step['status'] == 'success' else 'orange' if step['status'] == 'warning' else 'black'

            step_text = f'<font color="{step_color}"><b>{step_status} Step {step["step"]}: {step["name"]}</b></font> - <i>{step["status"].upper()}</i>'
            elements.append(Paragraph(step_text, styles['Normal']))

        elements.append(Spacer(1, 0.3*inch))

        # Section 3: Cross-Verification Results
        if results.get('cross_verification'):
            elements.append(Paragraph("3. CROSS-DOCUMENT VERIFICATION", heading_style))

            cv = results['cross_verification']
            if cv.get('all_match'):
                elements.append(Paragraph('<font color="green"><b>✓ All documents match</b></font>', styles['Normal']))
            else:
                elements.append(Paragraph('<font color="orange"><b>⚠ Mismatches detected:</b></font>', styles['Normal']))
                for mismatch in cv.get('mismatches', []):
                    elements.append(Paragraph(f"  • {mismatch}", styles['Normal']))

            elements.append(Spacer(1, 0.3*inch))

        # Section 4: Database Verification
        if results.get('database_verification'):
            elements.append(Paragraph("4. DATABASE VERIFICATION", heading_style))

            db = results['database_verification']
            if db.get('verified'):
                elements.append(Paragraph('<font color="green"><b>✓ Beneficiary designation confirmed</b></font>', styles['Normal']))

                if db.get('beneficiary'):
                    bene = db['beneficiary']
                    elements.append(Paragraph(f"<b>Beneficiary Percentage:</b> {bene.get('percentage', 'N/A')}%", styles['Normal']))
                    elements.append(Paragraph(f"<b>Designation Type:</b> {bene.get('designation_type', 'N/A')}", styles['Normal']))
            else:
                elements.append(Paragraph('<font color="red"><b>✗ Database verification failed</b></font>', styles['Normal']))
                for error in db.get('errors', []):
                    elements.append(Paragraph(f"  • {error}", styles['Normal']))

            elements.append(Spacer(1, 0.3*inch))

        # Section 5: Payout Calculation
        if results.get('payout'):
            elements.append(Paragraph("5. PAYOUT CALCULATION", heading_style))

            payout = results['payout']
            payout_info = [
                ['Account Balance:', f"${payout.get('account_balance', 0):,.2f}"],
                ['Beneficiary Percentage:', f"{payout.get('beneficiary_percentage', 0)}%"],
                ['Account Type:', payout.get('account_type', 'N/A')],
                ['Routing Number:', payout.get('routing_number', 'N/A')],
                ['<b>TRANSFER AMOUNT:</b>', f"<b>${payout.get('payout_amount', 0):,.2f}</b>"]
            ]

            payout_table = Table(payout_info, colWidths=[3*inch, 3*inch])
            payout_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -2), colors.lightgrey),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#d4edda')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -2), 10),
                ('FONTSIZE', (0, -1), (-1, -1), 14),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey)
            ]))
            elements.append(payout_table)
            elements.append(Spacer(1, 0.3*inch))

        # Section 6: Issues (if any)
        if results.get('issues') and len(results['issues']) > 0:
            elements.append(Paragraph("6. ISSUES REQUIRING ATTENTION", heading_style))
            for issue in results['issues']:
                elements.append(Paragraph(f'<font color="orange">⚠ {issue}</font>', styles['Normal']))
            elements.append(Spacer(1, 0.3*inch))

        # Section 7: Audit Trail
        elements.append(Paragraph("7. AUDIT TRAIL", heading_style))

        if results.get('audit_trail'):
            audit = results['audit_trail']
            audit_info = [
                ['Processing Timestamp:', results.get('timestamp', 'N/A')],
                ['Processed By:', audit.get('processed_by', 'System')],
                ['Steps Completed:', str(audit.get('steps_completed', 0))],
                ['Verification Status:', audit.get('verification_status', 'N/A').upper()],
                ['Issues Found:', str(audit.get('issues_found', 0))]
            ]

            audit_table = Table(audit_info, colWidths=[2.5*inch, 3.5*inch])
            audit_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey)
            ]))
            elements.append(audit_table)

        elements.append(Spacer(1, 0.5*inch))

        # Footer
        elements.append(Paragraph("_" * 80, styles['Normal']))
        elements.append(Paragraph(
            "This document is computer-generated and constitutes official approval for beneficiary claim processing. "
            "Generated using AWS Textract Intelligent Document Processing.",
            styles['Normal']
        ))
        elements.append(Paragraph(
            f"Generated with Claude Code | Community National Bank | {timestamp}",
            ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
        ))

        # Build PDF
        doc.build(elements)

        # Get PDF from buffer
        buffer.seek(0)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        # Return PDF as download
        from flask import make_response
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=Claim_Approval_{results.get("timestamp", "document")}.pdf'

        return response

    except Exception as e:
        print(f"Error generating approval document: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/process_claim', methods=['POST'])
def process_claim():
    """
    Process uploaded documents:
    - Death Certificate
    - Driver's License (ID)
    - Beneficiary Claim Form
    """

    try:
        # Check if all files are present
        if 'death_cert' not in request.files or 'drivers_license' not in request.files or 'claim_form' not in request.files:
            return jsonify({'error': 'Missing required documents'}), 400

        death_cert = request.files['death_cert']
        drivers_license = request.files['drivers_license']
        claim_form = request.files['claim_form']

        # Check if files were actually selected
        if death_cert.filename == '' or drivers_license.filename == '' or claim_form.filename == '':
            return jsonify({'error': 'No files selected'}), 400

        # Save uploaded files
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        death_cert_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{timestamp}_death_cert_{secure_filename(death_cert.filename)}')
        dl_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{timestamp}_dl_{secure_filename(drivers_license.filename)}')
        claim_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{timestamp}_claim_{secure_filename(claim_form.filename)}')

        print(f"Saving files:")
        print(f"  Death Cert: {death_cert_path}")
        print(f"  DL: {dl_path}")
        print(f"  Claim Form: {claim_path}")

        death_cert.save(death_cert_path)
        drivers_license.save(dl_path)
        claim_form.save(claim_path)

    except Exception as e:
        print(f"Error saving files: {str(e)}")
        return jsonify({'error': f'Error saving files: {str(e)}'}), 500

    # Initialize verification results
    results = {
        'timestamp': timestamp,
        'status': 'processing',
        'steps': [],
        'issues': [],
        'verification_methods': {},
        'final_approval': False
    }

    # Step 1: Verify Death Certificate
    results['steps'].append({'step': 1, 'name': 'Death Certificate Verification', 'status': 'processing'})
    death_cert_result = verify_death_certificate(death_cert_path)
    results['verification_methods']['death_certificate'] = death_cert_result

    if death_cert_result['verified']:
        results['steps'][-1]['status'] = 'success'
        results['steps'][-1]['data'] = death_cert_result['extracted_data']
    else:
        results['steps'][-1]['status'] = 'warning'
        results['issues'].append(f"Death Certificate: {death_cert_result.get('error', 'Could not verify')}")

    # Step 2: Verify Driver's License (ID)
    results['steps'].append({'step': 2, 'name': 'Identity Verification (Driver\'s License)', 'status': 'processing'})
    dl_result = verify_drivers_license(dl_path)
    results['verification_methods']['drivers_license'] = dl_result

    if dl_result['verified']:
        results['steps'][-1]['status'] = 'success'
        results['steps'][-1]['data'] = dl_result['extracted_data']
    else:
        results['steps'][-1]['status'] = 'warning'
        results['issues'].append(f"Driver's License: {dl_result.get('error', 'Could not verify')}")

    # Step 3: Extract Claim Form Data
    results['steps'].append({'step': 3, 'name': 'Beneficiary Claim Form Processing', 'status': 'processing'})
    claim_result = extract_claim_form_data(claim_path)
    results['verification_methods']['claim_form'] = claim_result

    if claim_result['extracted']:
        results['steps'][-1]['status'] = 'success'
        results['steps'][-1]['data'] = claim_result['data']
    else:
        results['steps'][-1]['status'] = 'warning'
        results['issues'].append(f"Claim Form: {claim_result.get('error', 'Could not extract data')}")

    # Step 4: Cross-Verification
    results['steps'].append({'step': 4, 'name': 'Cross-Document Verification', 'status': 'processing'})
    cross_verify_result = cross_verify_documents(
        death_cert_result.get('extracted_data', {}),
        dl_result.get('extracted_data', {}),
        claim_result.get('data', {})
    )
    results['cross_verification'] = cross_verify_result

    if cross_verify_result['all_match']:
        results['steps'][-1]['status'] = 'success'
    else:
        results['steps'][-1]['status'] = 'warning'
        results['issues'].extend(cross_verify_result.get('mismatches', []))

    # Step 5: Database Verification
    results['steps'].append({'step': 5, 'name': 'Database Verification', 'status': 'processing'})
    db_result = verify_against_databases(claim_result.get('data', {}))
    results['database_verification'] = db_result

    if db_result['verified']:
        results['steps'][-1]['status'] = 'success'
        results['steps'][-1]['data'] = db_result
    else:
        results['steps'][-1]['status'] = 'warning'
        results['issues'].extend(db_result.get('errors', []))

    # Step 6: Calculate Payout
    if db_result.get('verified') and len(results['issues']) == 0:
        results['steps'].append({'step': 6, 'name': 'Payout Calculation', 'status': 'processing'})
        payout_result = calculate_payout(db_result)
        results['payout'] = payout_result
        results['steps'][-1]['status'] = 'success'
        results['steps'][-1]['data'] = payout_result
        results['final_approval'] = True
        results['status'] = 'approved'
    else:
        results['status'] = 'requires_review'
        results['final_approval'] = False

    # Generate audit trail
    results['audit_trail'] = generate_audit_trail(results)

    return jsonify(results)

def verify_death_certificate(file_path):
    """Verify death certificate using AWS Textract"""
    return extract_death_certificate_textract(file_path)

def verify_drivers_license(file_path):
    """Verify driver's license using AWS Textract AnalyzeID"""
    return extract_drivers_license_textract(file_path)

def extract_claim_form_data(file_path):
    """Extract data from claim form using AWS Textract"""
    return extract_claim_form_textract(file_path)

def cross_verify_documents(death_cert_data, dl_data, claim_data):
    """Cross-verify data across all three documents"""
    mismatches = []

    # Check if deceased names match (case-insensitive)
    deceased_cert = (death_cert_data.get('deceased_name') or '').lower().strip()
    deceased_claim = (claim_data.get('deceased_name') or '').lower().strip()

    if deceased_cert and deceased_claim and deceased_cert != deceased_claim:
        mismatches.append(f'Deceased name mismatch: Death cert "{death_cert_data.get("deceased_name")}" vs Claim form "{claim_data.get("deceased_name")}"')

    # Check if beneficiary names match (case-insensitive)
    bene_dl = (dl_data.get('name') or '').lower().strip()
    bene_claim = (claim_data.get('beneficiary_name') or '').lower().strip()

    if bene_dl and bene_claim and bene_dl != bene_claim:
        mismatches.append(f'Beneficiary name mismatch: ID "{dl_data.get("name")}" vs Claim form "{claim_data.get("beneficiary_name")}"')

    return {
        'all_match': len(mismatches) == 0,
        'mismatches': mismatches
    }

def verify_against_databases(claim_data):
    """Verify claim against internal databases"""
    try:
        account_number = claim_data.get('account_number')
        beneficiary_name = claim_data.get('beneficiary_name')

        # Query databases
        conn_fin = sqlite3.connect(FINANCIAL_DB)
        conn_fin.row_factory = sqlite3.Row
        c_fin = conn_fin.cursor()

        # Find account
        c_fin.execute("SELECT * FROM accounts WHERE account_number = ?", (account_number,))
        account = c_fin.fetchone()

        if not account:
            return {
                'verified': False,
                'errors': [f'Account {account_number} not found in system']
            }

        account_id = account['account_id']

        conn_fin.close()

        # Find beneficiary designation
        conn_ben = sqlite3.connect(BENEFICIARY_DB)
        conn_ben.row_factory = sqlite3.Row
        c_ben = conn_ben.cursor()

        c_ben.execute("""
            SELECT b.*, bd.percentage, bd.designation_type
            FROM beneficiaries b
            JOIN beneficiary_designations bd ON b.beneficiary_id = bd.beneficiary_id
            WHERE bd.account_id = ? AND b.full_name = ?
        """, (account_id, beneficiary_name))

        beneficiary = c_ben.fetchone()
        conn_ben.close()

        if not beneficiary:
            return {
                'verified': False,
                'errors': [f'Beneficiary {beneficiary_name} not designated for account {account_number}']
            }

        return {
            'verified': True,
            'account': dict(account),
            'beneficiary': dict(beneficiary)
        }

    except Exception as e:
        return {
            'verified': False,
            'errors': [f'Database error: {str(e)}']
        }

def calculate_payout(db_result):
    """Calculate payout amounts"""
    account = db_result['account']
    beneficiary = db_result['beneficiary']

    balance = account['balance']
    percentage = beneficiary['percentage']
    payout_amount = balance * (percentage / 100)

    return {
        'account_balance': balance,
        'beneficiary_percentage': percentage,
        'payout_amount': payout_amount,
        'routing_number': account['routing_number'],
        'account_type': account['account_type']
    }

def generate_audit_trail(results):
    """Generate detailed audit trail"""
    return {
        'timestamp': results['timestamp'],
        'processed_by': 'System',
        'steps_completed': len(results['steps']),
        'verification_status': results['status'],
        'issues_found': len(results['issues'])
    }

if __name__ == '__main__':
    print("=" * 80)
    print("BANK OPERATIONS PLATFORM - BENEFICIARY CLAIM PROCESSING")
    print("=" * 80)
    print()
    print("Starting server on http://localhost:5009")
    print()
    app.run(host='0.0.0.0', port=5009, debug=True)
