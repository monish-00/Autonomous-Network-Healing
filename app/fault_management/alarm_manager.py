from datetime import datetime, timezone

from app.database.database_manager import DatabaseManager


class AlarmManager:
    """Manage network alarms and persist their lifecycle in SQLite."""

    def __init__(self, database=None):
        self.database = database or DatabaseManager()
        self.alarms = {}

        # Restore active alarms after an application restart.
        for alarm in self.database.get_active_alarms():
            self.alarms[alarm["target"]] = {
                "id": alarm["id"],
                "target": alarm["target"],
                "status": "ACTIVE",
                "first_seen": alarm["first_seen"],
                "last_seen": alarm["last_seen"],
                "occurrences": alarm["occurrences"],
                "details": alarm["details"],
                "severity": alarm["severity"],
            }

    @staticmethod
    def current_time():
        return datetime.now(timezone.utc).isoformat()

    def process_status(self, target, status, details=None):
        """Create, update, or resolve an alarm based on service status."""

        if status not in ("UP", "DOWN"):
            raise ValueError("Status must be UP or DOWN.")

        if status == "DOWN":
            if target not in self.alarms:
                alarm_id = self.database.create_alarm(
                    target=target,
                    severity="CRITICAL",
                    details=details,
                )

                alarm = {
                    "id": alarm_id,
                    "target": target,
                    "status": "ACTIVE",
                    "first_seen": self.current_time(),
                    "last_seen": self.current_time(),
                    "occurrences": 1,
                    "details": details,
                    "severity": "CRITICAL",
                }

                self.alarms[target] = alarm

                print(f"[ALARM CREATED] {target} is DOWN")

            else:
                alarm = self.alarms[target]
                alarm["last_seen"] = self.current_time()
                alarm["occurrences"] += 1
                alarm["details"] = details

                self.database.record_failure(
                    alarm_id=alarm["id"],
                    details=details,
                )

                print(
                    f"[ALARM UPDATED] {target} remains DOWN "
                    f"(checks: {alarm['occurrences']})"
                )

        else:
            if target in self.alarms:
                alarm = self.alarms.pop(target)
                alarm["status"] = "RESOLVED"
                alarm["resolved_at"] = self.current_time()

                self.database.resolve_alarm(
                    alarm_id=alarm["id"],
                    recovery_success=True,
                )

                print(f"[ALARM RESOLVED] {target} is UP")
                return alarm

            print(f"[HEALTHY] {target} is UP")

        return self.alarms.get(target)

    def record_recovery(self, target, success, duration):
        """Record a recovery result for an active alarm."""

        alarm = self.alarms.get(target)

        if alarm is None:
            return

        # Store the recovery outcome without resolving the alarm.
        with self.database.get_connection() as connection:
            connection.execute(
                """
                UPDATE alarms
                SET recovery_success = ?,
                    recovery_duration = ?
                WHERE id = ? AND status = 'ACTIVE'
                """,
                (int(success), duration, alarm["id"]),
            )

    def get_active_alarms(self):
        """Return all currently active alarms."""
        return list(self.alarms.values())

    def get_all_alarms(self):
        """Return all persisted alarms, including resolved alarms."""
        return self.database.get_all_alarms()