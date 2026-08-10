#!/usr/bin/env python3
"""
Remove beneficiaries that have no account designations (unlinked to any deceased)
"""

import sqlite3
from pathlib import Path

def main():
    base_dir = Path(__file__).parent

    print("=" * 80)
    print("REMOVING UNLINKED BENEFICIARIES")
    print("=" * 80)
    print()

    # Get all beneficiaries
    conn_ben = sqlite3.connect(base_dir / "beneficiary_registry.db")
    conn_ben.row_factory = sqlite3.Row
    c_ben = conn_ben.cursor()
    c_ben.execute("SELECT * FROM beneficiaries")
    all_bens = [dict(row) for row in c_ben.fetchall()]

    # Get all designations
    c_ben.execute("SELECT * FROM beneficiary_designations")
    all_designations = [dict(row) for row in c_ben.fetchall()]

    # Find beneficiaries with no designations
    ben_ids_with_designations = set(d['beneficiary_id'] for d in all_designations)
    unlinked_bens = [b for b in all_bens if b['beneficiary_id'] not in ben_ids_with_designations]

    print(f"Found {len(unlinked_bens)} unlinked beneficiaries:")
    for ben in unlinked_bens:
        print(f"  - ID {ben['beneficiary_id']}: {ben['full_name']} (SSN: {ben['ssn']})")
    print()

    if not unlinked_bens:
        print("No unlinked beneficiaries to remove!")
        return

    # Get their SSNs for removing from identity_verification
    unlinked_ssns = [b['ssn'] for b in unlinked_bens]
    unlinked_ids = [b['beneficiary_id'] for b in unlinked_bens]

    # Remove from beneficiaries table
    print("Removing from beneficiary_registry.db...")
    placeholders = ','.join('?' * len(unlinked_ids))
    c_ben.execute(f"DELETE FROM beneficiaries WHERE beneficiary_id IN ({placeholders})", unlinked_ids)
    removed_ben = c_ben.rowcount
    conn_ben.commit()
    conn_ben.close()
    print(f"  ✓ Removed {removed_ben} beneficiaries")

    # Remove from identity_verification
    print("Removing from identity_verification.db...")
    conn_id = sqlite3.connect(base_dir / "identity_verification.db")
    c_id = conn_id.cursor()
    placeholders = ','.join('?' * len(unlinked_ssns))
    c_id.execute(f"DELETE FROM identity_records WHERE ssn IN ({placeholders})", unlinked_ssns)
    removed_id = c_id.rowcount
    conn_id.commit()
    conn_id.close()
    print(f"  ✓ Removed {removed_id} identity records")

    print()
    print("=" * 80)
    print("CLEANUP COMPLETE")
    print("=" * 80)
    print()

    # Show updated counts
    conn_ben = sqlite3.connect(base_dir / "beneficiary_registry.db")
    c_ben = conn_ben.cursor()
    c_ben.execute("SELECT COUNT(*) FROM beneficiaries")
    total_bens = c_ben.fetchone()[0]
    conn_ben.close()

    conn_id = sqlite3.connect(base_dir / "identity_verification.db")
    c_id = conn_id.cursor()
    c_id.execute("SELECT COUNT(*) FROM identity_records")
    total_ids = c_id.fetchone()[0]
    conn_id.close()

    print(f"Remaining beneficiaries: {total_bens}")
    print(f"Remaining identity records: {total_ids}")
    print()
    print("All remaining beneficiaries are linked to deceased persons!")

if __name__ == "__main__":
    main()
