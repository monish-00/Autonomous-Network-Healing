import socket
import subprocess
import sys
import time
import os
import ipaddress
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ServiceRecovery:
    """Restart and verify the project's controlled test service."""

    def __init__(self, host="127.0.0.1", port=8080):
        self.host = host
        self.port = port
        self.process = None

    def is_service_running(self):
        """Check whether the test service accepts TCP connections."""
        try:
            with socket.create_connection(
                (self.host, self.port),
                timeout=1.0,
            ):
                return True
        except OSError:
            return False

    def start_service(self):
        """Start the project's own test service if it is unavailable."""

        if self.is_service_running():
            return {
                "success": False,
                "message": (
                    "The TCP port is reachable, so the controlled test "
                    "service was not restarted. Application health must be "
                    "verified over HTTP."
                ),
            }

        try:
            local_target = self.host == "localhost" or ipaddress.ip_address(
                self.host
            ).is_loopback
        except ValueError:
            local_target = False

        if not local_target:
            return {
                "success": False,
                "message": "Automatic recovery supports only a local test service.",
            }

        service_file = (
            PROJECT_ROOT
            / "app"
            / "monitoring"
            / "test_service.py"
        )

        service_env = os.environ.copy()
        service_env["TEST_SERVICE_HOST"] = "127.0.0.1"
        service_env["TEST_SERVICE_PORT"] = str(self.port)
        self.process = subprocess.Popen(
            [sys.executable, str(service_file)],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=service_env,
        )

        # Wait briefly for the service to become available.
        for _ in range(20):
            if self.is_service_running():
                return {
                    "success": True,
                    "message": "Service restarted successfully.",
                }

            if self.process.poll() is not None:
                return {
                    "success": False,
                    "message": (
                        "Test service process exited unexpectedly."
                    ),
                }

            time.sleep(0.25)

        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()

        return {
            "success": False,
            "message": "Service did not become available in time.",
        }

    def recover(self):
        """Attempt recovery and return the measured result."""

        start_time = time.perf_counter()

        if self.is_service_running():
            recovery_time = time.perf_counter() - start_time
            return {
                "success": False,
                "recovery_time_seconds": round(recovery_time, 3),
                "message": (
                    "Recovery could not restart the service because its TCP "
                    "port is already reachable; HTTP health remains the "
                    "controller's verification signal."
                ),
            }

        result = self.start_service()

        recovery_time = time.perf_counter() - start_time

        return {
            "success": result["success"],
            "recovery_time_seconds": round(recovery_time, 3),
            "message": (
                "Test service process started and its TCP port is reachable; "
                "awaiting HTTP health verification."
                if result["success"]
                else result["message"]
            ),
        }


if __name__ == "__main__":
    recovery = ServiceRecovery()

    print("\n=== AUTOMATIC SERVICE RECOVERY ===")

    if recovery.is_service_running():
        print("Service is healthy. Stop it to test recovery.")
    else:
        print("Service is DOWN. Attempting recovery...")

        result = recovery.recover()

        print(f"Result: {result['message']}")
        print(
            "Recovery time: "
            f"{result['recovery_time_seconds']} seconds"
        )
        print(f"Recovery successful: {result['success']}")
