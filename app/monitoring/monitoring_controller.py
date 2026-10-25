from app.monitoring.network_monitor import check_host, check_http_health
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
        """Monitor HTTP health, raise alarms, and attempt recovery."""

        target = f"{self.host}:{self.port}"

        print("\n=== AUTONOMOUS NETWORK HEALING PLATFORM ===")
        print(f"Checking target: {target}")

        # Step 1: Check TCP connectivity.
        tcp_result = check_host(self.host, self.port)
        print(f"\n[TCP CHECK] Status: {tcp_result['status']}")

        # Step 2: Check actual application health.
        result = check_http_health(self.host, self.port)

        print(f"[HTTP CHECK] Status: {result['status']}")
        print(f"[HTTP CHECK] URL: {result['url']}")

        if result["error"]:
            print(f"[HTTP CHECK] Details: {result['error']}")

        # Step 3: Create or resolve alarms based on HTTP health.
        self.alarm_manager.process_status(
            target=target,
            status=result["status"],
            details=result.get("error"),
        )

        recovery_result = None

        # Step 4: Attempt recovery if the application is unhealthy.
        if result["status"] == "DOWN":
            print("\n[RECOVERY] Attempting service recovery...")

            recovery_result = self.recovery_manager.recover()

            print(f"[RECOVERY] {recovery_result['message']}")
            print(
                "[RECOVERY] Duration: "
                f"{recovery_result['recovery_time_seconds']} seconds"
            )

            # Step 5: Verify actual application health after recovery.
            verified = check_http_health(self.host, self.port)

            # Recheck TCP connectivity after the recovery attempt.
            tcp_verified = check_host(self.host, self.port)
            tcp_result = tcp_verified

            print(f"[VERIFICATION] TCP status: {tcp_verified['status']}")
            print(f"[VERIFICATION] HTTP status: {verified['status']}")

            recovery_succeeded = bool(recovery_result["success"]) and (
                verified["status"] == "UP"
            )
            self.alarm_manager.record_recovery(
                target=target,
                success=recovery_succeeded,
                duration=recovery_result["recovery_time_seconds"],
            )

            if recovery_succeeded:
                self.alarm_manager.process_status(
                    target=target,
                    status="UP",
                    recovery_success=True,
                    recovery_duration=recovery_result["recovery_time_seconds"],
                )

                result = verified
                print("[RECOVERY SUCCESS] Application is healthy again.")
            else:
                print(
                    "[RECOVERY FAILED] Recovery was unsuccessful or the "
                    "HTTP health check still fails. The alarm remains active."
                )

        print("\n=== FINAL RESULT ===")
        print(f"Target: {target}")
        print(f"TCP status: {tcp_result['status']}")
        print(f"Application status: {result['status']}")

        print("\nActive alarms:")

        active_alarms = self.alarm_manager.get_active_alarms()

        for alarm in active_alarms:
            print(alarm)

        return {
            "tcp_monitoring": tcp_result,
            "monitoring": result,
            "recovery": recovery_result,
            "active_alarms": active_alarms,
        }


if __name__ == "__main__":
    controller = MonitoringController()
    controller.check_target()
