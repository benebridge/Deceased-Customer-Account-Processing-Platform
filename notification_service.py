"""
Notification Service for BeneBridge
Handles in-app notifications and email notification stubs for beneficiaries
"""

import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
import json

class NotificationService:
    """
    Manages notifications for beneficiaries.
    Sends in-app notifications and creates email stubs (ready for SMTP integration).
    """

    def __init__(self, db_path='benebridge.db'):
        self.db_path = db_path

    def get_db(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # =================== NOTIFICATION CREATION ===================

    def create_notification(
        self,
        case_id: int,
        notification_type: str,
        title: str,
        message: str,
        send_email: bool = True
    ) -> int:
        """
        Create a new notification for a case.

        Args:
            case_id: The case ID
            notification_type: Type of notification (status_change, document_request, etc.)
            title: Notification title
            message: Notification message
            send_email: Whether to send email notification

        Returns:
            notification_id
        """
        conn = self.get_db()
        cursor = conn.cursor()

        # Create in-app notification
        cursor.execute('''
            INSERT INTO notifications (case_id, notification_type, title, message, read, email_sent)
            VALUES (?, ?, ?, ?, 0, 0)
        ''', (case_id, notification_type, title, message))

        notification_id = cursor.lastrowid

        # Send email if requested
        if send_email:
            # Get case details for email
            case = cursor.execute('SELECT * FROM cases WHERE id = ?', (case_id,)).fetchone()
            if case and case['beneficiary_email']:
                self._send_email_stub(
                    to_email=case['beneficiary_email'],
                    beneficiary_name=case['beneficiary_name'],
                    case_number=case['case_number'],
                    subject=title,
                    body=message,
                    notification_id=notification_id
                )

                # Mark email as sent
                cursor.execute('''
                    UPDATE notifications SET email_sent = 1 WHERE id = ?
                ''', (notification_id,))

        conn.commit()
        conn.close()

        return notification_id

    def _send_email_stub(
        self,
        to_email: str,
        beneficiary_name: str,
        case_number: str,
        subject: str,
        body: str,
        notification_id: int
    ):
        """
        Email stub - logs email that would be sent.
        In production, this would integrate with SendGrid, AWS SES, or SMTP.
        """
        email_log = {
            'timestamp': datetime.now().isoformat(),
            'to': to_email,
            'to_name': beneficiary_name,
            'case_number': case_number,
            'subject': subject,
            'body': body,
            'notification_id': notification_id,
            'status': 'STUB - Would send in production'
        }

        # Log to file (in production, this would actually send email)
        with open('email_notifications.log', 'a') as f:
            f.write(json.dumps(email_log, indent=2) + '\n---\n')

        print(f"📧 EMAIL STUB - Would send to {to_email}: {subject}")

    # =================== NOTIFICATION RETRIEVAL ===================

    def get_notifications_for_case(self, case_id: int, unread_only: bool = False) -> List[Dict]:
        """Get all notifications for a case"""
        conn = self.get_db()
        cursor = conn.cursor()

        query = 'SELECT * FROM notifications WHERE case_id = ?'
        params = [case_id]

        if unread_only:
            query += ' AND read = 0'

        query += ' ORDER BY created_at DESC'

        notifications = cursor.execute(query, params).fetchall()
        conn.close()

        return [dict(row) for row in notifications]

    def get_unread_count(self, case_id: int) -> int:
        """Get count of unread notifications for a case"""
        conn = self.get_db()
        cursor = conn.cursor()

        count = cursor.execute('''
            SELECT COUNT(*) as count FROM notifications
            WHERE case_id = ? AND read = 0
        ''', (case_id,)).fetchone()['count']

        conn.close()
        return count

    def mark_as_read(self, notification_id: int):
        """Mark a notification as read"""
        conn = self.get_db()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE notifications SET read = 1 WHERE id = ?
        ''', (notification_id,))

        conn.commit()
        conn.close()

    def mark_all_as_read(self, case_id: int):
        """Mark all notifications for a case as read"""
        conn = self.get_db()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE notifications SET read = 1 WHERE case_id = ?
        ''', (case_id,))

        conn.commit()
        conn.close()

    # =================== PREDEFINED NOTIFICATION TEMPLATES ===================

    def notify_case_created(self, case_id: int):
        """Notify beneficiary that their case has been created"""
        return self.create_notification(
            case_id=case_id,
            notification_type='case_created',
            title='Your Claim Has Been Submitted',
            message='We have received your death benefit claim and are beginning the review process. You can track your claim status here at any time.',
            send_email=True
        )

    def notify_status_change(self, case_id: int, old_status: str, new_status: str):
        """Notify beneficiary of status change"""
        status_messages = {
            'pending': 'Your claim is pending initial review.',
            'under_review': 'Your claim is currently under review by our team.',
            'approved': 'Great news! Your claim has been approved and will be processed for payment.',
            'rejected': 'We regret to inform you that your claim has been rejected. Please contact us for more information.',
            'disbursed': 'Your benefit payment has been disbursed. You should receive it within 3-5 business days.'
        }

        return self.create_notification(
            case_id=case_id,
            notification_type='status_change',
            title=f'Claim Status Updated: {new_status.replace("_", " ").title()}',
            message=status_messages.get(new_status, f'Your claim status has been updated to {new_status}.'),
            send_email=True
        )

    def notify_document_uploaded(self, case_id: int, document_type: str):
        """Notify beneficiary that a document was uploaded"""
        return self.create_notification(
            case_id=case_id,
            notification_type='document_uploaded',
            title='Document Received',
            message=f'We have received your {document_type.replace("_", " ")} document and added it to your claim.',
            send_email=False  # Don't send email for every document
        )

    def notify_document_request(self, case_id: int, document_type: str, reason: str = ''):
        """Notify beneficiary that additional documents are needed"""
        message = f'We need additional documentation to process your claim: {document_type.replace("_", " ")}.'
        if reason:
            message += f' Reason: {reason}'

        return self.create_notification(
            case_id=case_id,
            notification_type='document_request',
            title='Additional Documentation Required',
            message=message,
            send_email=True
        )

    def notify_workflow_milestone(self, case_id: int, stage: int, stage_name: str):
        """Notify beneficiary when claim reaches a new workflow stage"""
        stage_messages = {
            1: 'We are currently reviewing your claim form and documents.',
            2: 'We are verifying beneficiary designations and account records.',
            3: 'We are reviewing account details and calculating tax withholding.',
            4: 'Your claim is undergoing final compliance review and approval.',
            5: 'Your claim has been approved and we are preparing payment.'
        }

        return self.create_notification(
            case_id=case_id,
            notification_type='workflow_milestone',
            title=f'Processing Update: {stage_name}',
            message=stage_messages.get(stage, f'Your claim has advanced to {stage_name}.'),
            send_email=True
        )

    def notify_estimated_completion(self, case_id: int, estimated_days: int):
        """Notify beneficiary of estimated completion time"""
        return self.create_notification(
            case_id=case_id,
            notification_type='timeline_update',
            title='Estimated Processing Time',
            message=f'Based on current progress, we estimate your claim will be processed within {estimated_days} business days.',
            send_email=False
        )

    def notify_payment_processed(self, case_id: int, amount: float, method: str):
        """Notify beneficiary that payment has been processed"""
        return self.create_notification(
            case_id=case_id,
            notification_type='payment_processed',
            title='Payment Processed',
            message=f'Your death benefit payment of ${amount:,.2f} has been processed via {method}. You should receive it within 3-5 business days.',
            send_email=True
        )

    def notify_verification_complete(self, case_id: int, verification_type: str):
        """Notify beneficiary when verification is complete"""
        return self.create_notification(
            case_id=case_id,
            notification_type='verification_complete',
            title=f'{verification_type.replace("_", " ").title()} Verified',
            message=f'We have successfully verified your {verification_type.replace("_", " ")}.',
            send_email=False
        )

    def notify_message_from_institution(self, case_id: int, message_from_user: str, message_text: str):
        """Notify beneficiary of a message from the institution"""
        return self.create_notification(
            case_id=case_id,
            notification_type='message_from_institution',
            title=f'Message from {message_from_user}',
            message=message_text,
            send_email=True
        )

    # =================== BULK OPERATIONS ===================

    def create_bulk_notification(self, case_ids: List[int], title: str, message: str, send_email: bool = False):
        """Create the same notification for multiple cases"""
        notification_ids = []
        for case_id in case_ids:
            nid = self.create_notification(
                case_id=case_id,
                notification_type='bulk_notification',
                title=title,
                message=message,
                send_email=send_email
            )
            notification_ids.append(nid)

        return notification_ids


def get_notification_service():
    """Get singleton instance of notification service"""
    return NotificationService()
