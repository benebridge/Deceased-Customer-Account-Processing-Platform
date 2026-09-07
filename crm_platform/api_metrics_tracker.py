#!/usr/bin/env python3
"""
API Performance Metrics Tracking

Per dissertation Table 5.3, tracks API call performance for:
- AWS Textract: Target 1,847ms average
- Ribbon Verify: Target 2,134ms average
- Persona API: Target 1,523ms average
- DocuSign: Target 892ms average

Stores metrics in SQLite database for analysis and dissertation validation.
"""

import sqlite3
import time
from datetime import datetime
import os


class APIMetricsTracker:
    """
    Tracks and logs API call performance metrics.

    Usage:
        tracker = APIMetricsTracker()
        result, duration_ms = tracker.track_api_call(
            'aws_textract',
            extract_death_certificate_textract,
            file_path='/path/to/file.pdf'
        )
    """

    def __init__(self, db_path=None):
        """
        Initialize metrics tracker.

        Args:
            db_path: Path to SQLite database. If None, uses crm_database.db
        """
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), 'crm_database.db')

        self.db_path = db_path
        self._ensure_metrics_table_exists()

    def _ensure_metrics_table_exists(self):
        """Create api_performance_metrics table if it doesn't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                api_name TEXT NOT NULL,
                duration_ms REAL NOT NULL,
                success BOOLEAN NOT NULL,
                error_message TEXT,
                case_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def track_api_call(self, api_name, func, *args, **kwargs):
        """
        Wrapper to track API call performance.

        Args:
            api_name: Name of the API (e.g., 'aws_textract', 'ribbon_verify')
            func: Function to call
            *args, **kwargs: Arguments to pass to the function

        Returns:
            tuple: (result, duration_ms)
        """
        start_time = time.time()
        error_message = None
        success = True
        result = None

        try:
            result = func(*args, **kwargs)

            # Determine success based on result structure
            if isinstance(result, dict):
                success = result.get('verified', result.get('success', True))

        except Exception as e:
            success = False
            error_message = str(e)
            result = {'error': error_message, 'success': False}

        finally:
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000

            # Log to database
            self._log_api_call(
                api_name=api_name,
                duration_ms=duration_ms,
                success=success,
                error_message=error_message,
                case_id=kwargs.get('case_id', None)
            )

            # Print performance info
            status = "✓" if success else "✗"
            print(f"  {status} API Call: {api_name} - {duration_ms:.2f}ms")

        return result, duration_ms

    def _log_api_call(self, api_name, duration_ms, success, error_message=None, case_id=None):
        """
        Log API call metrics to database.

        Args:
            api_name: Name of the API
            duration_ms: Duration in milliseconds
            success: Whether the call succeeded
            error_message: Error message if failed
            case_id: Associated case ID if applicable
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO api_performance_metrics (
                    timestamp,
                    api_name,
                    duration_ms,
                    success,
                    error_message,
                    case_id
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                api_name,
                duration_ms,
                success,
                error_message,
                case_id
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"  ! Error logging API metrics: {str(e)}")

    def get_api_statistics(self, api_name=None, days=30):
        """
        Get performance statistics for API calls.

        Args:
            api_name: Optional filter by API name
            days: Number of days to analyze (default: 30)

        Returns:
            dict: Statistics including average, min, max duration, success rate
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = """
                SELECT
                    api_name,
                    COUNT(*) as total_calls,
                    AVG(duration_ms) as avg_duration,
                    MIN(duration_ms) as min_duration,
                    MAX(duration_ms) as max_duration,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_calls,
                    COUNT(*) as total_calls_for_rate
                FROM api_performance_metrics
                WHERE datetime(timestamp) > datetime('now', '-' || ? || ' days')
            """

            if api_name:
                query += " AND api_name = ?"
                cursor.execute(query + " GROUP BY api_name", (days, api_name))
            else:
                query += " GROUP BY api_name"
                cursor.execute(query, (days,))

            results = cursor.fetchall()
            conn.close()

            stats = []
            for row in results:
                api, total, avg, min_dur, max_dur, successful, total_for_rate = row
                stats.append({
                    'api_name': api,
                    'total_calls': total,
                    'avg_duration_ms': round(avg, 2) if avg else 0,
                    'min_duration_ms': round(min_dur, 2) if min_dur else 0,
                    'max_duration_ms': round(max_dur, 2) if max_dur else 0,
                    'success_rate': round((successful / total_for_rate * 100), 2) if total_for_rate > 0 else 0,
                    'successful_calls': successful,
                    'failed_calls': total - successful
                })

            return stats

        except Exception as e:
            print(f"  ! Error retrieving API statistics: {str(e)}")
            return []

    def print_statistics_report(self, days=30):
        """
        Print formatted API performance statistics report.

        Args:
            days: Number of days to analyze (default: 30)
        """
        stats = self.get_api_statistics(days=days)

        if not stats:
            print("No API performance data available.")
            return

        print("\n" + "=" * 80)
        print(f"API PERFORMANCE STATISTICS - Last {days} Days")
        print("=" * 80)
        print()

        # Dissertation target metrics for comparison
        targets = {
            'aws_textract': 1847,
            'ribbon_verify': 2134,
            'persona_api': 1523,
            'docusign': 892
        }

        for stat in stats:
            api = stat['api_name']
            print(f"API: {api}")
            print(f"  Total Calls: {stat['total_calls']}")
            print(f"  Success Rate: {stat['success_rate']}%")
            print(f"  Avg Duration: {stat['avg_duration_ms']:.2f}ms", end="")

            # Show comparison to dissertation target
            if api in targets:
                target = targets[api]
                diff = stat['avg_duration_ms'] - target
                diff_pct = (diff / target) * 100
                print(f" (Target: {target}ms, Diff: {diff:+.2f}ms / {diff_pct:+.1f}%)")
            else:
                print()

            print(f"  Min Duration: {stat['min_duration_ms']:.2f}ms")
            print(f"  Max Duration: {stat['max_duration_ms']:.2f}ms")
            print(f"  Successful: {stat['successful_calls']}, Failed: {stat['failed_calls']}")
            print()

        print("=" * 80 + "\n")


# Global singleton instance for easy import
_tracker_instance = None

def get_tracker():
    """Get global APIMetricsTracker instance (singleton pattern)"""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = APIMetricsTracker()
    return _tracker_instance


if __name__ == '__main__':
    # Test the metrics tracker
    tracker = APIMetricsTracker()

    # Create some test data
    import random

    print("Generating test API performance data...\n")

    apis = [
        ('aws_textract', 1800, 200),
        ('ribbon_verify', 2100, 300),
        ('persona_api', 1500, 200),
        ('docusign', 900, 100)
    ]

    for api_name, base_ms, variance in apis:
        for _ in range(5):
            duration = base_ms + random.uniform(-variance, variance)
            success = random.random() > 0.1  # 90% success rate

            tracker._log_api_call(
                api_name=api_name,
                duration_ms=duration,
                success=success,
                error_message=None if success else "Simulated error",
                case_id=random.randint(1, 100)
            )

    # Print statistics report
    tracker.print_statistics_report(days=30)
