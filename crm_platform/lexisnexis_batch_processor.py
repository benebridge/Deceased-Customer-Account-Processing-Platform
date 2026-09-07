#!/usr/bin/env python3
"""
LexisNexis Deceased Batch Processing
Simulates overnight batch import of death notifications to enable proactive case creation

Per dissertation: Reduces fraud window from 3 days to 0-1 day (67% reduction)
by creating cases in NOTIFIED state before beneficiaries contact the institution.
"""

import sqlite3
import random
import requests
from datetime import datetime, timedelta


class LexisNexisBatchProcessor:
    """
    Batch processor for LexisNexis death notifications.

    In production, this would:
    1. Query LexisNexis API for recent death records
    2. Match against institution customer database (Jack Henry)
    3. Create proactive cases in NOTIFIED state in CRM

    For POC, we simulate this with synthetic data.
    """

    def __init__(self, crm_db_path, jackhenry_api_url='http://localhost:5012'):
        self.crm_db_path = crm_db_path
        self.jackhenry_api_url = jackhenry_api_url

    def run_overnight_batch(self):
        """
        Simulate overnight LexisNexis death notification batch processing.

        Returns:
            dict: Processing statistics including cases created, records processed, etc.
        """
        print("\n" + "=" * 80)
        print("LEXISNEXIS DECEASED BATCH PROCESSOR - OVERNIGHT RUN")
        print(f"Run Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        batch_stats = {
            'run_date': datetime.now().isoformat(),
            'records_processed': 0,
            'cases_created': 0,
            'cases_already_exist': 0,
            'match_failures': 0,
            'processing_time_seconds': 0.0
        }

        start_time = datetime.now()

        # Step 1: Simulate fetching death notifications from LexisNexis
        print("\n[1/4] Fetching death notifications from LexisNexis (simulated)...")
        death_notifications = self._simulate_lexisnexis_query()
        batch_stats['records_processed'] = len(death_notifications)
        print(f"  → Retrieved {len(death_notifications)} death notifications")

        # Step 2: Match each death notification to customer records
        print("\n[2/4] Matching death notifications to customer accounts...")
        matched_customers = []
        for notification in death_notifications:
            customer = self._match_death_notification_to_customer(notification)
            if customer:
                matched_customers.append(customer)
            else:
                batch_stats['match_failures'] += 1

        print(f"  → Matched {len(matched_customers)} customers")
        print(f"  → {batch_stats['match_failures']} notifications did not match any customers")

        # Step 3: Create proactive cases in NOTIFIED state
        print("\n[3/4] Creating proactive cases in CRM...")
        for customer in matched_customers:
            case_created = self._create_proactive_case(customer)
            if case_created:
                batch_stats['cases_created'] += 1
            else:
                batch_stats['cases_already_exist'] += 1

        print(f"  → Created {batch_stats['cases_created']} new cases in NOTIFIED state")
        print(f"  → {batch_stats['cases_already_exist']} cases already existed")

        # Step 4: Record batch run statistics
        end_time = datetime.now()
        batch_stats['processing_time_seconds'] = (end_time - start_time).total_seconds()

        print("\n[4/4] Recording batch processing statistics...")
        self._record_batch_run(batch_stats)

        print("\n" + "=" * 80)
        print("BATCH PROCESSING COMPLETE")
        print(f"Total Processing Time: {batch_stats['processing_time_seconds']:.2f} seconds")
        print(f"New Cases Created: {batch_stats['cases_created']}")
        print("=" * 80 + "\n")

        return batch_stats

    def _simulate_lexisnexis_query(self):
        """
        Simulate querying LexisNexis API for recent death records.

        In production, this would call the actual LexisNexis API.
        For POC, we generate synthetic death notifications.

        Returns:
            list: List of death notification records
        """
        # Simulate 2-5 death notifications per batch run
        num_notifications = random.randint(2, 5)

        notifications = []
        for i in range(num_notifications):
            # Generate synthetic SSNs that might match our test customers
            # In a real scenario, these would come from LexisNexis
            notifications.append({
                'source': 'LexisNexis',
                'notification_id': f'LN-{datetime.now().strftime("%Y%m%d")}-{i+1:04d}',
                'ssn': self._generate_test_ssn(),
                'deceased_name': f'Test Deceased {i+1}',
                'date_of_death': (datetime.now() - timedelta(days=random.randint(1, 30))).strftime('%Y-%m-%d'),
                'notification_date': datetime.now().strftime('%Y-%m-%d')
            })

        return notifications

    def _generate_test_ssn(self):
        """Generate a test SSN that might match our synthetic customers"""
        # In production, this would be actual SSNs from LexisNexis
        # For POC, we use synthetic SSNs
        return f"{random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(1000, 9999)}"

    def _match_death_notification_to_customer(self, death_record):
        """
        Match LexisNexis death record to Jack Henry customer by SSN.

        Args:
            death_record: Death notification from LexisNexis

        Returns:
            dict: Customer data if match found, None otherwise
        """
        try:
            # Query Jack Henry API to find customer by SSN
            response = requests.get(
                f"{self.jackhenry_api_url}/api/customers/by-ssn/{death_record['ssn']}",
                timeout=5
            )

            if response.status_code == 200:
                customer_data = response.json()
                # Enrich customer data with death notification info
                customer_data['death_notification'] = death_record
                return customer_data
            else:
                return None

        except Exception as e:
            print(f"  ! Error matching SSN {death_record['ssn']}: {str(e)}")
            return None

    def _create_proactive_case(self, customer_data):
        """
        Create case in NOTIFIED state before beneficiary contact.

        This is the key dissertation feature: proactive case creation
        reduces fraud window by 67% (from 3 days to 0-1 day).

        Args:
            customer_data: Matched customer with death notification

        Returns:
            bool: True if case created, False if already exists
        """
        conn = sqlite3.connect(self.crm_db_path)
        cursor = conn.cursor()

        try:
            # Check if case already exists for this customer
            cursor.execute("""
                SELECT id FROM workflow_cases
                WHERE customer_id = ? AND status != 'CLOSED'
            """, (customer_data['customer_id'],))

            existing_case = cursor.fetchone()
            if existing_case:
                print(f"  - Case already exists for customer {customer_data['customer_id']}")
                return False

            # Create new case in NOTIFIED state
            death_notification = customer_data['death_notification']

            cursor.execute("""
                INSERT INTO workflow_cases (
                    customer_id,
                    customer_name,
                    status,
                    claim_amount,
                    date_created,
                    last_updated,
                    death_notification_source,
                    death_notification_id,
                    deceased_ssn,
                    date_of_death
                ) VALUES (?, ?, 'NOTIFIED', 0.0, ?, ?, ?, ?, ?, ?)
            """, (
                customer_data['customer_id'],
                customer_data['full_name'],
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                death_notification['source'],
                death_notification['notification_id'],
                death_notification['ssn'],
                death_notification['date_of_death']
            ))

            conn.commit()
            case_id = cursor.lastrowid

            print(f"  + Created case #{case_id} for customer {customer_data['customer_id']} ({customer_data['full_name']})")
            print(f"    Death Date: {death_notification['date_of_death']}")
            print(f"    Notification: {death_notification['notification_id']}")

            return True

        except Exception as e:
            print(f"  ! Error creating case for customer {customer_data.get('customer_id', 'unknown')}: {str(e)}")
            conn.rollback()
            return False

        finally:
            conn.close()

    def _record_batch_run(self, batch_stats):
        """
        Record batch processing run statistics for audit and monitoring.

        Args:
            batch_stats: Dictionary of batch processing statistics
        """
        conn = sqlite3.connect(self.crm_db_path)
        cursor = conn.cursor()

        try:
            # Create batch_processing_runs table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS batch_processing_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_date TEXT,
                    records_processed INTEGER,
                    cases_created INTEGER,
                    cases_already_exist INTEGER,
                    match_failures INTEGER,
                    processing_time_seconds REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                INSERT INTO batch_processing_runs (
                    run_date,
                    records_processed,
                    cases_created,
                    cases_already_exist,
                    match_failures,
                    processing_time_seconds
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                batch_stats['run_date'],
                batch_stats['records_processed'],
                batch_stats['cases_created'],
                batch_stats['cases_already_exist'],
                batch_stats['match_failures'],
                batch_stats['processing_time_seconds']
            ))

            conn.commit()
            print(f"  → Batch run statistics recorded (ID: {cursor.lastrowid})")

        except Exception as e:
            print(f"  ! Error recording batch statistics: {str(e)}")
            conn.rollback()

        finally:
            conn.close()


def main():
    """Main execution function for testing"""
    import os

    # Get database path
    db_path = os.path.join(os.path.dirname(__file__), 'crm_database.db')

    # Create processor
    processor = LexisNexisBatchProcessor(db_path)

    # Run batch processing
    stats = processor.run_overnight_batch()

    print("\nBatch Processing Statistics:")
    print(f"  Records Processed: {stats['records_processed']}")
    print(f"  Cases Created: {stats['cases_created']}")
    print(f"  Cases Already Exist: {stats['cases_already_exist']}")
    print(f"  Match Failures: {stats['match_failures']}")
    print(f"  Processing Time: {stats['processing_time_seconds']:.2f}s")


if __name__ == '__main__':
    main()
