import os

from app.monitoring.network_monitor import check_host, check_http_health
from app.fault_management.alarm_manager import AlarmManager
from app.recovery.service_recovery import ServiceRecovery


class MonitoringController:
    """Coordinate monitoring, alarm management, and recovery."""

    def __init__(self, host=None, port=None, database=None):
        self.host = host or os.environ.get("MONITOR_HOST", "127.0.0.1")
        self.port = int(port or os.environ.get("MONITOR_PORT", "8080"))
        self.health_path = os.environ.get("HEALTH_PATH", "/health")
        self.timeout = float(os.environ.get("CHECK_TIMEOUT_SECONDS", "3"))
        self.alarm_manager = AlarmManager(database=database)
        self.recovery_manager = ServiceRecovery(host, port)

    def check_target(self):
        """Monitor HTTP health, raise alarms, and attempt recovery."""

        target = f"{self.host}:{self.port}"

        print("\n=== AUTONOMOUS NETWORK HEALING PLATFORM ===")
        print(f"Checking target: {target}")

        # Step 1: Check TCP connectivity.
        tcp_result = check_host(self.host, self.port, timeout=self.timeout)
        print(f"\n[TCP CHECK] Status: {tcp_result['status']}")

        # Step 2: Check actual application health.
        result = check_http_health(
            self.host,
            self.port,
            path=self.health_path,
            timeout=self.timeout,
        )

        print(f"[HTTP CHECK] Status: {result['status']}")
        print(f"[HTTP CHECK] URL: {result['url']}")

        if result["error"]:
            print(f"[HTTP CHECK] Details: {result['error']}")

        # Step 3: Create or resolve alarms based on HTTP health.
        self.alarm_manager.process_status(
            target=target,
            status=result["status"],
            details=(
                f"{result.get('fault_type')}: {result.get('error')}"
                if result.get("fault_type") and result.get("error")
                else result.get("error") or result.get("fault_type")
            ),
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
            verified = check_http_health(
                self.host,
                self.port,
                path=self.health_path,
                timeout=self.timeout,
            )

            # Recheck TCP connectivity after the recovery attempt.
            tcp_verified = check_host(self.host, self.port, timeout=self.timeout)
            tcp_result = tcp_verified

            print(f"[VERIFICATION] TCP status: {tcp_verified['status']}")
            print(f"[VERIFICATION] HTTP status: {verified['status']}")

            recovery_succeeded = bool(recovery_result["success"]) and (
                verified["status"] == "UP"
            )
            recovery_result = {
                **recovery_result,
                "attempt_success": bool(recovery_result["success"]),
                "http_verified": verified["status"] == "UP",
                "success": recovery_succeeded,
            }
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
