"""
Multi-Source Data Reconciliation Engine
Handles duplicate detection, data merging, and conflict resolution for death claims
"""

import sqlite3
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import json
from difflib import SequenceMatcher

class ReconciliationEngine:
    """
    Detects and merges duplicate case submissions from multiple sources.
    Handles conflicts and maintains audit trail of data changes.
    """

    def __init__(self, db_path='benebridge.db'):
        self.db_path = db_path

    def get_db(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # =================== DUPLICATE DETECTION ===================

    def find_potential_duplicates(self, case_data: Dict) -> List[Dict]:
        """
        Find potential duplicate cases based on multiple matching criteria.
        Returns list of potential duplicates with confidence scores.
        """
        conn = self.get_db()
        cursor = conn.cursor()

        potential_duplicates = []

        # Criteria 1: Exact account number match
        if case_data.get('account_number'):
            exact_matches = cursor.execute('''
                SELECT *, 'account_number' as match_type, 100 as confidence
                FROM cases
                WHERE account_number = ? AND id != ?
            ''', (case_data['account_number'], case_data.get('id', 0))).fetchall()
            potential_duplicates.extend([dict(row) for row in exact_matches])

        # Criteria 2: Deceased SSN + Beneficiary SSN match
        if case_data.get('deceased_ssn') and case_data.get('beneficiary_ssn'):
            ssn_matches = cursor.execute('''
                SELECT *, 'ssn_match' as match_type, 95 as confidence
                FROM cases
                WHERE deceased_ssn = ? AND beneficiary_ssn = ? AND id != ?
            ''', (case_data['deceased_ssn'], case_data['beneficiary_ssn'], case_data.get('id', 0))).fetchall()
            potential_duplicates.extend([dict(row) for row in ssn_matches])

        # Criteria 3: Deceased name + Beneficiary name fuzzy match
        if case_data.get('deceased_name') and case_data.get('beneficiary_name'):
            name_candidates = cursor.execute('''
                SELECT *
                FROM cases
                WHERE id != ?
            ''', (case_data.get('id', 0),)).fetchall()

            for candidate in name_candidates:
                deceased_similarity = self._string_similarity(
                    case_data['deceased_name'],
                    candidate['deceased_name']
                )
                beneficiary_similarity = self._string_similarity(
                    case_data['beneficiary_name'],
                    candidate['beneficiary_name']
                )

                # If both names are >80% similar, consider it a potential duplicate
                if deceased_similarity > 0.8 and beneficiary_similarity > 0.8:
                    dup = dict(candidate)
                    dup['match_type'] = 'name_fuzzy'
                    dup['confidence'] = int((deceased_similarity + beneficiary_similarity) / 2 * 100)
                    potential_duplicates.append(dup)

        conn.close()

        # Remove duplicates from list and sort by confidence
        unique_duplicates = self._deduplicate_results(potential_duplicates)
        return sorted(unique_duplicates, key=lambda x: x['confidence'], reverse=True)

    def _string_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity ratio between two strings (0-1)"""
        if not str1 or not str2:
            return 0.0
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

    def _deduplicate_results(self, duplicates: List[Dict]) -> List[Dict]:
        """Remove duplicate entries from results list"""
        seen_ids = set()
        unique = []
        for dup in duplicates:
            if dup['id'] not in seen_ids:
                seen_ids.add(dup['id'])
                unique.append(dup)
        return unique

    # =================== DATA MERGING ===================

    def merge_case_data(self, existing_case_id: int, new_data: Dict, user_id: int) -> Dict:
        """
        Merge new data into existing case.
        Handles conflicts by applying merge rules and creating audit trail.

        Returns: {
            'merged': True/False,
            'conflicts': [...],
            'changes': {...},
            'auto_resolved': [...],
            'needs_review': [...]
        }
        """
        conn = self.get_db()
        cursor = conn.cursor()

        # Get existing case
        existing = cursor.execute('SELECT * FROM cases WHERE id = ?', (existing_case_id,)).fetchone()
        if not existing:
            conn.close()
            return {'merged': False, 'error': 'Case not found'}

        existing_dict = dict(existing)

        # Detect conflicts
        conflicts = []
        changes = {}
        auto_resolved = []
        needs_review = []

        # Fields that can be auto-merged
        mergeable_fields = [
            'account_number', 'account_type', 'account_balance',
            'deceased_name', 'deceased_ssn', 'deceased_dob', 'date_of_death',
            'beneficiary_name', 'beneficiary_ssn', 'beneficiary_dob',
            'beneficiary_relationship', 'beneficiary_address', 'beneficiary_phone'
        ]

        for field in mergeable_fields:
            if field in new_data:
                existing_value = existing_dict.get(field)
                new_value = new_data[field]

                # Skip if values are the same
                if existing_value == new_value:
                    continue

                # Apply merge rules
                resolution = self._resolve_field_conflict(
                    field, existing_value, new_value, existing_dict, new_data
                )

                if resolution['action'] == 'keep_new':
                    changes[field] = {
                        'old': existing_value,
                        'new': new_value,
                        'reason': resolution['reason']
                    }
                    auto_resolved.append({
                        'field': field,
                        'resolution': 'Used new value',
                        'reason': resolution['reason']
                    })
                elif resolution['action'] == 'keep_existing':
                    auto_resolved.append({
                        'field': field,
                        'resolution': 'Kept existing value',
                        'reason': resolution['reason']
                    })
                elif resolution['action'] == 'needs_review':
                    conflicts.append({
                        'field': field,
                        'existing_value': existing_value,
                        'new_value': new_value,
                        'reason': resolution['reason']
                    })
                    needs_review.append(field)

        # Apply changes to database
        if changes:
            update_fields = []
            update_values = []
            for field, change in changes.items():
                update_fields.append(f"{field} = ?")
                update_values.append(change['new'])

            update_values.append(existing_case_id)

            cursor.execute(f'''
                UPDATE cases
                SET {', '.join(update_fields)}
                WHERE id = ?
            ''', update_values)

            # Log the merge in activity log
            cursor.execute('''
                INSERT INTO activity_log (case_id, user_id, action, details)
                VALUES (?, ?, ?, ?)
            ''', (
                existing_case_id,
                user_id,
                'data_merge',
                json.dumps({
                    'changes': {k: {'old': str(v['old']), 'new': str(v['new'])} for k, v in changes.items()},
                    'auto_resolved_count': len(auto_resolved),
                    'conflicts_count': len(conflicts)
                })
            ))

            conn.commit()

        conn.close()

        return {
            'merged': True,
            'conflicts': conflicts,
            'changes': changes,
            'auto_resolved': auto_resolved,
            'needs_review': needs_review
        }

    def _resolve_field_conflict(
        self,
        field: str,
        existing_value,
        new_value,
        existing_case: Dict,
        new_case: Dict
    ) -> Dict:
        """
        Apply merge rules to resolve field conflicts.
        Returns: {'action': 'keep_new'|'keep_existing'|'needs_review', 'reason': str}
        """

        # Rule 1: If existing is empty/null, always use new value
        if not existing_value or existing_value == '':
            return {'action': 'keep_new', 'reason': 'Existing value was empty'}

        # Rule 2: If new is empty/null, keep existing
        if not new_value or new_value == '':
            return {'action': 'keep_existing', 'reason': 'New value was empty'}

        # Rule 3: For account balance, use the most recent value
        if field == 'account_balance':
            # In production, would check timestamp of data source
            # For now, prefer higher balance (more conservative)
            if new_value > existing_value:
                return {'action': 'keep_new', 'reason': 'Higher balance (more conservative)'}
            else:
                return {'action': 'keep_existing', 'reason': 'Existing balance higher'}

        # Rule 4: For dates, prefer earlier date of death
        if field == 'date_of_death':
            try:
                existing_dt = datetime.strptime(str(existing_value), '%Y-%m-%d')
                new_dt = datetime.strptime(str(new_value), '%Y-%m-%d')
                if new_dt < existing_dt:
                    return {'action': 'keep_new', 'reason': 'Earlier date'}
                else:
                    return {'action': 'keep_existing', 'reason': 'Existing date earlier'}
            except:
                return {'action': 'needs_review', 'reason': 'Date format mismatch'}

        # Rule 5: For SSNs, use more complete value (no dashes vs dashes)
        if 'ssn' in field.lower():
            existing_clean = str(existing_value).replace('-', '')
            new_clean = str(new_value).replace('-', '')

            if existing_clean == new_clean:
                # Same SSN, prefer formatted version with dashes
                if '-' in str(new_value) and '-' not in str(existing_value):
                    return {'action': 'keep_new', 'reason': 'Better formatting'}
                else:
                    return {'action': 'keep_existing', 'reason': 'Values equivalent'}
            else:
                # Different SSNs - needs manual review
                return {'action': 'needs_review', 'reason': 'SSN mismatch'}

        # Rule 6: For names, use fuzzy matching
        if 'name' in field.lower():
            similarity = self._string_similarity(str(existing_value), str(new_value))
            if similarity > 0.85:
                # Very similar, use longer/more complete version
                if len(str(new_value)) > len(str(existing_value)):
                    return {'action': 'keep_new', 'reason': 'More complete name'}
                else:
                    return {'action': 'keep_existing', 'reason': 'Existing name complete'}
            else:
                return {'action': 'needs_review', 'reason': 'Name mismatch'}

        # Rule 7: For addresses and phone, prefer more complete
        if field in ['beneficiary_address', 'beneficiary_phone']:
            if len(str(new_value)) > len(str(existing_value)):
                return {'action': 'keep_new', 'reason': 'More complete information'}
            else:
                return {'action': 'keep_existing', 'reason': 'Existing info complete'}

        # Default: Needs manual review
        return {'action': 'needs_review', 'reason': 'Conflicting values require review'}

    # =================== CONFLICT RESOLUTION ===================

    def get_unresolved_conflicts(self) -> List[Dict]:
        """Get all cases with unresolved data conflicts"""
        conn = self.get_db()
        cursor = conn.cursor()

        # Look for merge conflicts in activity log
        conflicts = cursor.execute('''
            SELECT
                c.id,
                c.case_number,
                c.beneficiary_name,
                c.status,
                a.details,
                a.timestamp
            FROM cases c
            JOIN activity_log a ON c.id = a.case_id
            WHERE a.action = 'data_merge'
            AND json_extract(a.details, '$.conflicts_count') > 0
            ORDER BY a.timestamp DESC
        ''').fetchall()

        conn.close()
        return [dict(row) for row in conflicts]

    def resolve_conflict(self, case_id: int, field: str, chosen_value, user_id: int) -> bool:
        """Manually resolve a data conflict"""
        conn = self.get_db()
        cursor = conn.cursor()

        try:
            cursor.execute(f'''
                UPDATE cases SET {field} = ? WHERE id = ?
            ''', (chosen_value, case_id))

            cursor.execute('''
                INSERT INTO activity_log (case_id, user_id, action, details)
                VALUES (?, ?, ?, ?)
            ''', (
                case_id,
                user_id,
                'conflict_resolved',
                json.dumps({'field': field, 'chosen_value': str(chosen_value)})
            ))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            conn.close()
            return False

    # =================== BULK RECONCILIATION ===================

    def run_bulk_reconciliation(self) -> Dict:
        """
        Run reconciliation across all cases to find and merge duplicates.
        Returns summary of findings.
        """
        conn = self.get_db()
        cursor = conn.cursor()

        all_cases = cursor.execute('SELECT * FROM cases WHERE status != "merged"').fetchall()

        duplicates_found = []
        auto_merged = 0
        needs_review = 0

        for case in all_cases:
            case_dict = dict(case)
            potential_dups = self.find_potential_duplicates(case_dict)

            for dup in potential_dups:
                # Only auto-merge if confidence is 100% (exact account match)
                if dup['confidence'] == 100:
                    # Check if not already processed
                    existing_link = cursor.execute('''
                        SELECT * FROM activity_log
                        WHERE case_id = ? AND action = 'duplicate_detected'
                        AND json_extract(details, '$.duplicate_of') = ?
                    ''', (case_dict['id'], dup['id'])).fetchone()

                    if not existing_link:
                        duplicates_found.append({
                            'case_id': case_dict['id'],
                            'duplicate_of': dup['id'],
                            'confidence': dup['confidence'],
                            'match_type': dup['match_type']
                        })

                        # Log the duplicate detection
                        cursor.execute('''
                            INSERT INTO activity_log (case_id, user_id, action, details)
                            VALUES (?, ?, ?, ?)
                        ''', (
                            case_dict['id'],
                            1,  # System user
                            'duplicate_detected',
                            json.dumps({
                                'duplicate_of': dup['id'],
                                'confidence': dup['confidence'],
                                'match_type': dup['match_type']
                            })
                        ))

                        auto_merged += 1
                else:
                    needs_review += 1

        conn.commit()
        conn.close()

        return {
            'total_cases_scanned': len(all_cases),
            'duplicates_found': len(duplicates_found),
            'auto_merged': auto_merged,
            'needs_manual_review': needs_review,
            'details': duplicates_found
        }


def get_reconciliation_engine():
    """Get singleton instance of reconciliation engine"""
    return ReconciliationEngine()
