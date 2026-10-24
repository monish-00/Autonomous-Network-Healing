from datetime import datetime, timezone


class AlarmManager:
    """Manage active network alarms and their lifecycle."""

    def __init__(self):
        self.alarms = {}

    @staticmethod
    def current_time():
        return datetime.now(timezone.utc).isoformat()

    def process_status(self, target, status, details=None):
        """
        Create an alarm when a target goes DOWN.
        Resolve its alarm when the target returns UP.
        """
        if status not in ("UP", "DOWN"):
            raise ValueError("Status must be UP or DOWN.")

        if status == "DOWN":
            if target not in self.alarms:
                self.alarms[target] = {
                    "target": target,
                    "status": "ACTIVE",
                    "first_seen": self.current_time(),
                    "last_seen": self.current_time(),
                    "occurrences": 1,
                    "details": details,
                }

                print(f"[ALARM CREATED] {target} is DOWN")

            else:
                alarm = self.alarms[target]
                alarm["last_seen"] = self.current_time()
                alarm["occurrences"] += 1
                alarm["details"] = details

                print(
                    f"[ALARM UPDATED] {target} remains DOWN "
                    f"(checks: {alarm['occurrences']})"
                )

        else:
            if target in self.alarms:
                alarm = self.alarms.pop(target)
                alarm["status"] = "RESOLVED"
                alarm["resolved_at"] = self.current_time()

                print(f"[ALARM RESOLVED] {target} is UP")

                return alarm

            print(f"[HEALTHY] {target} is UP")

        return self.alarms.get(target)

    def get_active_alarms(self):
        """Return all currently active alarms."""
        return list(self.alarms.values())