#!/usr/bin/env python3
"""
BeneBridge Platform - Test Metrics Collection Script

Monitors CRM database in real-time during test scenario execution
Collects comprehensive metrics for dissertation Results chapter

Usage:
    python3 collect_test_metrics.py

Monitors:
    - workflow_cases: Case creation and updates
    - workflow_history: State transitions
    - manual_overrides: Manual interventions
    - approvals: Approval workflow metrics
    - document_verification: Verification results (if available)

Outputs:
    - Real-time console display
    - CSV export: test_results_TIMESTAMP.csv
    - JSON export: test_results_TIMESTAMP.json
    - Markdown summary: test_summary_TIMESTAMP.md
"""

import sqlite3
import time
import json
import csv
from datetime import datetime, timedelta
from collections import defaultdict
import os

# Database path
DB_PATH = '/Users/danallen/Library/Mobile Documents/com~apple~CloudDocs/MCA_Bridge/BeneBridgePOC/crm_platform/crm.db'

# Global metrics storage
metrics = {
    'cases': {},  # case_id -> case metrics
    'scenarios': [],  # List of scenario names being tested
    'start_time': None,
    'end_time': None
}

# Track last seen records to detect new ones
last_seen = {
    'cases': set(),
    'history': set(),
    'overrides': set(),
    'approvals': set()
}


def clear_screen():
    """Clear console screen"""
    os.system('clear' if os.name != 'nt' else 'cls')


