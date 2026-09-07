#!/usr/bin/env python3
"""
BeneBridge Platform - Test Results Data Extraction

Extracts comprehensive test data from CRM database for dissertation Results chapter
Includes workflow transitions, verification scores, approvals, and audit trails

Usage:
    python3 extract_test_results.py
"""

import sqlite3
import json
import csv
from datetime import datetime
from collections import defaultdict

# Database path
CRM_DB = "/Users/danallen/Library/Mobile Documents/com~apple~CloudDocs/MCA_Bridge/BeneBridgePOC/crm_platform/crm.db"

# Test case IDs from automated test run
TEST_CASE_IDS = [
    'DC-20260818-160040',  # Scenario 1: Simple POD
    'DC-20260818-160055',  # Scenario 2: Joint Account
    'DC-20260818-160110',  # Scenario 3: IRA Multi-Beneficiary
    'DC-20260818-160125',  # Scenario 4: Large Estate
    'DC-20260818-160140',  # Scenario 5: Standard Verification
    'DC-20260818-160155',  # Scenario 6: Name Discrepancy
    'DC-20260818-160210',  # Scenario 7: Fraud Detection
    'DC-20260818-160224',  # Scenario 8: Probate Required
]

SCENARIO_NAMES = {
    'DC-20260818-160040': 'Scenario 1: Simple POD - Auto Approval',
    'DC-20260818-160055': 'Scenario 2: Joint Account - Supervisor Approval',
    'DC-20260818-160110': 'Scenario 3: IRA Multi-Beneficiary - Manual Review',
    'DC-20260818-160125': 'Scenario 4: Large Estate - Manager Approval',
    'DC-20260818-160140': 'Scenario 5: Standard Verification - Ribbon Verify',
    'DC-20260818-160155': 'Scenario 6: Name Discrepancy - Manual Override',
    'DC-20260818-160210': 'Scenario 7: Fraud Detection - Investigation',
    'DC-20260818-160224': 'Scenario 8: Probate Required - Beneficiary Dispute',
}


def connect_db():
    """Connect to CRM database"""
    conn = sqlite3.connect(CRM_DB)
    conn.row_factory = sqlite3.Row
    return conn


def extract_workflow_transitions():
    """Extract workflow state transitions for all test cases"""
    conn = connect_db()
    c = conn.cursor()

    transitions_data = {}

    for case_id in TEST_CASE_IDS:
        c.execute('''
            SELECT case_id, from_state, to_state, changed_at, changed_by, notes
            FROM workflow_history
            WHERE case_id = ?
            ORDER BY changed_at ASC
        ''', (case_id,))

        transitions = []
        for row in c.fetchall():
            transitions.append({
                'case_id': row['case_id'],
                'from_state': row['from_state'],
                'to_state': row['to_state'],
                'timestamp': row['changed_at'],
                'changed_by': row['changed_by'],
                'notes': row['notes']
            })

        transitions_data[case_id] = transitions

    conn.close()
    return transitions_data


def extract_document_verification():
    """Extract document verification details including IDP confidence scores"""
    conn = connect_db()
    c = conn.cursor()

    verification_data = {}

    for case_id in TEST_CASE_IDS:
        # Check if document_verification table exists
        c.execute('''
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='document_verification'
        ''')

        if not c.fetchone():
            verification_data[case_id] = {
                'note': 'document_verification table not yet created',
                'extracted_fields': {}
            }
            continue

        c.execute('''
            SELECT document_type, verification_data, verification_status,
                   verification_date, confidence_score
            FROM document_verification
            WHERE case_id = ?
            ORDER BY verification_date ASC
        ''', (case_id,))

        docs = []
        for row in c.fetchall():
            doc_data = {
                'document_type': row['document_type'],
                'status': row['verification_status'],
                'verification_date': row['verification_date'],
                'confidence_score': row['confidence_score']
            }

            # Parse verification_data JSON if available
            if row['verification_data']:
                try:
                    verification_json = json.loads(row['verification_data'])
                    doc_data['extracted_fields'] = verification_json
                except:
                    pass

            docs.append(doc_data)

        verification_data[case_id] = docs

    conn.close()
    return verification_data


