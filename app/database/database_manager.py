import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from contextlib import contextmanager

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = PROJECT_ROOT / "network_healing.db"


def current_time():
    return datetime.now(timezone.utc).isoformat()


class DatabaseManager:
    """Persist alarm records and incident events using SQLite."""

    def close(self):
        """Close any resources if needed."""
        pass

    def __init__(self, database_path=DATABASE_PATH):
        self.database_path = str(database_path)
        self.initialize_database()

    @contextmanager
    def get_connection(self):
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row

        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize_database(self):
        """Create the required tables if they do not exist."""

        with self.get_connection() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS alarms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target TEXT NOT NULL,
                    severity TEXT NOT NULL DEFAULT 'CRITICAL',
                    status TEXT NOT NULL DEFAULT 'ACTIVE',
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    occurrences INTEGER NOT NULL DEFAULT 1,
                    details TEXT,
                    resolved_at TEXT,
                    recovery_success INTEGER,
                    recovery_duration REAL
                )
            """)

            connection.execute("""
                CREATE TABLE IF NOT EXISTS incident_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alarm_id INTEGER,
                    target TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    description TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (alarm_id)
                        REFERENCES alarms(id)
                )
            """)

    def create_alarm(
        self,
        target,
        severity="CRITICAL",
        details=None,
    ):
        """Create a new active alarm and record its creation event."""

        timestamp = current_time()

        with self.get_connection() as connection:
            cursor = connection.execute("""
                INSERT INTO alarms (
                    target,
                    severity,
                    status,
                    first_seen,
                    last_seen,
                    occurrences,
                    details
                )
                VALUES (?, ?, 'ACTIVE', ?, ?, 1, ?)
            """, (
                target,
                severity,
                timestamp,
                timestamp,
                details,
            ))

            alarm_id = cursor.lastrowid

            connection.execute("""
                INSERT INTO incident_events (
                    alarm_id,
                    target,
                    event_type,
                    description,
                    timestamp
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                alarm_id,
                target,
                "ALARM_CREATED",
                details or f"{severity} alarm created",
                timestamp,
            ))

            return alarm_id

    def record_failure(self, alarm_id, details=None):
        """Update an existing alarm without creating a duplicate."""

        timestamp = current_time()

        with self.get_connection() as connection:
            connection.execute("""
                UPDATE alarms
                SET last_seen = ?,
                    occurrences = occurrences + 1,
                    details = ?
                WHERE id = ? AND status = 'ACTIVE'
            """, (
                timestamp,
                details,
                alarm_id,
            ))

            connection.execute("""
                INSERT INTO incident_events (
                    alarm_id,
                    target,
                    event_type,
                    description,
                    timestamp
                )
                SELECT id, target, 'ALARM_UPDATED', ?, ?
                FROM alarms
                WHERE id = ?
            """, (
                details or "Repeated failure detected",
                timestamp,
                alarm_id,
            ))

    def resolve_alarm(
        self,
        alarm_id,
        recovery_success=True,
        recovery_duration=None,
    ):
        """Resolve an active alarm and record its recovery outcome."""

        timestamp = current_time()

        with self.get_connection() as connection:
            cursor = connection.execute("""
                UPDATE alarms
                SET status = 'RESOLVED',
                    resolved_at = ?,
                    recovery_success = ?,
                    recovery_duration = ?
                WHERE id = ? AND status = 'ACTIVE'
            """, (
                timestamp,
                int(recovery_success),
                recovery_duration,
                alarm_id,
            ))

            if cursor.rowcount:
                row = connection.execute("""
                    SELECT target FROM alarms WHERE id = ?
                """, (alarm_id,)).fetchone()

                connection.execute("""
                    INSERT INTO incident_events (
                        alarm_id,
                        target,
                        event_type,
                        description,
                        timestamp
                    )
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    alarm_id,
                    row["target"],
                    "ALARM_RESOLVED",
                    "Service recovered and alarm resolved",
                    timestamp,
                ))

    def get_active_alarms(self):
        with self.get_connection() as connection:
            rows = connection.execute("""
                SELECT * FROM alarms
                WHERE status = 'ACTIVE'
                ORDER BY first_seen DESC
            """).fetchall()

            return [dict(row) for row in rows]

    def get_all_alarms(self):
        with self.get_connection() as connection:
            rows = connection.execute("""
                SELECT * FROM alarms
                ORDER BY first_seen DESC
            """).fetchall()

            return [dict(row) for row in rows]

    def get_event_history(self, limit=100):
        with self.get_connection() as connection:
            rows = connection.execute("""
                SELECT * FROM incident_events
                ORDER BY timestamp DESC, id DESC
                LIMIT ?
            """, (limit,)).fetchall()

            return [dict(row) for row in rows]


if __name__ == "__main__":
    database = DatabaseManager()

    print("Database initialized successfully.")
    print(f"Database location: {DATABASE_PATH}")
    print("Tables: alarms, incident_events")