def connect_db():
    """Connect to CRM database"""
    if not os.path.exists(DB_PATH):
        print(f"❌ ERROR: Database not found at {DB_PATH}")
        return None

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def format_duration(seconds):
    """Format seconds into human-readable duration"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.2f}h"


def calculate_automation_rate(case_metrics):
    """Calculate percentage of automated actions"""
    total_actions = case_metrics.get('total_actions', 0)
    manual_actions = case_metrics.get('manual_interventions', 0)

    if total_actions == 0:
        return 0.0

    automated = total_actions - manual_actions
    return (automated / total_actions) * 100


def poll_database():
    """Poll database for new records and updates"""
    conn = connect_db()
    if not conn:
        return False

    try:
        c = conn.cursor()

        # =====================================================================
        # POLL: workflow_cases table
        # =====================================================================
        c.execute('''
            SELECT case_id, deceased_name, workflow_status, total_claim_amount,
                   created_date, updated_date, primary_beneficiary_name
            FROM workflow_cases
            ORDER BY created_date DESC
        ''')

        cases = c.fetchall()

        for case in cases:
            case_id = case['case_id']

            # New case detected
            if case_id not in last_seen['cases']:
                last_seen['cases'].add(case_id)

                # Initialize case metrics
                metrics['cases'][case_id] = {
                    'case_id': case_id,
                    'deceased_name': case['deceased_name'],
                    'beneficiary_name': case['primary_beneficiary_name'],
                    'claim_amount': case['total_claim_amount'] or 0.0,
                    'created_at': case['created_date'],
                    'current_status': case['workflow_status'],
                    'state_history': [],
                    'state_durations': {},
                    'manual_interventions': 0,
                    'manual_overrides': [],
                    'approvals': [],
                    'total_actions': 0,
                    'verification_time': None,
                    'processing_complete': False,
                    'final_state': None,
                    'total_processing_time': None
                }

                print(f"\n🆕 NEW CASE DETECTED: {case_id}")
                print(f"   Deceased: {case['deceased_name']}")
                print(f"   Claim Amount: ${case['total_claim_amount'] or 0:,.2f}")
                print(f"   Initial Status: {case['workflow_status']}")

            # Update current status
            else:
                old_status = metrics['cases'][case_id]['current_status']
                new_status = case['workflow_status']

                if old_status != new_status:
                    metrics['cases'][case_id]['current_status'] = new_status
                    print(f"\n📊 STATUS UPDATE: {case_id}")
                    print(f"   {old_status} → {new_status}")

        # =====================================================================
        # POLL: workflow_history table
        # =====================================================================
        c.execute('''
            SELECT id, case_id, from_state, to_state, changed_at, changed_by
            FROM workflow_history
            ORDER BY changed_at ASC
        ''')

        history = c.fetchall()

        for record in history:
            record_id = record['id']
            case_id = record['case_id']

            if record_id not in last_seen['history'] and case_id in metrics['cases']:
                last_seen['history'].add(record_id)

                # Add to state history
                transition = {
                    'from_state': record['from_state'],
                    'to_state': record['to_state'],
                    'timestamp': record['changed_at'],
                    'changed_by': record['changed_by']
                }
                metrics['cases'][case_id]['state_history'].append(transition)
                metrics['cases'][case_id]['total_actions'] += 1

                print(f"   State Transition: {record['from_state']} → {record['to_state']}")

        # Calculate state durations
        for case_id, case_data in metrics['cases'].items():
            if len(case_data['state_history']) > 0:
                for i, transition in enumerate(case_data['state_history']):
                    state = transition['to_state']
                    start_time = datetime.fromisoformat(transition['timestamp'])

                    # Calculate duration until next transition or now
                    if i + 1 < len(case_data['state_history']):
                        end_time = datetime.fromisoformat(case_data['state_history'][i + 1]['timestamp'])
                    else:
                        end_time = datetime.now()

                    duration = (end_time - start_time).total_seconds()

                    if state not in case_data['state_durations']:
                        case_data['state_durations'][state] = 0
                    case_data['state_durations'][state] += duration

        # =====================================================================
        # POLL: manual_overrides table
        # =====================================================================
        c.execute('''
            SELECT id, case_id, override_type, justification, overridden_by, overridden_at
            FROM manual_overrides
            ORDER BY overridden_at ASC
        ''')

        overrides = c.fetchall()

        for override in overrides:
            override_id = override['id']
            case_id = override['case_id']

            if override_id not in last_seen['overrides'] and case_id in metrics['cases']:
                last_seen['overrides'].add(override_id)

                override_data = {
                    'type': override['override_type'],
                    'justification': override['justification'],
                    'overridden_by': override['overridden_by'],
                    'timestamp': override['overridden_at']
                }

                metrics['cases'][case_id]['manual_overrides'].append(override_data)
                metrics['cases'][case_id]['manual_interventions'] += 1
                metrics['cases'][case_id]['total_actions'] += 1

                print(f"\n⚠️  MANUAL OVERRIDE DETECTED: {case_id}")
                print(f"   Type: {override['override_type']}")
                print(f"   By: {override['overridden_by']}")

        # =====================================================================
        # POLL: approvals table
        # =====================================================================
        c.execute('''
            SELECT id, case_id, approval_tier, requested_by, requested_at,
                   approved_by, approved_at, approval_status
            FROM approvals
            ORDER BY requested_at ASC
        ''')

        approvals = c.fetchall()

        for approval in approvals:
            approval_id = approval['id']
            case_id = approval['case_id']

            if approval_id not in last_seen['approvals'] and case_id in metrics['cases']:
                last_seen['approvals'].add(approval_id)

                # Calculate approval duration if approved
                approval_duration = None
                if approval['approved_at'] and approval['requested_at']:
                    requested = datetime.fromisoformat(approval['requested_at'])
                    approved = datetime.fromisoformat(approval['approved_at'])
                    approval_duration = (approved - requested).total_seconds()

                approval_data = {
                    'tier': approval['approval_tier'],
                    'requested_by': approval['requested_by'],
                    'requested_at': approval['requested_at'],
                    'approved_by': approval['approved_by'],
                    'approved_at': approval['approved_at'],
                    'status': approval['approval_status'],
                    'duration_seconds': approval_duration
                }

                metrics['cases'][case_id]['approvals'].append(approval_data)
                metrics['cases'][case_id]['total_actions'] += 1

                print(f"\n✅ APPROVAL ACTIVITY: {case_id}")
                print(f"   Tier: {approval['approval_tier']}")
                print(f"   Status: {approval['approval_status']}")
                if approval_duration:
                    print(f"   Duration: {format_duration(approval_duration)}")

        # =====================================================================
        # Calculate total processing time for each case
        # =====================================================================
        for case_id, case_data in metrics['cases'].items():
            if case_data['created_at']:
                created = datetime.fromisoformat(case_data['created_at'])

                # Check if case is in terminal state
                terminal_states = ['APPROVED', 'DENIED', 'CLOSED', 'FRAUD_INVESTIGATION', 'ON_HOLD']
                if case_data['current_status'] in terminal_states:
                    # Use last state transition time or now
                    if len(case_data['state_history']) > 0:
                        last_transition = datetime.fromisoformat(case_data['state_history'][-1]['timestamp'])
                    else:
                        last_transition = datetime.now()

                    total_time = (last_transition - created).total_seconds()
                    case_data['total_processing_time'] = total_time
                    case_data['processing_complete'] = True
                    case_data['final_state'] = case_data['current_status']

        conn.close()
        return True

    except Exception as e:
        print(f"\n❌ ERROR polling database: {e}")
        conn.close()
        return False


def display_live_metrics():
    """Display live metrics in console"""
    clear_screen()

    print("=" * 80)
    print("🔴 BENEBRIDGE PLATFORM - LIVE METRICS COLLECTION")
    print("=" * 80)
    print(f"Monitoring: {DB_PATH}")
    print(f"Active Cases: {len(metrics['cases'])}")
    print(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    if len(metrics['cases']) == 0:
        print("\n📋 No cases detected yet. Waiting for activity...")
        print("\n💡 TIP: Create a new case in the CRM dashboard to begin testing.")
        return

    # Display each case
    for case_id, case_data in metrics['cases'].items():
        print(f"\n{'─' * 80}")
        print(f"📁 CASE: {case_id}")
        print(f"{'─' * 80}")
        print(f"Deceased: {case_data['deceased_name']}")
        print(f"Beneficiary: {case_data['beneficiary_name'] or 'N/A'}")
        print(f"Claim Amount: ${case_data['claim_amount']:,.2f}")
        print(f"Current Status: {case_data['current_status']}")

        if case_data['processing_complete']:
            print(f"✅ Processing Complete: {case_data['final_state']}")
            print(f"⏱️  Total Time: {format_duration(case_data['total_processing_time'])}")

        # State transitions
        if len(case_data['state_history']) > 0:
            print(f"\n📊 State Transitions ({len(case_data['state_history'])}):")
            for transition in case_data['state_history'][-5:]:  # Last 5
                print(f"   {transition['from_state']} → {transition['to_state']}")

        # Manual interventions
        if case_data['manual_interventions'] > 0:
            print(f"\n⚠️  Manual Interventions: {case_data['manual_interventions']}")
            for override in case_data['manual_overrides'][-3:]:  # Last 3
                print(f"   Type: {override['type']}")

        # Approvals
        if len(case_data['approvals']) > 0:
            print(f"\n✅ Approvals ({len(case_data['approvals'])}):")
            for approval in case_data['approvals']:
                duration_str = f" ({format_duration(approval['duration_seconds'])})" if approval['duration_seconds'] else ""
                print(f"   {approval['tier']}: {approval['status']}{duration_str}")

        # Automation rate
        if case_data['total_actions'] > 0:
            auto_rate = calculate_automation_rate(case_data)
            print(f"\n🤖 Automation Rate: {auto_rate:.1f}%")
            print(f"   Total Actions: {case_data['total_actions']}")
            print(f"   Manual Actions: {case_data['manual_interventions']}")

    print("\n" + "=" * 80)
    print("Press Ctrl+C to stop monitoring and export results")
    print("=" * 80)


def export_results():
    """Export metrics to CSV, JSON, and Markdown"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # =========================================================================
    # Export to JSON (complete data)
    # =========================================================================
    json_filename = f"test_results_{timestamp}.json"
    with open(json_filename, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"\n✅ Exported JSON: {json_filename}")

    # =========================================================================
    # Export to CSV (summary data)
    # =========================================================================
    csv_filename = f"test_results_{timestamp}.csv"
    with open(csv_filename, 'w', newline='') as f:
        writer = csv.writer(f)

        # Header
        writer.writerow([
            'Case ID',
            'Deceased Name',
            'Beneficiary Name',
            'Claim Amount',
            'Final Status',
            'Processing Complete',
            'Total Processing Time (seconds)',
            'State Transitions',
            'Manual Interventions',
            'Manual Overrides',
            'Approvals',
            'Automation Rate (%)',
            'Created At'
        ])

        # Data rows
        for case_id, case_data in metrics['cases'].items():
            writer.writerow([
                case_id,
                case_data['deceased_name'],
                case_data['beneficiary_name'] or 'N/A',
                case_data['claim_amount'],
                case_data['current_status'],
                case_data['processing_complete'],
                case_data['total_processing_time'] or 'N/A',
                len(case_data['state_history']),
                case_data['manual_interventions'],
                len(case_data['manual_overrides']),
                len(case_data['approvals']),
                f"{calculate_automation_rate(case_data):.1f}",
                case_data['created_at']
            ])

    print(f"✅ Exported CSV: {csv_filename}")

    # =========================================================================
    # Export to Markdown (formatted summary)
    # =========================================================================
    md_filename = f"test_summary_{timestamp}.md"
    with open(md_filename, 'w') as f:
        f.write("# BeneBridge Platform - Test Results Summary\n\n")
        f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Total Cases Tested**: {len(metrics['cases'])}\n\n")

        f.write("---\n\n")

        # Summary table
        f.write("## Summary Table\n\n")
        f.write("| Case ID | Deceased | Claim Amount | Status | Processing Time | Automation Rate |\n")
        f.write("|---------|----------|--------------|--------|-----------------|------------------|\n")

        for case_id, case_data in metrics['cases'].items():
            proc_time = format_duration(case_data['total_processing_time']) if case_data['total_processing_time'] else 'N/A'
            auto_rate = f"{calculate_automation_rate(case_data):.1f}%"

            f.write(f"| {case_id} | {case_data['deceased_name']} | ${case_data['claim_amount']:,.2f} | {case_data['current_status']} | {proc_time} | {auto_rate} |\n")

        f.write("\n---\n\n")

        # Detailed case reports
        f.write("## Detailed Case Reports\n\n")

        for case_id, case_data in metrics['cases'].items():
            f.write(f"### {case_id}: {case_data['deceased_name']}\n\n")
            f.write(f"**Beneficiary**: {case_data['beneficiary_name'] or 'N/A'}\n")
            f.write(f"**Claim Amount**: ${case_data['claim_amount']:,.2f}\n")
            f.write(f"**Final Status**: {case_data['current_status']}\n")

            if case_data['total_processing_time']:
                f.write(f"**Total Processing Time**: {format_duration(case_data['total_processing_time'])}\n")

            f.write(f"**Automation Rate**: {calculate_automation_rate(case_data):.1f}%\n\n")

            # State transitions
            if len(case_data['state_history']) > 0:
                f.write(f"**State Transitions** ({len(case_data['state_history'])}):\n")
                for transition in case_data['state_history']:
                    f.write(f"- {transition['from_state']} → {transition['to_state']}\n")
                f.write("\n")

            # Manual overrides
            if len(case_data['manual_overrides']) > 0:
                f.write(f"**Manual Overrides** ({len(case_data['manual_overrides'])}):\n")
                for override in case_data['manual_overrides']:
                    f.write(f"- Type: {override['type']}\n")
                    f.write(f"  Justification: {override['justification']}\n")
                f.write("\n")

            # Approvals
            if len(case_data['approvals']) > 0:
                f.write(f"**Approvals** ({len(case_data['approvals'])}):\n")
                for approval in case_data['approvals']:
                    duration = f" (Duration: {format_duration(approval['duration_seconds'])})" if approval['duration_seconds'] else ""
                    f.write(f"- {approval['tier']}: {approval['status']}{duration}\n")
                f.write("\n")

            f.write("---\n\n")

    print(f"✅ Exported Markdown: {md_filename}")
    print("\n" + "=" * 80)
    print("📊 All results exported successfully!")
    print("=" * 80)


def main():
    """Main monitoring loop"""
    print("=" * 80)
    print("🚀 BENEBRIDGE METRICS COLLECTION SCRIPT")
    print("=" * 80)
    print(f"Database: {DB_PATH}")
    print("\nStarting real-time monitoring...")
    print("Press Ctrl+C to stop and export results\n")

    metrics['start_time'] = datetime.now().isoformat()

    try:
        while True:
            success = poll_database()

            if success:
                display_live_metrics()

            # Poll every 2 seconds
            time.sleep(2)

    except KeyboardInterrupt:
        print("\n\n⏹️  Monitoring stopped by user")
        metrics['end_time'] = datetime.now().isoformat()

        print("\n📊 Exporting results...")
        export_results()

        print("\n✅ Metrics collection complete!")
        print("\nYou can now use these files for your dissertation Results chapter:")
        print("  - CSV file for tables and data analysis")
        print("  - JSON file for detailed programmatic access")
        print("  - Markdown file for formatted summary\n")


if __name__ == '__main__':
    main()