def extract_approvals():
    """Extract approval workflow details"""
    conn = connect_db()
    c = conn.cursor()

    approvals_data = {}

    for case_id in TEST_CASE_IDS:
        c.execute('''
            SELECT approval_tier, requested_by, requested_at,
                   approved_by, approved_at, approval_status,
                   approval_notes, denial_reason
            FROM approvals
            WHERE case_id = ?
            ORDER BY requested_at ASC
        ''', (case_id,))

        approvals = []
        for row in c.fetchall():
            approval_duration = None
            if row['approved_at'] and row['requested_at']:
                try:
                    requested = datetime.fromisoformat(row['requested_at'])
                    approved = datetime.fromisoformat(row['approved_at'])
                    approval_duration = (approved - requested).total_seconds()
                except:
                    pass

            approvals.append({
                'approval_tier': row['approval_tier'],
                'requested_by': row['requested_by'],
                'requested_at': row['requested_at'],
                'approved_by': row['approved_by'],
                'approved_at': row['approved_at'],
                'status': row['approval_status'],
                'approval_duration_seconds': approval_duration,
                'notes': row['approval_notes'],
                'denial_reason': row['denial_reason']
            })

        approvals_data[case_id] = approvals

    conn.close()
    return approvals_data


def extract_manual_overrides():
    """Extract manual override data"""
    conn = connect_db()
    c = conn.cursor()

    overrides_data = {}

    for case_id in TEST_CASE_IDS:
        c.execute('''
            SELECT override_type, field_name, original_value, new_value,
                   justification, overridden_by, overridden_at
            FROM manual_overrides
            WHERE case_id = ?
            ORDER BY overridden_at ASC
        ''', (case_id,))

        overrides = []
        for row in c.fetchall():
            overrides.append({
                'override_type': row['override_type'],
                'field_name': row['field_name'],
                'original_value': row['original_value'],
                'new_value': row['new_value'],
                'justification': row['justification'],
                'overridden_by': row['overridden_by'],
                'overridden_at': row['overridden_at']
            })

        overrides_data[case_id] = overrides

    conn.close()
    return overrides_data


def extract_ai_communications():
    """Extract sample AI-generated communications"""
    conn = connect_db()
    c = conn.cursor()

    # Check if communications table exists
    c.execute('''
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='communications'
    ''')

    if not c.fetchone():
        conn.close()
        return {'note': 'communications table not yet created'}

    communications_data = {}

    # Get 2 sample communications (first and one fraud case)
    sample_cases = [TEST_CASE_IDS[0], TEST_CASE_IDS[6]]  # Scenario 1 and 7

    for case_id in sample_cases:
        c.execute('''
            SELECT communication_type, subject, body, generated_at,
                   sent_at, recipient_email, template_used
            FROM communications
            WHERE case_id = ?
            ORDER BY generated_at DESC
            LIMIT 2
        ''', (case_id,))

        comms = []
        for row in c.fetchall():
            comms.append({
                'type': row['communication_type'],
                'subject': row['subject'],
                'body': row['body'],
                'generated_at': row['generated_at'],
                'sent_at': row['sent_at'],
                'recipient': row['recipient_email'],
                'template': row['template_used'],
                'character_count': len(row['body']) if row['body'] else 0
            })

        communications_data[case_id] = comms

    conn.close()
    return communications_data


def extract_audit_events():
    """Extract audit event counts per case"""
    conn = connect_db()
    c = conn.cursor()

    # Check if audit_log table exists
    c.execute('''
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='audit_log'
    ''')

    if not c.fetchone():
        conn.close()
        return {'note': 'audit_log table not yet created'}

    audit_data = {}

    for case_id in TEST_CASE_IDS:
        c.execute('''
            SELECT event_type, COUNT(*) as count
            FROM audit_log
            WHERE case_id = ?
            GROUP BY event_type
        ''', (case_id,))

        events = {}
        total_events = 0
        for row in c.fetchall():
            events[row['event_type']] = row['count']
            total_events += row['count']

        audit_data[case_id] = {
            'total_events': total_events,
            'events_by_type': events
        }

    conn.close()
    return audit_data


def extract_case_summary():
    """Extract case summary information"""
    conn = connect_db()
    c = conn.cursor()

    case_summaries = {}

    for case_id in TEST_CASE_IDS:
        c.execute('''
            SELECT case_id, deceased_name, primary_beneficiary_name,
                   workflow_status, total_claim_amount, priority,
                   created_date, updated_date
            FROM workflow_cases
            WHERE case_id = ?
        ''', (case_id,))

        row = c.fetchone()
        if row:
            # Calculate processing time
            processing_time = None
            if row['created_date'] and row['updated_date']:
                try:
                    created = datetime.fromisoformat(row['created_date'])
                    updated = datetime.fromisoformat(row['updated_date'])
                    processing_time = (updated - created).total_seconds()
                except:
                    pass

            case_summaries[case_id] = {
                'case_id': row['case_id'],
                'deceased_name': row['deceased_name'],
                'beneficiary_name': row['primary_beneficiary_name'],
                'final_status': row['workflow_status'],
                'claim_amount': row['total_claim_amount'],
                'priority': row['priority'],
                'created_date': row['created_date'],
                'updated_date': row['updated_date'],
                'processing_time_seconds': processing_time
            }

    conn.close()
    return case_summaries


