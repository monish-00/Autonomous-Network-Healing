from app.monitoring.network_monitor import check_host
from app.fault_management.alarm_manager import AlarmManager
from app.recovery.service_recovery import ServiceRecovery


class MonitoringController:
    """Coordinate monitoring, alarm management, and recovery."""

    def __init__(self, host="127.0.0.1", port=8080):
        self.host = host
        self.port = port
        self.alarm_manager = AlarmManager()
        self.recovery_manager = ServiceRecovery(host, port)

    def check_target(self):
        """Monitor the target, raise alarms, and attempt recovery."""

        target = f"{self.host}:{self.port}"

        print("\n=== AUTONOMOUS NETWORK HEALING PLATFORM ===")
        print(f"Checking target: {target}")

        # Step 1: Monitor the service.
        result = check_host(self.host, self.port)

        print(f"Initial status: {result['status']}")

        # Step 2: Process the alarm.
        self.alarm_manager.process_status(
            target=target,
            status=result["status"],
            details=result.get("error"),
        )

        # Step 3: Attempt recovery only when the service is DOWN.
        recovery_result = None

        if result["status"] == "DOWN":
            print("\n[RECOVERY] Attempting service recovery...")

            recovery_result = self.recovery_manager.recover()
            self.alarm_manager.record_recovery(
                target=target,
                success=recovery_result["success"],
                duration=recovery_result["recovery_time_seconds"],
            )

            print(f"[RECOVERY] {recovery_result['message']}")
            print(
                "[RECOVERY] Duration: "
                f"{recovery_result['recovery_time_seconds']} seconds"
            )

            # Step 4: Independently check the service after recovery.
            verified = check_host(self.host, self.port)

            print(f"[VERIFICATION] Status: {verified['status']}")

            if verified["status"] == "UP":
                self.alarm_manager.process_status(
                    target=target,
                    status="UP",
                )
                result = verified

            else:
                print(
                    "[RECOVERY FAILED] The service is still unavailable."
                )

        print("\n=== FINAL RESULT ===")
        print(f"Target: {target}")
        print(f"Status: {result['status']}")

        print("\nActive alarms:")

        for alarm in self.alarm_manager.get_active_alarms():
            print(alarm)

        return {
            "monitoring": result,
            "recovery": recovery_result,
            "active_alarms": self.alarm_manager.get_active_alarms(),
        }


if __name__ == "__main__":
    controller = MonitoringController()
    controller.check_target()