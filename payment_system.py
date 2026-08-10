"""
Payment System Integration for BeneBridge
Handles death benefit payment initiation and tracking
"""

import sqlite3
from datetime import datetime
from typing import Dict, Optional
import json
import secrets
import string

class PaymentSystem:
    """
    Payment system integration layer.
    In production, this would integrate with the bank's payment processing system.
    For POC, generates payment authorization codes and logs transactions.
    """

    def __init__(self, db_path='benebridge.db'):
        self.db_path = db_path
        self._init_payment_tables()

    def get_db(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_payment_tables(self):
        """Initialize payment tracking tables"""
        conn = self.get_db()
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER NOT NULL,
                payment_reference TEXT UNIQUE NOT NULL,
                gross_amount REAL NOT NULL,
                federal_withholding REAL NOT NULL,
                state_withholding REAL NOT NULL,
                net_amount REAL NOT NULL,
                payment_method TEXT NOT NULL,
                beneficiary_account_number TEXT,
                beneficiary_routing_number TEXT,
                beneficiary_bank_name TEXT,
                payment_status TEXT DEFAULT 'pending',
                initiated_by INTEGER,
                initiated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                bank_confirmation_number TEXT,
                payment_details TEXT,
                FOREIGN KEY (case_id) REFERENCES cases(id),
                FOREIGN KEY (initiated_by) REFERENCES users(id)
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_payments_case_id ON payments(case_id)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(payment_status)
        ''')

        conn.commit()
        conn.close()

    # =================== PAYMENT INITIATION ===================

    def initiate_payment(
        self,
        case_id: int,
        gross_amount: float,
        federal_withholding: float,
        state_withholding: float,
        payment_method: str,
        beneficiary_account_number: Optional[str] = None,
        beneficiary_routing_number: Optional[str] = None,
        beneficiary_bank_name: Optional[str] = None,
        initiated_by: Optional[int] = None
    ) -> Dict:
        """
        Initiate a death benefit payment.

        Args:
            case_id: Case ID
            gross_amount: Gross distribution amount
            federal_withholding: Federal tax withholding
            state_withholding: State tax withholding
            payment_method: 'ACH', 'Wire', 'Check'
            beneficiary_account_number: Bank account number (for ACH/Wire)
            beneficiary_routing_number: Bank routing number (for ACH/Wire)
            beneficiary_bank_name: Bank name
            initiated_by: User ID who initiated payment

        Returns:
            Payment initiation result with reference number
        """

        net_amount = gross_amount - federal_withholding - state_withholding

        # Generate unique payment reference
        payment_reference = self._generate_payment_reference()

        conn = self.get_db()
        cursor = conn.cursor()

        # Insert payment record
        cursor.execute('''
            INSERT INTO payments (
                case_id, payment_reference, gross_amount,
                federal_withholding, state_withholding, net_amount,
                payment_method, beneficiary_account_number,
                beneficiary_routing_number, beneficiary_bank_name,
                payment_status, initiated_by, payment_details
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            case_id,
            payment_reference,
            gross_amount,
            federal_withholding,
            state_withholding,
            net_amount,
            payment_method,
            beneficiary_account_number,
            beneficiary_routing_number,
            beneficiary_bank_name,
            'pending_authorization',
            initiated_by,
            json.dumps({
                'payment_method': payment_method,
                'initiated_at': datetime.now().isoformat(),
                'gross_amount': gross_amount,
                'net_amount': net_amount
            })
        ))

        payment_id = cursor.lastrowid

        # Update case status
        cursor.execute('''
            UPDATE cases SET status = 'approved' WHERE id = ?
        ''', (case_id,))

        conn.commit()
        conn.close()

        # Generate bank system redirect URL
        bank_system_url = self._generate_bank_system_url(payment_reference, payment_method)

        return {
            'success': True,
            'payment_id': payment_id,
            'payment_reference': payment_reference,
            'net_amount': net_amount,
            'payment_method': payment_method,
            'payment_status': 'pending_authorization',
            'bank_system_url': bank_system_url,
            'message': f'Payment initiated. Reference: {payment_reference}'
        }

    def _generate_payment_reference(self) -> str:
        """Generate unique payment reference number"""
        prefix = 'PAY'
        date_part = datetime.now().strftime('%Y%m%d')
        random_part = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
        return f'{prefix}-{date_part}-{random_part}'

    def _generate_bank_system_url(self, payment_reference: str, payment_method: str) -> str:
        """
        Generate URL to bank's internal payment system.
        In production, this would be the actual bank's payment processing URL.
        For POC, this is a placeholder URL.
        """

        # Simulated bank system URLs based on payment method
        bank_systems = {
            'ACH': 'https://bank-internal.example.com/payments/ach/authorize',
            'Wire': 'https://bank-internal.example.com/payments/wire/authorize',
            'Check': 'https://bank-internal.example.com/payments/check/print'
        }

        base_url = bank_systems.get(payment_method, bank_systems['ACH'])

        # In production, would include authentication tokens and encrypted parameters
        return f'{base_url}?ref={payment_reference}&source=benebridge'

    # =================== PAYMENT TRACKING ===================

    def get_payment_status(self, payment_reference: str) -> Optional[Dict]:
        """Get payment status by reference number"""
        conn = self.get_db()
        cursor = conn.cursor()

        payment = cursor.execute('''
            SELECT * FROM payments WHERE payment_reference = ?
        ''', (payment_reference,)).fetchone()

        conn.close()

        if payment:
            return dict(payment)
        return None

    def get_payments_for_case(self, case_id: int) -> list:
        """Get all payments for a case"""
        conn = self.get_db()
        cursor = conn.cursor()

        payments = cursor.execute('''
            SELECT p.*, u.full_name as initiated_by_name
            FROM payments p
            LEFT JOIN users u ON p.initiated_by = u.id
            WHERE p.case_id = ?
            ORDER BY p.initiated_at DESC
        ''', (case_id,)).fetchall()

        conn.close()

        return [dict(row) for row in payments]

    def update_payment_status(
        self,
        payment_reference: str,
        new_status: str,
        bank_confirmation_number: Optional[str] = None
    ) -> bool:
        """
        Update payment status.
        Statuses: pending_authorization, authorized, processing, completed, failed, cancelled
        """
        conn = self.get_db()
        cursor = conn.cursor()

        if new_status in ['completed', 'failed']:
            cursor.execute('''
                UPDATE payments
                SET payment_status = ?, processed_at = ?, bank_confirmation_number = ?
                WHERE payment_reference = ?
            ''', (new_status, datetime.now(), bank_confirmation_number, payment_reference))
        else:
            cursor.execute('''
                UPDATE payments
                SET payment_status = ?, bank_confirmation_number = ?
                WHERE payment_reference = ?
            ''', (new_status, bank_confirmation_number, payment_reference))

        conn.commit()
        conn.close()

        return True

    # =================== PAYMENT METHODS ===================

    def get_payment_method_requirements(self, payment_method: str) -> Dict:
        """Get required information for each payment method"""
        requirements = {
            'ACH': {
                'required_fields': [
                    'beneficiary_account_number',
                    'beneficiary_routing_number',
                    'beneficiary_bank_name',
                    'account_type'  # checking or savings
                ],
                'processing_time': '1-3 business days',
                'fees': 0.0,
                'limits': {'min': 0.01, 'max': 1000000.00}
            },
            'Wire': {
                'required_fields': [
                    'beneficiary_account_number',
                    'beneficiary_routing_number',
                    'beneficiary_bank_name',
                    'beneficiary_bank_address',
                    'swift_code'  # for international
                ],
                'processing_time': 'Same day',
                'fees': 30.00,
                'limits': {'min': 0.01, 'max': 10000000.00}
            },
            'Check': {
                'required_fields': [
                    'beneficiary_name',
                    'beneficiary_address'
                ],
                'processing_time': '5-7 business days (mail)',
                'fees': 0.0,
                'limits': {'min': 0.01, 'max': 100000.00}
            }
        }

        return requirements.get(payment_method, {})

    # =================== PAYMENT VALIDATION ===================

    def validate_payment_eligibility(self, case_id: int) -> Dict:
        """
        Validate that a case is eligible for payment.
        Checks: status, required approvals, tax calculations, documents
        """
        conn = self.get_db()
        cursor = conn.cursor()

        case = cursor.execute('SELECT * FROM cases WHERE id = ?', (case_id,)).fetchone()

        if not case:
            conn.close()
            return {'eligible': False, 'reason': 'Case not found'}

        issues = []

        # Check case status
        if case['status'] not in ['approved', 'under_review']:
            issues.append('Case must be approved before payment')

        # Check for required documents
        docs = cursor.execute('''
            SELECT COUNT(*) as count FROM documents WHERE case_id = ?
        ''', (case_id,)).fetchone()['count']

        if docs < 2:  # At least death cert and ID
            issues.append('Missing required documents')

        # Check for tax calculation
        tax_calc = cursor.execute('''
            SELECT COUNT(*) as count FROM tax_calculations WHERE case_id = ?
        ''', (case_id,)).fetchone()['count']

        if tax_calc == 0:
            issues.append('Tax withholding not calculated')

        # Check workflow completion
        incomplete_tasks = cursor.execute('''
            SELECT COUNT(*) as count FROM workflow_tasks
            WHERE case_id = ? AND completed = 0 AND stage <= 4
        ''', (case_id,)).fetchone()['count']

        if incomplete_tasks > 0:
            issues.append(f'{incomplete_tasks} workflow tasks not completed')

        # Check for existing payments
        existing_payments = cursor.execute('''
            SELECT COUNT(*) as count FROM payments
            WHERE case_id = ? AND payment_status IN ('completed', 'processing', 'pending_authorization')
        ''', (case_id,)).fetchone()['count']

        if existing_payments > 0:
            issues.append('Payment already initiated for this case')

        conn.close()

        eligible = len(issues) == 0

        return {
            'eligible': eligible,
            'issues': issues,
            'message': 'Case is eligible for payment' if eligible else 'Case has issues preventing payment'
        }

    # =================== REPORTING ===================

    def get_payment_statistics(self) -> Dict:
        """Get payment statistics"""
        conn = self.get_db()
        cursor = conn.cursor()

        total_payments = cursor.execute('SELECT COUNT(*) as count FROM payments').fetchone()['count']

        pending = cursor.execute('''
            SELECT COUNT(*) as count FROM payments WHERE payment_status = 'pending_authorization'
        ''').fetchone()['count']

        completed = cursor.execute('''
            SELECT COUNT(*) as count FROM payments WHERE payment_status = 'completed'
        ''').fetchone()['count']

        total_disbursed = cursor.execute('''
            SELECT COALESCE(SUM(net_amount), 0) as total FROM payments WHERE payment_status = 'completed'
        ''').fetchone()['total']

        avg_payment = cursor.execute('''
            SELECT COALESCE(AVG(net_amount), 0) as avg FROM payments WHERE payment_status = 'completed'
        ''').fetchone()['avg']

        conn.close()

        return {
            'total_payments': total_payments,
            'pending': pending,
            'completed': completed,
            'total_disbursed': total_disbursed,
            'average_payment': avg_payment
        }


def get_payment_system():
    """Get singleton instance of payment system"""
    return PaymentSystem()