def generate_reports(all_data):
    """Generate comprehensive reports"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # =========================================================================
    # Export complete data to JSON
    # =========================================================================
    json_filename = f"comprehensive_test_results_{timestamp}.json"
    with open(json_filename, 'w') as f:
        json.dump(all_data, f, indent=2)

    print(f"\n✅ Exported complete data: {json_filename}")

    # =========================================================================
    # Generate CSV: Workflow Transitions
    # =========================================================================
    csv_filename = f"workflow_transitions_{timestamp}.csv"
    with open(csv_filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Case ID', 'Scenario', 'From State', 'To State', 'Timestamp', 'Changed By', 'Notes'])

        for case_id, transitions in all_data['workflow_transitions'].items():
            for t in transitions:
                writer.writerow([
                    case_id,
                    SCENARIO_NAMES.get(case_id, case_id),
                    t['from_state'],
                    t['to_state'],
                    t['timestamp'],
                    t['changed_by'],
                    t['notes']
                ])

    print(f"✅ Exported workflow transitions: {csv_filename}")

    # =========================================================================
    # Generate CSV: Approvals
    # =========================================================================
    csv_filename = f"approvals_{timestamp}.csv"
    with open(csv_filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Case ID', 'Scenario', 'Approval Tier', 'Status',
            'Requested At', 'Approved At', 'Duration (seconds)',
            'Approved By', 'Notes'
        ])

        for case_id, approvals in all_data['approvals'].items():
            for a in approvals:
                writer.writerow([
                    case_id,
                    SCENARIO_NAMES.get(case_id, case_id),
                    a['approval_tier'],
                    a['status'],
                    a['requested_at'],
                    a['approved_at'],
                    a['approval_duration_seconds'],
                    a['approved_by'],
                    a['notes']
                ])

    print(f"✅ Exported approvals: {csv_filename}")

    # =========================================================================
    # Generate CSV: Manual Overrides
    # =========================================================================
    csv_filename = f"manual_overrides_{timestamp}.csv"
    with open(csv_filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Case ID', 'Scenario', 'Override Type', 'Field',
            'Original Value', 'New Value', 'Justification',
            'Overridden By', 'Timestamp'
        ])

        for case_id, overrides in all_data['manual_overrides'].items():
            for o in overrides:
                writer.writerow([
                    case_id,
                    SCENARIO_NAMES.get(case_id, case_id),
                    o['override_type'],
                    o['field_name'],
                    o['original_value'],
                    o['new_value'],
                    o['justification'],
                    o['overridden_by'],
                    o['overridden_at']
                ])

    print(f"✅ Exported manual overrides: {csv_filename}")

    # =========================================================================
    # Generate Markdown Summary Report
    # =========================================================================
    md_filename = f"dissertation_results_data_{timestamp}.md"
    with open(md_filename, 'w') as f:
        f.write("# BeneBridge Platform - Comprehensive Test Results\n\n")
        f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Test Cases**: {len(TEST_CASE_IDS)}\n\n")

        f.write("---\n\n")

        # Case Summaries
        f.write("## Case Summaries\n\n")
        f.write("| Case ID | Scenario | Final Status | Claim Amount | Processing Time |\n")
        f.write("|---------|----------|--------------|--------------|------------------|\n")

        for case_id, summary in all_data['case_summaries'].items():
            proc_time = f"{summary['processing_time_seconds']:.2f}s" if summary['processing_time_seconds'] else 'N/A'
            f.write(f"| {case_id} | {SCENARIO_NAMES.get(case_id, 'Unknown')} | {summary['final_status']} | ${summary['claim_amount']:,.2f} | {proc_time} |\n")

        f.write("\n---\n\n")

        # Workflow Transitions Summary
        f.write("## Workflow Transition Counts\n\n")
        f.write("| Case ID | Scenario | Total Transitions |\n")
        f.write("|---------|----------|-------------------|\n")

        for case_id, transitions in all_data['workflow_transitions'].items():
            f.write(f"| {case_id} | {SCENARIO_NAMES.get(case_id, 'Unknown')} | {len(transitions)} |\n")

        f.write("\n---\n\n")

        # Approval Summary
        f.write("## Approval Workflow Summary\n\n")
        f.write("| Case ID | Scenario | Approvals Required | Average Duration |\n")
        f.write("|---------|----------|-------------------|------------------|\n")

        for case_id, approvals in all_data['approvals'].items():
            if approvals:
                durations = [a['approval_duration_seconds'] for a in approvals if a['approval_duration_seconds']]
                avg_duration = sum(durations) / len(durations) if durations else 0
                f.write(f"| {case_id} | {SCENARIO_NAMES.get(case_id, 'Unknown')} | {len(approvals)} | {avg_duration:.2f}s |\n")
            else:
                f.write(f"| {case_id} | {SCENARIO_NAMES.get(case_id, 'Unknown')} | 0 | N/A |\n")

        f.write("\n---\n\n")

        # Manual Overrides Summary
        f.write("## Manual Override Summary\n\n")

        total_overrides = sum(len(overrides) for overrides in all_data['manual_overrides'].values())

        if total_overrides > 0:
            f.write("| Case ID | Scenario | Override Count | Override Types |\n")
            f.write("|---------|----------|----------------|----------------|\n")

            for case_id, overrides in all_data['manual_overrides'].items():
                if overrides:
                    override_types = set(o['override_type'] for o in overrides)
                    f.write(f"| {case_id} | {SCENARIO_NAMES.get(case_id, 'Unknown')} | {len(overrides)} | {', '.join(override_types)} |\n")
        else:
            f.write("No manual overrides were recorded during test execution.\n")

        f.write("\n---\n\n")

        # AI Communications Sample
        if 'ai_communications' in all_data and isinstance(all_data['ai_communications'], dict):
            f.write("## Sample AI-Generated Communications\n\n")

            for case_id, comms in all_data['ai_communications'].items():
                if comms:
                    f.write(f"### {SCENARIO_NAMES.get(case_id, case_id)}\n\n")
                    for comm in comms:
                        f.write(f"**Type**: {comm['type']}\n")
                        f.write(f"**Subject**: {comm['subject']}\n")
                        f.write(f"**Character Count**: {comm['character_count']}\n")
                        f.write(f"**Generated**: {comm['generated_at']}\n\n")
                        f.write("```\n")
                        f.write(comm['body'][:500] if comm['body'] else 'N/A')
                        if comm['body'] and len(comm['body']) > 500:
                            f.write("...\n")
                        f.write("\n```\n\n")

        f.write("---\n\n")

        # Audit Event Summary
        if 'audit_events' in all_data and isinstance(all_data['audit_events'], dict):
            f.write("## Audit Event Summary\n\n")
            f.write("| Case ID | Scenario | Total Events |\n")
            f.write("|---------|----------|-------------|\n")

            for case_id, audit in all_data['audit_events'].items():
                if isinstance(audit, dict):
                    f.write(f"| {case_id} | {SCENARIO_NAMES.get(case_id, 'Unknown')} | {audit.get('total_events', 0)} |\n")

    print(f"✅ Exported markdown report: {md_filename}")


def main():
    """Main execution"""
    print("=" * 80)
    print("BENEBRIDGE - COMPREHENSIVE TEST RESULTS EXTRACTION")
    print("=" * 80)
    print(f"\nExtracting data for {len(TEST_CASE_IDS)} test cases...")
    print(f"Database: {CRM_DB}\n")

    all_data = {}

    # Priority 1: Critical for Chapter 5
    print("📊 Extracting workflow transitions...")
    all_data['workflow_transitions'] = extract_workflow_transitions()
    print(f"   ✓ Found transitions for {len([k for k,v in all_data['workflow_transitions'].items() if v])} cases")

    print("📊 Extracting document verification data...")
    all_data['document_verification'] = extract_document_verification()
    print(f"   ✓ Extracted verification data")

    print("📊 Extracting approval data...")
    all_data['approvals'] = extract_approvals()
    print(f"   ✓ Found approvals for {len([k for k,v in all_data['approvals'].items() if v])} cases")

    # Priority 2: Nice to Have
    print("📊 Extracting manual overrides...")
    all_data['manual_overrides'] = extract_manual_overrides()
    override_count = sum(len(v) for v in all_data['manual_overrides'].values())
    print(f"   ✓ Found {override_count} manual overrides")

    print("📊 Extracting AI communications...")
    all_data['ai_communications'] = extract_ai_communications()
    print(f"   ✓ Extracted sample communications")

    print("📊 Extracting audit events...")
    all_data['audit_events'] = extract_audit_events()
    print(f"   ✓ Extracted audit event data")

    # Case summaries
    print("📊 Extracting case summaries...")
    all_data['case_summaries'] = extract_case_summary()
    print(f"   ✓ Extracted {len(all_data['case_summaries'])} case summaries")

    # Generate reports
    print("\n📝 Generating reports...")
    generate_reports(all_data)

    print("\n" + "=" * 80)
    print("✅ DATA EXTRACTION COMPLETE!")
    print("=" * 80)
    print("\nFiles ready for dissertation Results chapter:")
    print("  - comprehensive_test_results_*.json (complete data)")
    print("  - workflow_transitions_*.csv (for tables)")
    print("  - approvals_*.csv (for approval analysis)")
    print("  - manual_overrides_*.csv (for override analysis)")
    print("  - dissertation_results_data_*.md (formatted summary)")
    print()


if __name__ == '__main__':
    main()
